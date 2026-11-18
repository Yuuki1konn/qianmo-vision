package com.qianmo.ruralvision.postprocess

import kotlin.math.max
import kotlin.math.min

class BoxPostProcessor {
    data class Box(
        val x1: Float,
        val y1: Float,
        val x2: Float,
        val y2: Float,
        val score: Float,
        val clsId: Int
    )

    fun nms(boxes: List<Box>, iouThreshold: Float = 0.5f): List<Box> {
        val sorted = boxes.sortedByDescending { it.score }.toMutableList()
        val keep = mutableListOf<Box>()

        while (sorted.isNotEmpty()) {
            val cur = sorted.removeAt(0)
            keep.add(cur)
            val remain = mutableListOf<Box>()
            for (b in sorted) {
                if (b.clsId != cur.clsId || iou(cur, b) < iouThreshold) {
                    remain.add(b)
                }
            }
            sorted.clear()
            sorted.addAll(remain)
        }
        return keep
    }

    private fun iou(a: Box, b: Box): Float {
        val xx1 = max(a.x1, b.x1)
        val yy1 = max(a.y1, b.y1)
        val xx2 = min(a.x2, b.x2)
        val yy2 = min(a.y2, b.y2)

        val w = max(0f, xx2 - xx1)
        val h = max(0f, yy2 - yy1)
        val inter = w * h

        val areaA = (a.x2 - a.x1) * (a.y2 - a.y1)
        val areaB = (b.x2 - b.x1) * (b.y2 - b.y1)
        return inter / (areaA + areaB - inter + 1e-6f)
    }
}
