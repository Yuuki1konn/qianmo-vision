package com.qianmo.ruralvision.inference

import android.content.Context
import android.content.res.AssetManager
import android.util.Log
import com.qianmo.ruralvision.config.AppConfig

object DetectionModuleFactory {
    private const val TAG = "DetectionModuleFactory"

    fun createDefault(context: Context): DetectionRuntimeSetup {
        if (!AppConfig.Detection.ENABLED) {
            return unavailableSetup(
                requested = false,
                stateText = "检测未启用",
                runtimeLabel = "未启用",
                modelName = AppConfig.Detection.MODEL_NAME
            )
        }

        val failures = mutableListOf<String>()
        for (backend in configuredBackendCandidates()) {
            val modelName = modelNameFor(backend)
            if (!assetExists(context.assets, modelName)) {
                failures += "$backend: 缺少$modelName"
                continue
            }

            try {
                val module = when (backend) {
                    AppConfig.Detection.BACKEND_TFLITE -> createTfliteModule(context)
                    AppConfig.Detection.BACKEND_ONNX -> OnnxDetectionModule.fromAssets(context, modelName)
                    else -> null
                }

                if (module == null) {
                    failures += "$backend: 不支持的后端"
                    continue
                }

                if (!module.available) {
                    module.close()
                    failures += "$backend: 模块不可用"
                    continue
                }

                if (backend == AppConfig.Detection.BACKEND_TFLITE && !isAcceptedTfliteRuntime(module.backendLabel)) {
                    module.close()
                    failures += "$backend: 运行时${module.backendLabel}不符合 TFLite-GPU 验收要求"
                    continue
                }

                if (module.available) {
                    return DetectionRuntimeSetup(
                        module = module,
                        requested = true,
                        ready = true,
                        modeText = "分割 + 检测",
                        stateText = "检测已启用",
                        runtimeLabel = module.backendLabel,
                        modelName = modelName
                    )
                }

                module.close()
                failures += "$backend: 模块不可用"
            } catch (ex: Exception) {
                failures += "$backend: ${ex.message ?: ex.javaClass.simpleName}"
                Log.w(TAG, "Detection backend $backend init failed", ex)
            }
        }

        if (failures.isNotEmpty()) {
            Log.w(TAG, "Detection setup failed across all backends: ${failures.joinToString(" | ")}")
        }
        return unavailableSetup(
            requested = true,
            stateText = "检测未就绪",
            runtimeLabel = "未加载",
            modelName = defaultModelName(context)
        )
    }

    fun defaultModelName(context: Context): String {
        for (backend in configuredBackendCandidates()) {
            val modelName = modelNameFor(backend)
            if (assetExists(context.assets, modelName)) {
                return modelName
            }
        }
        return modelNameFor(AppConfig.Detection.BACKEND)
    }

    private fun createTfliteModule(context: Context): DetectionModule {
        val engine = DetectionEngine(context)
        val inputSize = inferInputSize(engine.getInputShape())
        val parser = createTfliteParser(engine, inputSize)
        return TfLiteDetectionModule(engine, parser, inputSize)
    }

    private fun createTfliteParser(
        engine: DetectionEngine,
        inputSize: Int
    ): DetectionOutputParser {
        val outputShapes = (0 until engine.getOutputCount()).map { index ->
            engine.getOutputShape(index)
        }
        val hasIntermediateBoxes = outputShapes.any { shape ->
            shape.size == 3 && shape[0] == 1 && shape[1] == 4
        }
        val hasIntermediateClasses = outputShapes.any { shape ->
            shape.size == 3 && shape[0] == 1 && shape[1] == AppConfig.Detection.Classes.TRICYCLE + 1
        }
        return if (hasIntermediateBoxes && hasIntermediateClasses) {
            YoloV8TfliteIntermediateDetectionParser(
                numClasses = AppConfig.Detection.Classes.TRICYCLE + 1,
                scoreThreshold = AppConfig.Detection.SCORE_THRESHOLD,
                iouThreshold = AppConfig.Detection.IOU_THRESHOLD,
                inputSize = inputSize
            )
        } else {
            YoloV8TfliteDetectionParser(
                numClasses = AppConfig.Detection.Classes.TRICYCLE + 1,
                scoreThreshold = AppConfig.Detection.SCORE_THRESHOLD,
                iouThreshold = AppConfig.Detection.IOU_THRESHOLD,
                inputSize = inputSize,
                coordinatesNormalized = false
            )
        }
    }

    internal fun configuredBackendCandidates(
        preferredBackend: String = AppConfig.Detection.BACKEND
    ): List<String> {
        return when (preferredBackend) {
            AppConfig.Detection.BACKEND_ONNX -> listOf(AppConfig.Detection.BACKEND_ONNX)
            else -> listOf(AppConfig.Detection.BACKEND_TFLITE)
        }
    }

    internal fun isAcceptedTfliteRuntime(backendLabel: String): Boolean {
        return !AppConfig.Detection.REQUIRE_GPU_RUNTIME ||
            backendLabel.equals("TFLite-GPU", ignoreCase = true)
    }

    private fun modelNameFor(backend: String): String {
        return when (backend) {
            AppConfig.Detection.BACKEND_ONNX -> AppConfig.Detection.ONNX_MODEL_NAME
            else -> AppConfig.Detection.MODEL_NAME
        }
    }

    private fun assetExists(assets: AssetManager, modelName: String): Boolean {
        return try {
            assets.open(modelName).use { true }
        } catch (_: Exception) {
            false
        }
    }

    private fun inferInputSize(shape: IntArray): Int {
        val spatialDims = shape.filter { it > 4 }
        return spatialDims.minOrNull() ?: AppConfig.Detection.DEFAULT_INPUT_SIZE
    }

    private fun unavailableSetup(
        requested: Boolean,
        stateText: String,
        runtimeLabel: String,
        modelName: String
    ): DetectionRuntimeSetup {
        return DetectionRuntimeSetup(
            module = NoOpDetectionModule(),
            requested = requested,
            ready = false,
            modeText = "仅分割",
            stateText = stateText,
            runtimeLabel = runtimeLabel,
            modelName = modelName
        )
    }
}
