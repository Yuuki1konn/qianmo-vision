package com.qianmo.ruralvision.inference

import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import org.tensorflow.lite.DataType
import java.nio.ByteBuffer
import java.nio.ByteOrder

// 适配 Ultralytics YOLOv8 常见 TFLite 导出格式：
// [1, attrs, count] 或 [1, count, attrs]，坐标默认按输入尺寸像素值归一化到 0..1。
class YoloV8TfliteDetectionParser(
    private val numClasses: Int,
    private val scoreThreshold: Float,
    private val iouThreshold: Float,
    private val inputSize: Int,
    private val coordinatesNormalized: Boolean = false
) : DetectionOutputParser {
    private val decoder = YoloV8TensorDecoder(
        numClasses = numClasses,
        scoreThreshold = scoreThreshold,
        iouThreshold = iouThreshold,
        inputSize = inputSize,
        coordinatesNormalized = coordinatesNormalized
    )
    private var outputShape: IntArray = intArrayOf()

    override fun createOutputMap(engine: DetectionEngine): MutableMap<Int, Any> {
        if (engine.getOutputCount() < 1) return mutableMapOf()
        if (engine.getOutputDataType(0) != DataType.FLOAT32) return mutableMapOf()

        outputShape = engine.getOutputShape(0)
        if (outputShape.size !in 3..4) return mutableMapOf()

        val elementCount = outputShape.fold(1) { acc, dim -> acc * dim.coerceAtLeast(1) }
        val buffer = ByteBuffer.allocateDirect(elementCount * 4).order(ByteOrder.nativeOrder())
        return mutableMapOf(0 to buffer)
    }

    override fun parse(outputs: Map<Int, Any>): List<BoxPostProcessor.Box> {
        val outputBuffer = outputs[0] as? ByteBuffer ?: return emptyList()
        if (outputShape.isEmpty()) return emptyList()

        val tensorShape = if (outputShape.size == 4 && outputShape[0] == 1 && outputShape[1] == 1) {
            intArrayOf(outputShape[0], outputShape[2], outputShape[3])
        } else {
            outputShape
        }

        val values = outputBuffer.toFloatArray()
        return parseTensor(values, tensorShape)
    }

    private fun parseTensor(values: FloatArray, shape: IntArray): List<BoxPostProcessor.Box> {
        return decoder.decode(values, shape)
    }

    private fun ByteBuffer.toFloatArray(): FloatArray {
        rewind()
        val floatBuffer = order(ByteOrder.nativeOrder()).asFloatBuffer()
        val array = FloatArray(floatBuffer.remaining())
        floatBuffer.get(array)
        return array
    }
}
