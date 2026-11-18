package com.qianmo.ruralvision

import android.Manifest
import android.content.Intent
import android.content.res.Configuration
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.util.Size
import android.util.Log
import android.view.Surface
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.qianmo.ruralvision.camera.CameraFrameProcessor
import com.qianmo.ruralvision.camera.ImageProxyBitmapConverter
import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.debug.DebugCapture
import com.qianmo.ruralvision.debug.DebugCaptureWriter
import com.qianmo.ruralvision.domain.DriveStateEvaluator
import com.qianmo.ruralvision.inference.DetectionModuleFactory
import com.qianmo.ruralvision.inference.DetectionRuntimeSetup
import com.qianmo.ruralvision.inference.DetectionTensorInspector
import com.qianmo.ruralvision.inference.SegmentationEngine
import com.qianmo.ruralvision.postprocess.MaskPostProcessor
import com.qianmo.ruralvision.pipeline.LatestFramePerceptionCoordinator
import com.qianmo.ruralvision.render.OverlayView
import com.qianmo.ruralvision.tts.WarningTtsManager
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    companion object {
        private const val TAG = "RuralVision"
        private const val ANALYZER_SKIP_LOG_INTERVAL = 30L
        private const val EXTRA_TRIGGER_DEBUG_CAPTURE = "trigger_debug_capture"
    }

    private lateinit var previewView: PreviewView
    private lateinit var overlayView: OverlayView

    private val frameProcessor = CameraFrameProcessor()
    private val bitmapConverter = ImageProxyBitmapConverter()
    private lateinit var warningTtsManager: WarningTtsManager
    private var segmentationEngine: SegmentationEngine? = null
    private var coordinator: LatestFramePerceptionCoordinator? = null
    private lateinit var detectionSetup: DetectionRuntimeSetup
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var debugCaptureExecutor: ExecutorService
    private lateinit var debugCaptureWriter: DebugCaptureWriter
    private var previewUseCase: Preview? = null
    private var analysisUseCase: ImageAnalysis? = null
    private var powerManager: PowerManager? = null
    private var thermalStatusListener: PowerManager.OnThermalStatusChangedListener? = null
    private var analyzerSkippedFrames = 0L

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startCamera()
        } else {
            Toast.makeText(this, getString(R.string.camera_permission_denied), Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configureWindow()
        setContentView(R.layout.activity_main)

        previewView = findViewById(R.id.previewView)
        previewView.implementationMode = PreviewView.ImplementationMode.PERFORMANCE
        overlayView = findViewById(R.id.overlayView)
        val debugCaptureButton: Button = findViewById(R.id.debugCaptureButton)
        cameraExecutor = Executors.newSingleThreadExecutor()
        debugCaptureExecutor = Executors.newSingleThreadExecutor()
        warningTtsManager = WarningTtsManager(this)
        detectionSetup = DetectionModuleFactory.createDefault(this)
        debugCaptureWriter = DebugCaptureWriter(this)

        debugCaptureButton.setOnClickListener {
            val queued = coordinator?.requestDebugCapture() == true
            val messageRes = if (queued) {
                R.string.debug_capture_queued
            } else {
                R.string.debug_capture_unavailable
            }
            Toast.makeText(this, getString(messageRes), Toast.LENGTH_SHORT).show()
        }
        installInsetHandling(debugCaptureButton)
        hideSystemBars()

        logDetectionTensorReportIfNeeded()
        setupPipeline()
        maybeQueueDebugCaptureFromIntent(intent)
        registerThermalMonitoring()

        if (hasCameraPermission()) {
            startCamera()
        } else {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun setupPipeline() {
        try {
            segmentationEngine = SegmentationEngine(this)
            coordinator = LatestFramePerceptionCoordinator(
                frameProcessor = frameProcessor,
                segmentationEngine = segmentationEngine!!,
                maskPostProcessor = MaskPostProcessor(),
                driveStateEvaluator = DriveStateEvaluator(),
                overlayView = overlayView,
                warningTtsManager = warningTtsManager,
                detectionModule = detectionSetup.module,
                detectionRuntimeSetup = detectionSetup,
                onDebugCaptureReady = ::saveDebugCapture
            )
            if (detectionSetup.requested && !detectionSetup.ready) {
                overlayView.updateOverlay(
                    OverlayView.OverlayState(
                        statusText = getString(R.string.detection_not_ready),
                        perfText = getString(R.string.runtime_not_started),
                        voiceEnabled = warningTtsManager.isEnabled(),
                        voiceStatusText = warningTtsManager.statusText(),
                        modeText = detectionSetup.modeText,
                        detectionStateText = detectionSetup.stateText,
                        segmentationDetailText = buildEvidenceLine(
                            "分割",
                            segmentationEngine?.runtimeLabel ?: "未启动",
                            segmentationEngine?.activeModelName ?: AppConfig.Segmentation.MODEL_NAME
                        ),
                        detectionDetailText = buildEvidenceLine(
                            "检测",
                            detectionSetup.stateText,
                            detectionSetup.runtimeLabel,
                            detectionSetup.modelName
                        )
                    )
                )
                Toast.makeText(this, getString(R.string.detection_not_ready), Toast.LENGTH_LONG).show()
            }
        } catch (ex: Exception) {
            overlayView.updateOverlay(
                OverlayView.OverlayState(
                    statusText = getString(R.string.segmentation_model_missing),
                    perfText = getString(R.string.runtime_not_started),
                    voiceEnabled = warningTtsManager.isEnabled(),
                    voiceStatusText = warningTtsManager.statusText(),
                    modeText = detectionSetup.modeText,
                    detectionStateText = detectionSetup.stateText,
                    segmentationDetailText = buildEvidenceLine(
                        "分割",
                        "未启动",
                        AppConfig.Segmentation.MODEL_NAME
                    ),
                    detectionDetailText = buildEvidenceLine(
                        "检测",
                        detectionSetup.stateText,
                        detectionSetup.runtimeLabel,
                        detectionSetup.modelName
                    )
                )
            )
            Toast.makeText(this, getString(R.string.segmentation_model_missing), Toast.LENGTH_LONG).show()
        }
    }

    private fun logDetectionTensorReportIfNeeded() {
        if (!AppConfig.Detection.ENABLED || !AppConfig.Detection.LOG_TENSOR_SHAPES) return
        try {
            val report = DetectionTensorInspector.inspectModel(this)
            Log.i(TAG, report)
        } catch (ex: Exception) {
            Log.w(TAG, "检测模型张量检查失败: ${ex.message}")
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            bindUseCases(cameraProvider)
        }, ContextCompat.getMainExecutor(this))
    }

    private fun bindUseCases(cameraProvider: ProcessCameraProvider) {
        val targetRotation = currentTargetRotation()
        val preview = Preview.Builder()
            .setTargetRotation(targetRotation)
            .build()
            .also {
            it.setSurfaceProvider(previewView.surfaceProvider)
        }

        val analysis = ImageAnalysis.Builder()
            .setTargetRotation(targetRotation)
            .setTargetResolution(Size(AppConfig.Camera.ANALYSIS_WIDTH, AppConfig.Camera.ANALYSIS_HEIGHT))
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
            .build()
            .also { imageAnalysis ->
                imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                    try {
                        if (coordinator?.canAcceptFrame() == false) {
                            analyzerSkippedFrames += 1
                            if (analyzerSkippedFrames % ANALYZER_SKIP_LOG_INTERVAL == 0L) {
                                Log.i(TAG, "Analyzer skipped $analyzerSkippedFrames frames because coordinator is busy.")
                            }
                            return@setAnalyzer
                        }
                        val bitmap = bitmapConverter.toBitmap(imageProxy)
                        coordinator?.submitFrame(
                            frame = bitmap,
                            rotationDegrees = imageProxy.imageInfo.rotationDegrees,
                            mirrorX = false
                        )
                    } catch (ex: Exception) {
                        Log.e(TAG, "Analyzer failed to submit frame", ex)
                    } finally {
                        imageProxy.close()
                    }
                }
            }

        val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
        previewUseCase = preview
        analysisUseCase = analysis
        cameraProvider.unbindAll()
        cameraProvider.bindToLifecycle(
            this,
            cameraSelector,
            preview,
            analysis
        )
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    override fun onResume() {
        super.onResume()
        hideSystemBars()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        maybeQueueDebugCaptureFromIntent(intent)
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        hideSystemBars()
        previewView.post {
            updateUseCaseTargetRotation()
            overlayView.requestLayout()
            previewView.requestLayout()
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            hideSystemBars()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterThermalMonitoring()
        coordinator?.shutdown()
        cameraExecutor.shutdownNow()
        debugCaptureExecutor.shutdownNow()
    }

    private fun updateUseCaseTargetRotation() {
        val rotation = currentTargetRotation()
        previewUseCase?.targetRotation = rotation
        analysisUseCase?.targetRotation = rotation
    }

    private fun currentTargetRotation(): Int {
        return previewView.display?.rotation ?: Surface.ROTATION_0
    }

    private fun saveDebugCapture(capture: DebugCapture) {
        debugCaptureExecutor.execute {
            try {
                val captureDir = debugCaptureWriter.save(capture)
                Log.i(TAG, "Saved debug capture to ${captureDir.absolutePath}")
                runOnUiThread {
                    Toast.makeText(
                        this,
                        getString(R.string.debug_capture_saved, captureDir.name),
                        Toast.LENGTH_LONG
                    ).show()
                }
            } catch (ex: Exception) {
                Log.e(TAG, "Failed to save debug capture", ex)
                runOnUiThread {
                    Toast.makeText(this, getString(R.string.debug_capture_save_failed), Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun maybeQueueDebugCaptureFromIntent(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_TRIGGER_DEBUG_CAPTURE, false) != true) return
        intent.removeExtra(EXTRA_TRIGGER_DEBUG_CAPTURE)
        if (queueDebugCapture()) return

        previewView.postDelayed(
            {
                queueDebugCapture()
            },
            1200L
        )
    }

    private fun queueDebugCapture(): Boolean {
        val queued = coordinator?.requestDebugCapture() == true
        Log.i(TAG, "Debug capture requested from intent: queued=$queued")
        return queued
    }

    private fun registerThermalMonitoring() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return
        val manager = getSystemService(PowerManager::class.java) ?: return
        powerManager = manager
        coordinator?.updateThermalStatus(manager.currentThermalStatus)
        val listener = PowerManager.OnThermalStatusChangedListener { status ->
            Log.i(TAG, "Thermal status changed: ${thermalStatusLabel(status)}")
            coordinator?.updateThermalStatus(status)
        }
        thermalStatusListener = listener
        manager.addThermalStatusListener(listener)
    }

    private fun unregisterThermalMonitoring() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return
        val manager = powerManager ?: return
        val listener = thermalStatusListener ?: return
        manager.removeThermalStatusListener(listener)
        thermalStatusListener = null
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

    private fun configureWindow() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            window.attributes = window.attributes.apply {
                layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            }
        }
    }

    private fun hideSystemBars() {
        val controller = WindowInsetsControllerCompat(window, window.decorView)
        controller.hide(WindowInsetsCompat.Type.systemBars())
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
    }

    private fun installInsetHandling(debugCaptureButton: View) {
        val overlaySafePadding = dp(20)
        ViewCompat.setOnApplyWindowInsetsListener(overlayView) { view, insets ->
            val systemInsets = insets.getInsets(
                WindowInsetsCompat.Type.displayCutout() or WindowInsetsCompat.Type.systemBars()
            )
            view.setPadding(
                systemInsets.left + overlaySafePadding,
                systemInsets.top + overlaySafePadding,
                systemInsets.right + overlaySafePadding,
                systemInsets.bottom + overlaySafePadding
            )
            insets
        }

        val buttonParams = debugCaptureButton.layoutParams as ViewGroup.MarginLayoutParams
        val baseLeft = buttonParams.leftMargin
        val baseTop = buttonParams.topMargin
        val baseRight = buttonParams.rightMargin
        val baseBottom = buttonParams.bottomMargin
        ViewCompat.setOnApplyWindowInsetsListener(debugCaptureButton) { view, insets ->
            val systemInsets = insets.getInsets(
                WindowInsetsCompat.Type.displayCutout() or WindowInsetsCompat.Type.systemBars()
            )
            val params = view.layoutParams as ViewGroup.MarginLayoutParams
            params.leftMargin = baseLeft + systemInsets.left
            params.topMargin = baseTop + systemInsets.top
            params.rightMargin = baseRight + systemInsets.right
            params.bottomMargin = baseBottom + systemInsets.bottom
            view.layoutParams = params
            insets
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
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
}
