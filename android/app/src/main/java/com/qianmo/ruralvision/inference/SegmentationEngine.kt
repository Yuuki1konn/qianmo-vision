package com.qianmo.ruralvision.inference

import android.content.Context
import android.util.Log
import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.postprocess.MaskPostProcessor
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer

class SegmentationEngine(
    context: Context,
    modelName: String = AppConfig.Segmentation.MODEL_NAME
) {
    companion object {
        private const val TAG = "SegmentationEngine"
    }

    data class SegmentationResult(
        val width: Int,
        val height: Int,
        val binaryMask: ByteArray
    )

    private val interpreter: Interpreter
    private val delegate: GpuDelegate?
    private val postProcessor = MaskPostProcessor()
    val activeModelName: String
    val runtimeLabel: String
    val inputWidth: Int
    val inputHeight: Int
    private val outputWidth: Int
    private val outputHeight: Int
    private val outputBuffer: ByteBuffer
    private val logits: FloatArray
    private val thresholdMask: ByteArray

    init {
        val runtimeSetup = createRuntimeSetup(context, modelName)
        delegate = runtimeSetup.delegate
        interpreter = runtimeSetup.interpreter
        activeModelName = runtimeSetup.modelName
        runtimeLabel = runtimeSetup.runtimeLabel
        Log.i(TAG, "Segmentation runtime: ${runtimeSetup.runtimeLabel}, model=${runtimeSetup.modelName}")
        val inputShape = interpreter.getInputTensor(0).shape()
        inputHeight = inputShape[1]
        inputWidth = inputShape[2]
        if (inputWidth != AppConfig.Segmentation.INPUT_SIZE || inputHeight != AppConfig.Segmentation.INPUT_SIZE) {
            Log.w(
                TAG,
                "Configured input=${AppConfig.Segmentation.INPUT_SIZE}, but model expects ${inputWidth}x$inputHeight. Using model tensor shape."
            )
        }
        val outputShape = interpreter.getOutputTensor(0).shape()
        outputHeight = outputShape[1]
        outputWidth = outputShape[2]
        outputBuffer = ByteBuffer.allocateDirect(outputWidth * outputHeight * 4)
            .order(ByteOrder.nativeOrder())
        logits = FloatArray(outputWidth * outputHeight)
        thresholdMask = ByteArray(outputWidth * outputHeight)
    }

    fun run(
        input: ByteBuffer,
        threshold: Float = AppConfig.Segmentation.THRESHOLD,
        enableMorphClose: Boolean = AppConfig.Segmentation.ENABLE_MORPH_CLOSE
    ): SegmentationResult {
        input.rewind()
        outputBuffer.rewind()
        interpreter.run(input, outputBuffer)

        outputBuffer.rewind()
        outputBuffer.asFloatBuffer().get(logits)

        for (index in logits.indices) {
            thresholdMask[index] = if (sigmoid(logits[index]) >= threshold) 1 else 0
        }

        var binaryMask = thresholdMask
        if (enableMorphClose) {
            binaryMask = postProcessor.morphologyClose(binaryMask, outputWidth, outputHeight)
        }

        return SegmentationResult(
            width = outputWidth,
            height = outputHeight,
            binaryMask = binaryMask
        )
    }

    fun close() {
        interpreter.close()
        delegate?.close()
    }

    private fun loadModelFile(context: Context, modelName: String): MappedByteBuffer {
        val fileDescriptor = context.assets.openFd(modelName)
        fileDescriptor.use { afd ->
            FileInputStream(afd.fileDescriptor).channel.use { channel ->
                return channel.map(
                    java.nio.channels.FileChannel.MapMode.READ_ONLY,
                    afd.startOffset,
                    afd.declaredLength
                )
            }
        }
    }

    private fun sigmoid(x: Float): Float {
        return (1.0 / (1.0 + kotlin.math.exp(-x.toDouble()))).toFloat()
    }

    private data class RuntimeSetup(
        val modelName: String,
        val delegate: GpuDelegate?,
        val runtimeLabel: String,
        val usesNnApi: Boolean,
        val interpreter: Interpreter
    )

    private fun createRuntimeSetup(context: Context, defaultModelName: String): RuntimeSetup {
        if (!AppConfig.Segmentation.USE_GPU_IF_AVAILABLE) {
            return RuntimeSetup(
                modelName = defaultModelName,
                delegate = null,
                runtimeLabel = "CPU",
                usesNnApi = false,
                interpreter = createInterpreter(
                    context = context,
                    modelName = defaultModelName,
                    delegate = null,
                    useNnApi = false
                )
            )
        }

        val compatibilitySupported = CompatibilityList().use { compat ->
            compat.isDelegateSupportedOnThisDevice()
        }
        Log.i(TAG, "GPU CompatibilityList supported=$compatibilitySupported")
        val shouldAttemptGpu = compatibilitySupported || AppConfig.Segmentation.ALLOW_UNSUPPORTED_GPU
        if (!compatibilitySupported && AppConfig.Segmentation.ALLOW_UNSUPPORTED_GPU) {
            Log.w(TAG, "GPU CompatibilityList reports unsupported on this device; forcing GPU init by config.")
        }
        if (!shouldAttemptGpu) {
            Log.i(TAG, "Skipping GPU delegate init because CompatibilityList reported unsupported.")
        }

        val attemptedDelegate = if (shouldAttemptGpu) {
            try {
                Log.i(TAG, "Attempting GPU delegate init.")
                GpuDelegate()
            } catch (ex: Throwable) {
                Log.w(TAG, "GPU delegate init failed, fallback to CPU/optional NNAPI: ${ex.message}")
                null
            }
        } else {
            null
        }

        if (attemptedDelegate != null) {
            try {
                return RuntimeSetup(
                    modelName = AppConfig.Segmentation.GPU_MODEL_NAME,
                    delegate = attemptedDelegate,
                    runtimeLabel = "GPU",
                    usesNnApi = false,
                    interpreter = createInterpreter(
                        context = context,
                        modelName = AppConfig.Segmentation.GPU_MODEL_NAME,
                        delegate = attemptedDelegate,
                        useNnApi = false
                    )
                )
            } catch (ex: Throwable) {
                attemptedDelegate.close()
                Log.w(TAG, "GPU interpreter init failed, fallback to CPU/optional NNAPI: ${ex.message}")
            }
        }

        if (AppConfig.Segmentation.USE_NNAPI_IF_AVAILABLE && tryEnableNnApi()) {
            try {
                Log.i(TAG, "Attempting NNAPI interpreter init.")
                return RuntimeSetup(
                    modelName = AppConfig.Segmentation.CPU_MODEL_NAME,
                    delegate = null,
                    runtimeLabel = "NNAPI",
                    usesNnApi = true,
                    interpreter = createInterpreter(
                        context = context,
                        modelName = AppConfig.Segmentation.CPU_MODEL_NAME,
                        delegate = null,
                        useNnApi = true
                    )
                )
            } catch (ex: Throwable) {
                Log.w(TAG, "NNAPI interpreter init failed, fallback to CPU: ${ex.message}")
            }
        } else if (AppConfig.Segmentation.USE_NNAPI_IF_AVAILABLE) {
            Log.w(TAG, "NNAPI API unavailable on this build; fallback to CPU.")
        } else {
            Log.i(TAG, "NNAPI fallback disabled by config; using CPU when GPU is unavailable.")
        }

        return RuntimeSetup(
            modelName = AppConfig.Segmentation.CPU_MODEL_NAME,
            delegate = null,
            runtimeLabel = "CPU",
            usesNnApi = false,
            interpreter = createInterpreter(
                context = context,
                modelName = AppConfig.Segmentation.CPU_MODEL_NAME,
                delegate = null,
                useNnApi = false
            )
        )
    }

    private fun createInterpreter(
        context: Context,
        modelName: String,
        delegate: GpuDelegate?,
        useNnApi: Boolean
    ): Interpreter {
        val options = Interpreter.Options().apply {
            setNumThreads(AppConfig.Runtime.NUM_THREADS)
            setUseXNNPACK(delegate == null && !useNnApi)
            delegate?.let { addDelegate(it) }
        }
        if (useNnApi) {
            enableNnApiOn(options)
        }
        return Interpreter(loadModelFile(context, modelName), options)
    }

    private fun tryEnableNnApi(): Boolean {
        return try {
            Interpreter.Options::class.java.getMethod("setUseNNAPI", Boolean::class.javaPrimitiveType)
            true
        } catch (_: Throwable) {
            false
        }
    }

    private fun enableNnApiOn(options: Interpreter.Options) {
        Interpreter.Options::class.java
            .getMethod("setUseNNAPI", Boolean::class.javaPrimitiveType)
            .invoke(options, true)
    }
}
