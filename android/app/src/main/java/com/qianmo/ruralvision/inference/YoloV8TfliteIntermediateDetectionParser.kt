package com.qianmo.ruralvision.inference

import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import org.tensorflow.lite.DataType
import java.nio.ByteBuffer
import java.nio.ByteOrder

// 适配 TFLite 中间输出：
// output0: [1, 4, count] DFL 解码后的 l/t/r/b 距离
// output1: [1, numClasses, count] sigmoid 后的类别分数
class YoloV8TfliteIntermediateDetectionParser(
    private val numClasses: Int,
    private val scoreThreshold: Float,
    private val iouThreshold: Float,
    private val inputSize: Int
) : DetectionOutputParser {
    private data class OutputSpec(
        val index: Int,
        val shape: IntArray
    )

    private val boxPostProcessor = BoxPostProcessor()
    private var dflSpec: OutputSpec? = null
    private var clsSpec: OutputSpec? = null
    private var anchorX: FloatArray = floatArrayOf()
    private var anchorY: FloatArray = floatArrayOf()
    private var strideValues: FloatArray = floatArrayOf()

    override fun createOutputMap(engine: DetectionEngine): MutableMap<Int, Any> {
        dflSpec = null
        clsSpec = null
        val outputs = mutableMapOf<Int, Any>()

        for (index in 0 until engine.getOutputCount()) {
            if (engine.getOutputDataType(index) != DataType.FLOAT32) {
                return mutableMapOf()
            }

            val shape = engine.getOutputShape(index)
            if (shape.size != 3 || shape[0] != 1) {
                continue
            }

            when (shape[1]) {
                4 -> dflSpec = OutputSpec(index, shape)
                numClasses -> clsSpec = OutputSpec(index, shape)
            }
        }

        val dfl = dflSpec ?: return mutableMapOf()
        val cls = clsSpec ?: return mutableMapOf()
        if (dfl.shape[2] != cls.shape[2]) {
            return mutableMapOf()
        }

        if (!buildAnchors(dfl.shape[2])) {
            return mutableMapOf()
        }

        outputs[dfl.index] = createBuffer(dfl.shape)
        outputs[cls.index] = createBuffer(cls.shape)
        return outputs
    }

    override fun parse(outputs: Map<Int, Any>): List<BoxPostProcessor.Box> {
        val dfl = dflSpec ?: return emptyList()
        val cls = clsSpec ?: return emptyList()
        val dflBuffer = outputs[dfl.index] as? ByteBuffer ?: return emptyList()
        val clsBuffer = outputs[cls.index] as? ByteBuffer ?: return emptyList()

        val dflValues = dflBuffer.toFloatArray()
        val clsValues = clsBuffer.toFloatArray()
        return decode(dflValues, clsValues, dfl.shape[2])
    }

    private fun createBuffer(shape: IntArray): ByteBuffer {
        val elementCount = shape.fold(1) { acc, dim -> acc * dim.coerceAtLeast(1) }
        return ByteBuffer.allocateDirect(elementCount * 4).order(ByteOrder.nativeOrder())
    }

    private fun buildAnchors(candidateCount: Int): Boolean {
        val xAnchors = FloatArray(candidateCount)
        val yAnchors = FloatArray(candidateCount)
        val strides = FloatArray(candidateCount)
        var index = 0

        for (stride in intArrayOf(8, 16, 32)) {
            if (inputSize % stride != 0) {
                return false
            }
            val grid = inputSize / stride
            repeat(grid) { y ->
                repeat(grid) { x ->
                    if (index >= candidateCount) {
                        return false
                    }
                    xAnchors[index] = x + 0.5f
                    yAnchors[index] = y + 0.5f
                    strides[index] = stride.toFloat()
                    index++
                }
            }
        }

        if (index != candidateCount) {
            return false
        }

        anchorX = xAnchors
        anchorY = yAnchors
        strideValues = strides
        return true
    }

    private fun decode(
        dflValues: FloatArray,
        clsValues: FloatArray,
        candidateCount: Int
    ): List<BoxPostProcessor.Box> {
        val boxes = ArrayList<BoxPostProcessor.Box>(candidateCount)

        for (candidateIndex in 0 until candidateCount) {
            val left = dflValues[candidateIndex]
            val top = dflValues[candidateCount + candidateIndex]
            val right = dflValues[candidateCount * 2 + candidateIndex]
            val bottom = dflValues[candidateCount * 3 + candidateIndex]

            val stride = strideValues[candidateIndex]
            val centerX = (anchorX[candidateIndex] + (right - left) / 2f) * stride
            val centerY = (anchorY[candidateIndex] + (bottom - top) / 2f) * stride
            val width = (left + right) * stride
            val height = (top + bottom) * stride
            if (width <= 0f || height <= 0f) {
                continue
            }

            var bestClassId = -1
            var bestClassScore = 0f
            for (classIndex in 0 until numClasses) {
                val score = clsValues[classIndex * candidateCount + candidateIndex]
                if (score > bestClassScore) {
                    bestClassScore = score
                    bestClassId = classIndex
                }
            }

            if (bestClassId < 0 || bestClassScore < scoreThreshold) {
                continue
            }

            val normalized = normalizeBox(centerX, centerY, width, height)
            if (normalized[2] <= normalized[0] || normalized[3] <= normalized[1]) {
                continue
            }

            boxes.add(
                BoxPostProcessor.Box(
                    x1 = normalized[0],
                    y1 = normalized[1],
                    x2 = normalized[2],
                    y2 = normalized[3],
                    score = bestClassScore,
                    clsId = bestClassId
                )
            )
        }

        return boxPostProcessor.nms(boxes, iouThreshold)
    }

    private fun normalizeBox(cx: Float, cy: Float, w: Float, h: Float): FloatArray {
        val centerX = cx / inputSize.toFloat()
        val centerY = cy / inputSize.toFloat()
        val boxW = w / inputSize.toFloat()
        val boxH = h / inputSize.toFloat()

        val x1 = (centerX - boxW / 2f).coerceIn(0f, 1f)
        val y1 = (centerY - boxH / 2f).coerceIn(0f, 1f)
        val x2 = (centerX + boxW / 2f).coerceIn(0f, 1f)
        val y2 = (centerY + boxH / 2f).coerceIn(0f, 1f)
        return floatArrayOf(x1, y1, x2, y2)
    }

    private fun ByteBuffer.toFloatArray(): FloatArray {
        rewind()
        val floatBuffer = order(ByteOrder.nativeOrder()).asFloatBuffer()
        val array = FloatArray(floatBuffer.remaining())
        floatBuffer.get(array)
        return array
    }
}
