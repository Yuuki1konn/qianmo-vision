package com.qianmo.ruralvision.pipeline

import android.graphics.Bitmap
import android.os.SystemClock
import com.qianmo.ruralvision.camera.CameraFrameProcessor
import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.domain.DriveStateEvaluator
import com.qianmo.ruralvision.inference.SegmentationEngine
import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import com.qianmo.ruralvision.postprocess.MaskPostProcessor
import com.qianmo.ruralvision.render.OverlayView
import com.qianmo.ruralvision.tts.WarningTtsManager
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

class LatestFrameSegmentationCoordinator(
    private val frameProcessor: CameraFrameProcessor,
    private val segmentationEngine: SegmentationEngine,
    private val maskPostProcessor: MaskPostProcessor,
    private val driveStateEvaluator: DriveStateEvaluator,
    private val overlayView: OverlayView,
    private val warningTtsManager: WarningTtsManager
) {
    private val executor = Executors.newSingleThreadExecutor()
    private val latestFrame = AtomicReference<Bitmap?>(null)
    private val isRunning = AtomicBoolean(false)
    private var lastProcessMs = 0L

    fun submitFrame(
        frame: Bitmap,
        rotationDegrees: Int = 0,
        mirrorX: Boolean = false,
        boxes: List<BoxPostProcessor.Box> = emptyList()
    ) {
        latestFrame.set(frame)
        if (isRunning.compareAndSet(false, true)) {
            executor.execute {
                try {
                    processLatest(rotationDegrees, mirrorX, boxes)
                } finally {
                    isRunning.set(false)
                    val pendingFrame = latestFrame.get()
                    if (pendingFrame != null) {
                        submitFrame(pendingFrame, rotationDegrees, mirrorX, boxes)
                    }
                }
            }
        }
    }

    private fun processLatest(
        rotationDegrees: Int,
        mirrorX: Boolean,
        boxes: List<BoxPostProcessor.Box>
    ) {
        while (true) {
            val frame = latestFrame.getAndSet(null) ?: break
            val startMs = SystemClock.elapsedRealtime()
            val prep = frameProcessor.preprocess(
                frame = frame,
                inputWidth = segmentationEngine.inputWidth,
                inputHeight = segmentationEngine.inputHeight,
                rotationDegrees = rotationDegrees,
                mirrorX = mirrorX
            )
            val segResult = segmentationEngine.run(prep.inputBuffer)
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
            val perfText = buildPerfText(elapsed)

            overlayView.post {
                overlayView.updateOverlay(
                    OverlayView.OverlayState(
                        maskData = segResult.binaryMask.copyOf(),
                        maskWidth = segResult.width,
                        maskHeight = segResult.height,
                        boxes = boxes,
                        statusText = driveState.statusText,
                        perfText = perfText,
                        voiceEnabled = true
                    )
                )
            }
        }
    }

    fun getLastProcessMs(): Long = lastProcessMs

    fun shutdown() {
        executor.shutdownNow()
        warningTtsManager.release()
        segmentationEngine.close()
    }

    private fun buildPerfText(elapsedMs: Long): String {
        val fps = if (elapsedMs <= 0) 0f else (1000f / elapsedMs.toFloat())
        val mode = when {
            fps >= AppConfig.Runtime.TARGET_FPS -> "流畅"
            fps >= AppConfig.Runtime.MIN_ACCEPTABLE_FPS -> "一般"
            else -> "降级"
        }
        return "识别中 $mode ${"%.1f".format(fps)}FPS"
    }
}
