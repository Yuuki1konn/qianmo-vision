package com.qianmo.ruralvision.inference

import com.qianmo.ruralvision.postprocess.BoxPostProcessor

class YoloV8TensorDecoder(
    private val numClasses: Int,
    private val scoreThreshold: Float,
    private val iouThreshold: Float,
    private val inputSize: Int,
    private val coordinatesNormalized: Boolean = false
) {
    private val boxPostProcessor = BoxPostProcessor()

    fun decode(values: FloatArray, shape: IntArray): List<BoxPostProcessor.Box> {
        if (shape.size != 3) return emptyList()
        if (shape[0] != 1) return emptyList()

        val dim1 = shape[1]
        val dim2 = shape[2]
        val attrsWithObj = numClasses + 5
        val attrsNoObj = numClasses + 4

        val channelsFirst = when {
            dim1 == attrsWithObj || dim1 == attrsNoObj -> true
            dim2 == attrsWithObj || dim2 == attrsNoObj -> false
            dim1 < dim2 -> true
            dim2 < dim1 -> false
            else -> true
        }

        val attrs = if (channelsFirst) dim1 else dim2
        val count = if (channelsFirst) dim2 else dim1
        if (attrs < attrsNoObj) return emptyList()

        val hasObjectness = attrs >= attrsWithObj
        val boxes = ArrayList<BoxPostProcessor.Box>(count)

        for (index in 0 until count) {
            val cx = readValue(values, channelsFirst, attrs, count, index, 0)
            val cy = readValue(values, channelsFirst, attrs, count, index, 1)
            val w = readValue(values, channelsFirst, attrs, count, index, 2)
            val h = readValue(values, channelsFirst, attrs, count, index, 3)
            if (w <= 0f || h <= 0f) continue

            val objectness = if (hasObjectness) {
                readValue(values, channelsFirst, attrs, count, index, 4)
            } else {
                1f
            }

            var bestClassId = -1
            var bestClassScore = 0f
            val classOffset = if (hasObjectness) 5 else 4
            for (clsIndex in 0 until numClasses) {
                val clsScore = readValue(values, channelsFirst, attrs, count, index, classOffset + clsIndex)
                if (clsScore > bestClassScore) {
                    bestClassScore = clsScore
                    bestClassId = clsIndex
                }
            }

            if (bestClassId < 0) continue
            val score = objectness * bestClassScore
            if (score < scoreThreshold) continue

            val normalized = normalizeBox(cx, cy, w, h)
            if (normalized[2] <= normalized[0] || normalized[3] <= normalized[1]) continue

            boxes.add(
                BoxPostProcessor.Box(
                    x1 = normalized[0],
                    y1 = normalized[1],
                    x2 = normalized[2],
                    y2 = normalized[3],
                    score = score,
                    clsId = bestClassId
                )
            )
        }

        return boxPostProcessor.nms(boxes, iouThreshold)
    }

    private fun readValue(
        values: FloatArray,
        channelsFirst: Boolean,
        attrs: Int,
        count: Int,
        candidateIndex: Int,
        attrIndex: Int
    ): Float {
        val flatIndex = if (channelsFirst) {
            attrIndex * count + candidateIndex
        } else {
            candidateIndex * attrs + attrIndex
        }
        return values.getOrElse(flatIndex) { 0f }
    }

    private fun normalizeBox(cx: Float, cy: Float, w: Float, h: Float): FloatArray {
        val scale = if (coordinatesNormalized) 1f else inputSize.toFloat()
        val centerX = cx / scale
        val centerY = cy / scale
        val boxW = w / scale
        val boxH = h / scale

        val x1 = (centerX - boxW / 2f).coerceIn(0f, 1f)
        val y1 = (centerY - boxH / 2f).coerceIn(0f, 1f)
        val x2 = (centerX + boxW / 2f).coerceIn(0f, 1f)
        val y2 = (centerY + boxH / 2f).coerceIn(0f, 1f)

        return floatArrayOf(x1, y1, x2, y2)
    }
}
