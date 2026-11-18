package com.qianmo.ruralvision.pipeline

import android.graphics.Bitmap
import android.os.PowerManager
import android.os.SystemClock
import android.util.Log
import com.qianmo.ruralvision.camera.CameraFrameProcessor
import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.debug.DebugCapture
import com.qianmo.ruralvision.domain.DriveStateEvaluator
import com.qianmo.ruralvision.inference.DetectionModule
import com.qianmo.ruralvision.inference.NoOpDetectionModule
import com.qianmo.ruralvision.inference.DetectionRuntimeSetup
import com.qianmo.ruralvision.inference.SegmentationEngine
import com.qianmo.ruralvision.postprocess.MaskPostProcessor
import com.qianmo.ruralvision.render.OverlayView
import com.qianmo.ruralvision.tts.WarningTtsManager
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

class LatestFramePerceptionCoordinator(
    private val frameProcessor: CameraFrameProcessor,
    private val segmentationEngine: SegmentationEngine,
    private val maskPostProcessor: MaskPostProcessor,
    private val driveStateEvaluator: DriveStateEvaluator,
    private val overlayView: OverlayView,
    private val warningTtsManager: WarningTtsManager,
    private val detectionModule: DetectionModule = NoOpDetectionModule(),
    private val detectionRuntimeSetup: DetectionRuntimeSetup = DetectionRuntimeSetup(
        module = NoOpDetectionModule(),
        requested = false,
        ready = false,
        modeText = "仅分割",
        stateText = "检测未启用",
        runtimeLabel = "未启用",
        modelName = AppConfig.Detection.MODEL_NAME
    ),
    private val onDebugCaptureReady: ((DebugCapture) -> Unit)? = null
) {
    companion object {
        private const val TAG = "PerceptionCoordinator"
        private const val PERF_LOG_INTERVAL_FRAMES = 5L
        private const val PERF_LOG_INITIAL_FRAMES = 3L
    }

    data class UiRuntimeState(
        val perfText: String,
        val modeText: String,
        val detectionStateText: String,
        val segmentationDetailText: String,
        val detectionDetailText: String
    )

    private data class FramePacket(
        val bitmap: Bitmap,
        val rotationDegrees: Int,
        val mirrorX: Boolean
    )

    private val executor = Executors.newSingleThreadExecutor()
    private val latestFrame = AtomicReference<FramePacket?>(null)
    private val isRunning = AtomicBoolean(false)
    private val isShuttingDown = AtomicBoolean(false)
    private val debugCaptureRequested = AtomicBoolean(false)

    @Volatile
    private var thermalStatus: Int = PowerManager.THERMAL_STATUS_NONE

    @Volatile
    private var nextFrameAllowedAtMs: Long = 0L

    private var lastProcessMs = 0L
    private var lastFrameCompletedAtMs = 0L
    private var processedFrames = 0L
    private var lastDetectionBoxes = emptyList<com.qianmo.ruralvision.postprocess.BoxPostProcessor.Box>()
    private var detectionBackoffUntilFrame = 0L
    private var detectionRuntimeFailed = false
    private var detectionFailureText = "检测未启用"

    fun submitFrame(
        frame: Bitmap,
        rotationDegrees: Int = 0,
        mirrorX: Boolean = false
    ) {
        if (isShuttingDown.get()) return
        latestFrame.set(FramePacket(frame, rotationDegrees, mirrorX))
        tryStartProcessing()
    }

    fun getLastProcessMs(): Long = lastProcessMs

    fun canAcceptFrame(): Boolean {
        return !isShuttingDown.get() && !isRunning.get() && !isCoolingDown()
    }

    fun requestDebugCapture(): Boolean {
        if (isShuttingDown.get()) return false
        debugCaptureRequested.set(true)
        return true
    }

    fun updateThermalStatus(status: Int) {
        thermalStatus = status
        Log.i(
            TAG,
            "Thermal status=${thermalStatusLabel(status)}, processing cap=${"%.1f".format(currentProcessingFpsCap())}fps, runtime=${segmentationEngine.runtimeLabel}"
        )
    }

    fun shutdown() {
        if (!isShuttingDown.compareAndSet(false, true)) return
        latestFrame.set(null)
        executor.shutdown()
        try {
            if (!executor.awaitTermination(1500, TimeUnit.MILLISECONDS)) {
                executor.shutdownNow()
                executor.awaitTermination(500, TimeUnit.MILLISECONDS)
            }
        } catch (_: InterruptedException) {
            executor.shutdownNow()
            Thread.currentThread().interrupt()
        }
        warningTtsManager.release()
        detectionModule.close()
        segmentationEngine.close()
    }

    private fun tryStartProcessing() {
        if (isShuttingDown.get() || isCoolingDown() || latestFrame.get() == null) return
        if (isRunning.compareAndSet(false, true)) {
            executor.execute {
                try {
                    processLatest()
                } catch (ex: Exception) {
                    Log.e(TAG, "Perception pipeline crashed while processing frame", ex)
                } finally {
                    isRunning.set(false)
                    if (!isShuttingDown.get()) {
                        tryStartProcessing()
                    }
                }
            }
        }
    }

    private fun processLatest() {
        while (true) {
            if (isShuttingDown.get()) break
            val packet = latestFrame.getAndSet(null) ?: break
            val startMs = SystemClock.elapsedRealtime()
            processedFrames += 1

            val preprocessStartMs = SystemClock.elapsedRealtime()
            val segPrep = frameProcessor.preprocess(
                frame = packet.bitmap,
                inputWidth = segmentationEngine.inputWidth,
                inputHeight = segmentationEngine.inputHeight,
                rotationDegrees = packet.rotationDegrees,
                mirrorX = packet.mirrorX
            )
            val preprocessMs = SystemClock.elapsedRealtime() - preprocessStartMs

            val segmentationStartMs = SystemClock.elapsedRealtime()
            val segResult = segmentationEngine.run(segPrep.inputBuffer)
            val segmentationMs = SystemClock.elapsedRealtime() - segmentationStartMs

            val detectionStartMs = SystemClock.elapsedRealtime()
            val boxes = maybeRunDetection(packet)
            val detectionMs = SystemClock.elapsedRealtime() - detectionStartMs
            val driveState = driveStateEvaluator.evaluate(
                mask = segResult.binaryMask,
                width = segResult.width,
                height = segResult.height,
                boxes = boxes
            )
            driveState.warningEvent?.let { event ->
                warningTtsManager.speakWarning(
                    event = event,
                    minIntervalMs = AppConfig.Runtime.TTS_INTERVAL_MS
                )
            }

            val elapsed = SystemClock.elapsedRealtime() - startMs
            lastProcessMs = elapsed
            val completedAtMs = SystemClock.elapsedRealtime()
            val outputIntervalMs =
                if (lastFrameCompletedAtMs == 0L) elapsed else completedAtMs - lastFrameCompletedAtMs
            lastFrameCompletedAtMs = completedAtMs
            val cooldownMs = computeCooldownMs(elapsed)
            nextFrameAllowedAtMs = completedAtMs + cooldownMs
            val runtimeState = buildRuntimeState(
                processElapsedMs = elapsed,
                outputIntervalMs = outputIntervalMs
            )
            logPerformanceIfNeeded(
                totalMs = elapsed,
                preprocessMs = preprocessMs,
                segmentationMs = segmentationMs,
                detectionMs = detectionMs,
                outputIntervalMs = outputIntervalMs
            )
            maybeDispatchDebugCapture(
                segPrep = segPrep,
                segResult = segResult,
                driveState = driveState,
                runtimeState = runtimeState,
                totalMs = elapsed,
                preprocessMs = preprocessMs,
                segmentationMs = segmentationMs,
                detectionMs = detectionMs
            )

            overlayView.post {
                overlayView.updateOverlay(
                    OverlayView.OverlayState(
                        maskData = segResult.binaryMask.copyOf(),
                        maskWidth = segResult.width,
                        maskHeight = segResult.height,
                        boxes = boxes,
                        statusText = driveState.statusText,
                        perfText = runtimeState.perfText,
                        voiceEnabled = warningTtsManager.isEnabled(),
                        voiceStatusText = warningTtsManager.statusText(),
                        modeText = runtimeState.modeText,
                        detectionStateText = runtimeState.detectionStateText,
                        segmentationDetailText = runtimeState.segmentationDetailText,
                        detectionDetailText = runtimeState.detectionDetailText
                    )
                )
            }

            if (cooldownMs > 0L) break
        }
    }

    private fun logPerformanceIfNeeded(
        totalMs: Long,
        preprocessMs: Long,
        segmentationMs: Long,
        detectionMs: Long,
        outputIntervalMs: Long
    ) {
        val shouldLog =
            processedFrames <= PERF_LOG_INITIAL_FRAMES ||
                processedFrames % PERF_LOG_INTERVAL_FRAMES == 0L
        if (!shouldLog) return
        Log.i(
            TAG,
            "Frame #$processedFrames timings total=${totalMs}ms preprocess=${preprocessMs}ms segmentation=${segmentationMs}ms detection=${detectionMs}ms wall=${outputIntervalMs}ms"
        )
    }

    private fun maybeDispatchDebugCapture(
        segPrep: CameraFrameProcessor.PreprocessResult,
        segResult: SegmentationEngine.SegmentationResult,
        driveState: DriveStateEvaluator.DriveState,
        runtimeState: UiRuntimeState,
        totalMs: Long,
        preprocessMs: Long,
        segmentationMs: Long,
        detectionMs: Long
    ) {
        if (!debugCaptureRequested.compareAndSet(true, false)) return
        val callback = onDebugCaptureReady ?: return
        try {
            callback(
                DebugCapture(
                    frameBitmap = segPrep.previewBitmap.copy(Bitmap.Config.ARGB_8888, false),
                    maskData = segResult.binaryMask.copyOf(),
                    maskWidth = segResult.width,
                    maskHeight = segResult.height,
                    frameIndex = processedFrames,
                    totalMs = totalMs,
                    preprocessMs = preprocessMs,
                    segmentationMs = segmentationMs,
                    detectionMs = detectionMs,
                    statusText = driveState.statusText,
                    perfText = runtimeState.perfText,
                    modeText = runtimeState.modeText,
                    detectionStateText = runtimeState.detectionStateText,
                    drivableRatio = driveState.drivableRatio,
                    centerSafe = driveState.centerSafe,
                    roadNarrow = driveState.roadNarrow,
                    segmentationRuntime = segmentationEngine.runtimeLabel,
                    segmentationModelName = segmentationEngine.activeModelName,
                    detectionRuntime = detectionRuntimeSetup.runtimeLabel,
                    detectionModelName = detectionRuntimeSetup.modelName
                )
            )
        } catch (ex: Exception) {
            Log.e(TAG, "Failed to dispatch debug capture", ex)
        }
    }

    private fun maybeRunDetection(packet: FramePacket): List<com.qianmo.ruralvision.postprocess.BoxPostProcessor.Box> {
        if (!detectionModule.available || !AppConfig.Detection.ENABLED || detectionRuntimeFailed) {
            return emptyList()
        }

        if (isDetectionBackoffActive()) {
            return lastDetectionBoxes
        }

        val shouldRun = processedFrames % AppConfig.Detection.RUN_EVERY_N_FRAMES == 0L
        if (!shouldRun) {
            return lastDetectionBoxes
        }

        val detPrep = frameProcessor.preprocess(
            frame = packet.bitmap,
            inputWidth = detectionModule.inputSize,
            inputHeight = detectionModule.inputSize,
            rotationDegrees = packet.rotationDegrees,
            mirrorX = packet.mirrorX,
            tensorLayout = detectionModule.tensorLayout
        )
        return try {
            val detectionStartMs = SystemClock.elapsedRealtime()
            val result = detectionModule.detect(detPrep.inputBuffer)
            val detectionElapsedMs = SystemClock.elapsedRealtime() - detectionStartMs
            lastDetectionBoxes = result
            maybeApplyDetectionBackoff(detectionElapsedMs)
            result
        } catch (ex: Exception) {
            detectionRuntimeFailed = true
            detectionFailureText = "检测运行失败，已自动关闭"
            lastDetectionBoxes = emptyList()
            Log.e(TAG, "Detection inference failed; disabling detection for this session.", ex)
            emptyList()
        }
    }

    private fun buildRuntimeState(
        processElapsedMs: Long,
        outputIntervalMs: Long
    ): UiRuntimeState {
        val outputFps = if (outputIntervalMs <= 0) 0f else 1000f / outputIntervalMs.toFloat()
        val computeFps = if (processElapsedMs <= 0) 0f else 1000f / processElapsedMs.toFloat()
        val mode = when {
            outputFps >= AppConfig.Runtime.TARGET_FPS -> "流畅"
            outputFps >= AppConfig.Runtime.MIN_ACCEPTABLE_FPS -> "一般"
            else -> "降级"
        }
        val detectionStateText = detectionStateText()
        return UiRuntimeState(
            perfText = "识别中 $mode 输出${"%.1f".format(outputFps)} 计算${"%.1f".format(computeFps)}FPS",
            modeText = if (detectionRuntimeFailed) "仅分割" else detectionRuntimeSetup.modeText,
            detectionStateText = detectionStateText,
            segmentationDetailText = buildEvidenceLine(
                "分割",
                segmentationEngine.runtimeLabel,
                segmentationEngine.activeModelName
            ),
            detectionDetailText = buildEvidenceLine(
                "检测",
                detectionStateText,
                detectionRuntimeSetup.runtimeLabel,
                detectionRuntimeSetup.modelName
            )
        )
    }

    private fun detectionStateText(): String {
        if (detectionRuntimeFailed) return detectionFailureText
        return if (isDetectionBackoffActive()) {
            "${detectionRuntimeSetup.stateText} · 节流中"
        } else {
            detectionRuntimeSetup.stateText
        }
    }

    private fun buildEvidenceLine(prefix: String, vararg parts: String): String {
        val normalizedParts = parts
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
        return if (normalizedParts.isEmpty()) {
            prefix
        } else {
            "$prefix: ${normalizedParts.joinToString(" · ")}"
        }
    }

    private fun isDetectionBackoffActive(): Boolean {
        return processedFrames < detectionBackoffUntilFrame
    }

    private fun maybeApplyDetectionBackoff(detectionElapsedMs: Long) {
        if (detectionElapsedMs < AppConfig.Detection.SLOW_INFERENCE_THRESHOLD_MS) return
        val backoffFrames = computeDetectionBackoffFrames(detectionElapsedMs)
        val targetFrame = processedFrames + backoffFrames
        if (targetFrame <= detectionBackoffUntilFrame) return
        detectionBackoffUntilFrame = targetFrame
        Log.w(
            TAG,
            "Detection inference slow (${detectionElapsedMs}ms); backing off ${backoffFrames} frames until frame #$detectionBackoffUntilFrame"
        )
    }

    private fun computeDetectionBackoffFrames(detectionElapsedMs: Long): Long {
        val latencyBackoff = when {
            detectionElapsedMs >= AppConfig.Detection.SLOW_INFERENCE_EXTREME_THRESHOLD_MS ->
                AppConfig.Detection.SLOW_INFERENCE_EXTREME_BACKOFF_FRAMES

            detectionElapsedMs >= AppConfig.Detection.SLOW_INFERENCE_HIGH_THRESHOLD_MS ->
                AppConfig.Detection.SLOW_INFERENCE_HIGH_BACKOFF_FRAMES

            detectionElapsedMs >= AppConfig.Detection.SLOW_INFERENCE_MEDIUM_THRESHOLD_MS ->
                AppConfig.Detection.SLOW_INFERENCE_MEDIUM_BACKOFF_FRAMES

            else -> AppConfig.Detection.SLOW_INFERENCE_BACKOFF_FRAMES
        }
        val thermalExtra = when {
            thermalStatus >= PowerManager.THERMAL_STATUS_SEVERE -> AppConfig.Detection.RUN_EVERY_N_FRAMES.toLong() * 2L
            thermalStatus == PowerManager.THERMAL_STATUS_MODERATE -> AppConfig.Detection.RUN_EVERY_N_FRAMES.toLong()
            else -> 0L
        }
        return latencyBackoff + thermalExtra
    }

    private fun isCoolingDown(nowMs: Long = SystemClock.elapsedRealtime()): Boolean {
        return AppConfig.Runtime.ENABLE_SUSTAINED_PACING && nowMs < nextFrameAllowedAtMs
    }

    private fun computeCooldownMs(processElapsedMs: Long): Long {
        if (!AppConfig.Runtime.ENABLE_SUSTAINED_PACING) return 0L
        val cappedFps = currentProcessingFpsCap().coerceAtLeast(0.1f)
        val targetIntervalMs = (1000f / cappedFps).toLong()
        return (targetIntervalMs - processElapsedMs).coerceAtLeast(0L)
    }

    private fun currentProcessingFpsCap(): Float {
        val usingGpu = segmentationEngine.runtimeLabel.equals("GPU", ignoreCase = true)
        val maxFps = if (usingGpu) {
            AppConfig.Runtime.MAX_PROCESSING_FPS_GPU
        } else {
            AppConfig.Runtime.MAX_PROCESSING_FPS_CPU
        }
        val thermalCap = when {
            thermalStatus >= PowerManager.THERMAL_STATUS_CRITICAL -> {
                if (usingGpu) AppConfig.Runtime.THERMAL_CRITICAL_MAX_FPS_GPU else AppConfig.Runtime.THERMAL_CRITICAL_MAX_FPS_CPU
            }

            thermalStatus == PowerManager.THERMAL_STATUS_SEVERE -> {
                if (usingGpu) AppConfig.Runtime.THERMAL_SEVERE_MAX_FPS_GPU else AppConfig.Runtime.THERMAL_SEVERE_MAX_FPS_CPU
            }

            thermalStatus == PowerManager.THERMAL_STATUS_MODERATE -> {
                if (usingGpu) AppConfig.Runtime.THERMAL_MODERATE_MAX_FPS_GPU else AppConfig.Runtime.THERMAL_MODERATE_MAX_FPS_CPU
            }

            thermalStatus == PowerManager.THERMAL_STATUS_LIGHT -> {
                if (usingGpu) AppConfig.Runtime.THERMAL_LIGHT_MAX_FPS_GPU else AppConfig.Runtime.THERMAL_LIGHT_MAX_FPS_CPU
            }

            else -> maxFps
        }
        return minOf(maxFps, thermalCap)
    }

    private fun thermalStatusLabel(status: Int): String {
        return when (status) {
            PowerManager.THERMAL_STATUS_NONE -> "none"
            PowerManager.THERMAL_STATUS_LIGHT -> "light"
            PowerManager.THERMAL_STATUS_MODERATE -> "moderate"
            PowerManager.THERMAL_STATUS_SEVERE -> "severe"
            PowerManager.THERMAL_STATUS_CRITICAL -> "critical"
            PowerManager.THERMAL_STATUS_EMERGENCY -> "emergency"
            PowerManager.THERMAL_STATUS_SHUTDOWN -> "shutdown"
            else -> "unknown($status)"
        }
    }
}
