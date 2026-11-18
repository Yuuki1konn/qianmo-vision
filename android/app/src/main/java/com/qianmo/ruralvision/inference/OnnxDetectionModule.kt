package com.qianmo.ruralvision.inference

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtException
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import android.content.Context
import android.util.Log
import com.qianmo.ruralvision.camera.TensorLayout
import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.channels.FileChannel

class OnnxDetectionModule(
    private val environment: OrtEnvironment,
    private val session: OrtSession,
    private val decoder: YoloV8TensorDecoder,
    override val inputSize: Int,
    private val runtimeName: String
) : DetectionModule {
    companion object {
        private const val TAG = "OnnxDetectionModule"

        fun fromAssets(
            context: Context,
            modelName: String = AppConfig.Detection.ONNX_MODEL_NAME
        ): OnnxDetectionModule {
            val environment = OrtEnvironment.getEnvironment()
            val modelBuffer = loadModelBuffer(context, modelName)
            val sessionSetup = createSession(environment, modelBuffer)
            val inputName = sessionSetup.session.inputNames.first()
            val inputInfo = sessionSetup.session.inputInfo[inputName]?.info as? TensorInfo
            val inputSize = inferInputSize(inputInfo)
            val decoder = YoloV8TensorDecoder(
                numClasses = 6,
                scoreThreshold = AppConfig.Detection.SCORE_THRESHOLD,
                iouThreshold = AppConfig.Detection.IOU_THRESHOLD,
                inputSize = inputSize,
                coordinatesNormalized = false
            )
            return OnnxDetectionModule(
                environment = environment,
                session = sessionSetup.session,
                decoder = decoder,
                inputSize = inputSize,
                runtimeName = sessionSetup.runtimeName
            )
        }

        private fun createSession(
            environment: OrtEnvironment,
            modelBuffer: ByteBuffer
        ): SessionSetup {
            for ((runtimeName, options) in sessionOptionCandidates()) {
                try {
                    val session = environment.createSession(modelBuffer.duplicate(), options)
                    options.close()
                    Log.i(TAG, "ONNX detection runtime selected: $runtimeName")
                    return SessionSetup(session = session, runtimeName = runtimeName)
                } catch (ex: Exception) {
                    Log.w(TAG, "ONNX detection runtime $runtimeName failed", ex)
                    try {
                        options.close()
                    } catch (_: Exception) {
                    }
                }
            }
            throw IllegalStateException("No ONNX runtime could be initialized")
        }

        private fun sessionOptionCandidates(): List<Pair<String, OrtSession.SessionOptions>> {
            val candidates = ArrayList<Pair<String, OrtSession.SessionOptions>>()
            if (AppConfig.Detection.USE_ONNX_NNAPI_IF_AVAILABLE) {
                buildSessionOptions("NNAPI") { addNnapi() }?.let(candidates::add)
            }
            if (AppConfig.Detection.USE_ONNX_XNNPACK_IF_AVAILABLE) {
                buildSessionOptions("XNNPACK") { addXnnpack(emptyMap()) }?.let(candidates::add)
            }
            buildSessionOptions("CPU")?.let(candidates::add)
            return candidates
        }

        private fun buildSessionOptions(
            runtimeName: String,
            providerConfig: (OrtSession.SessionOptions.() -> Unit)? = null
        ): Pair<String, OrtSession.SessionOptions>? {
            return try {
                val options = OrtSession.SessionOptions().apply {
                    setIntraOpNumThreads(AppConfig.Runtime.NUM_THREADS)
                    setInterOpNumThreads(1)
                    setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
                    setMemoryPatternOptimization(true)
                    setCPUArenaAllocator(true)
                    providerConfig?.invoke(this)
                }
                runtimeName to options
            } catch (ex: Exception) {
                Log.w(TAG, "Failed to prepare ONNX session options for $runtimeName", ex)
                null
            }
        }

        private fun inferInputSize(info: TensorInfo?): Int {
            val spatialDims = info
                ?.shape
                ?.map { it.toInt() }
                ?.filter { it > 4 }
                .orEmpty()
            return spatialDims.minOrNull() ?: AppConfig.Detection.DEFAULT_INPUT_SIZE
        }

        private fun loadModelBuffer(context: Context, modelName: String): ByteBuffer {
            return try {
                context.assets.openFd(modelName).use { descriptor ->
                    FileInputStream(descriptor.fileDescriptor).channel.use { channel ->
                        channel.map(
                            FileChannel.MapMode.READ_ONLY,
                            descriptor.startOffset,
                            descriptor.declaredLength
                        )
                    }
                }
            } catch (ex: Exception) {
                Log.w(TAG, "Falling back to heap-backed ONNX asset load for $modelName", ex)
                val modelBytes = context.assets.open(modelName).use { it.readBytes() }
                ByteBuffer.allocateDirect(modelBytes.size)
                    .order(ByteOrder.nativeOrder())
                    .apply {
                        put(modelBytes)
                        rewind()
                    }
            }
        }
    }

    private data class SessionSetup(
        val session: OrtSession,
        val runtimeName: String
    )

    private val inputName: String = session.inputNames.first()
    private val outputName: String = session.outputNames.first()
    private val outputShape: IntArray = session.outputInfo[outputName]
        ?.info
        ?.let { info -> (info as TensorInfo).shape.map { dim -> dim.toInt() }.toIntArray() }
        ?: intArrayOf(1, 10, 10164)

    override val available: Boolean = true
    override val tensorLayout: TensorLayout = TensorLayout.NCHW
    override val backendLabel: String = "ONNX-$runtimeName"

    override fun detect(input: ByteBuffer): List<BoxPostProcessor.Box> {
        input.rewind()
        val tensor = OnnxTensor.createTensor(
            environment,
            input.asFloatBuffer(),
            longArrayOf(1, 3, inputSize.toLong(), inputSize.toLong())
        )
        tensor.use { onnxInput ->
            session.run(mapOf(inputName to onnxInput)).use { results ->
                val outputValue = results[0]
                val values = when (outputValue) {
                    null -> FloatArray(0)
                    is OnnxTensor -> outputValue.floatBufferToArray()
                    else -> flattenOrtValue(outputValue.value)
                }
                if (values.isEmpty()) {
                    Log.w(TAG, "ONNX detection output is empty. outputType=${outputValue?.value?.javaClass?.name}")
                }
                return decoder.decode(values, outputShape)
            }
        }
    }

    override fun close() {
        try {
            session.close()
        } catch (_: OrtException) {
        }
        environment.close()
    }
}

