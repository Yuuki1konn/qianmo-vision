package com.qianmo.ruralvision.inference

import android.content.Context
import android.util.Log
import com.qianmo.ruralvision.config.AppConfig
import org.tensorflow.lite.DataType
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import java.nio.ByteBuffer
import java.io.FileInputStream
import java.nio.MappedByteBuffer

class DetectionEngine(
    context: Context,
    modelName: String = AppConfig.Detection.MODEL_NAME
) {
    companion object {
        private const val TAG = "DetectionEngine"
    }

    private val interpreter: Interpreter
    private val delegate: GpuDelegate?
    val activeModelName: String
    val runtimeLabel: String

    init {
        val runtimeSetup = createRuntimeSetup(context, modelName)
        delegate = runtimeSetup.delegate
        interpreter = runtimeSetup.interpreter
        activeModelName = runtimeSetup.modelName
        runtimeLabel = runtimeSetup.runtimeLabel
        Log.i(TAG, "Detection runtime: ${runtimeSetup.runtimeLabel}, model=${runtimeSetup.modelName}")
    }

    fun run(input: ByteBuffer, outputs: MutableMap<Int, Any>) {
        input.rewind()
        interpreter.runForMultipleInputsOutputs(arrayOf(input), outputs)
    }

    fun getInputCount(): Int = interpreter.inputTensorCount

    fun getInputShape(index: Int = 0): IntArray = interpreter.getInputTensor(index).shape()

    fun getInputDataType(index: Int = 0): DataType = interpreter.getInputTensor(index).dataType()

    fun getOutputCount(): Int = interpreter.outputTensorCount

    fun getOutputShape(index: Int): IntArray = interpreter.getOutputTensor(index).shape()

    fun getOutputDataType(index: Int): DataType = interpreter.getOutputTensor(index).dataType()

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

    private data class RuntimeSetup(
        val modelName: String,
        val delegate: GpuDelegate?,
        val runtimeLabel: String,
        val usesNnApi: Boolean,
        val interpreter: Interpreter
    )

    private fun createRuntimeSetup(context: Context, defaultModelName: String): RuntimeSetup {
        if (!AppConfig.Detection.USE_GPU_IF_AVAILABLE) {
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
        val shouldAttemptGpu = compatibilitySupported || AppConfig.Detection.ALLOW_UNSUPPORTED_GPU
        if (!compatibilitySupported && AppConfig.Detection.ALLOW_UNSUPPORTED_GPU) {
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
                    modelName = defaultModelName,
                    delegate = attemptedDelegate,
                    runtimeLabel = "GPU",
                    usesNnApi = false,
                    interpreter = createInterpreter(
                        context = context,
                        modelName = defaultModelName,
                        delegate = attemptedDelegate,
                        useNnApi = false
                    )
                )
            } catch (ex: Throwable) {
                attemptedDelegate.close()
                Log.w(TAG, "GPU interpreter init failed, fallback to CPU/optional NNAPI: ${ex.message}")
            }
        }

        if (AppConfig.Detection.USE_NNAPI_IF_AVAILABLE && tryEnableNnApi()) {
            try {
                Log.i(TAG, "Attempting NNAPI interpreter init.")
                return RuntimeSetup(
                    modelName = defaultModelName,
                    delegate = null,
                    runtimeLabel = "NNAPI",
                    usesNnApi = true,
                    interpreter = createInterpreter(
                        context = context,
                        modelName = defaultModelName,
                        delegate = null,
                        useNnApi = true
                    )
                )
            } catch (ex: Throwable) {
                Log.w(TAG, "NNAPI interpreter init failed, fallback to CPU: ${ex.message}")
            }
        } else if (AppConfig.Detection.USE_NNAPI_IF_AVAILABLE) {
            Log.w(TAG, "NNAPI API unavailable on this build; fallback to CPU.")
        } else {
            Log.i(TAG, "NNAPI fallback disabled by config; using CPU when GPU is unavailable.")
        }

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