private fun OnnxTensor.floatBufferToArray(): FloatArray {
    val buffer = floatBuffer
    buffer.rewind()
    val array = FloatArray(buffer.remaining())
    buffer.get(array)
    return array
}

private fun flattenOrtValue(value: Any?): FloatArray {
    val size = countFloatValues(value)
    if (size == 0) return FloatArray(0)
    val output = FloatArray(size)
    fillFloatValues(value, output, 0)
    return output
}

private fun countFloatValues(value: Any?): Int {
    return when (value) {
        null -> 0
        is FloatArray -> value.size
        is FloatBuffer -> value.remaining()
        is Array<*> -> value.sumOf(::countFloatValues)
        else -> throw IllegalArgumentException("Unsupported ONNX output type: ${value.javaClass.name}")
    }
}

private fun fillFloatValues(value: Any?, output: FloatArray, startIndex: Int): Int {
    return when (value) {
        null -> startIndex
        is FloatArray -> {
            value.copyInto(output, destinationOffset = startIndex)
            startIndex + value.size
        }

        is FloatBuffer -> {
            val duplicate = value.duplicate()
            duplicate.rewind()
            val count = duplicate.remaining()
            duplicate.get(output, startIndex, count)
            startIndex + count
        }

        is Array<*> -> {
            var offset = startIndex
            value.forEach { item ->
                offset = fillFloatValues(item, output, offset)
            }
            offset
        }

        else -> throw IllegalArgumentException("Unsupported ONNX output type: ${value.javaClass.name}")
    }
}
