package com.qianmo.ruralvision.postprocess

import android.graphics.Bitmap
import android.graphics.Color

class MaskPostProcessor {
    fun threshold(mask: FloatArray, th: Float = 0.5f): ByteArray {
        return ByteArray(mask.size) { i -> if (mask[i] >= th) 1 else 0 }
    }

    fun morphologyClose(binaryMask: ByteArray, width: Int, height: Int): ByteArray {
        // 简化版 3x3 闭运算：先膨胀后腐蚀
        val dilated = dilate(binaryMask, width, height)
        return erode(dilated, width, height)
    }

    private fun dilate(src: ByteArray, width: Int, height: Int): ByteArray {
        val dst = ByteArray(src.size)
        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                var v = 0
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        if (src[(y + dy) * width + (x + dx)].toInt() != 0) {
                            v = 1
                        }
                    }
                }
                dst[y * width + x] = v.toByte()
            }
        }
        return dst
    }

    private fun erode(src: ByteArray, width: Int, height: Int): ByteArray {
        val dst = ByteArray(src.size)
        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                var v = 1
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        if (src[(y + dy) * width + (x + dx)].toInt() == 0) {
                            v = 0
                        }
                    }
                }
                dst[y * width + x] = v.toByte()
            }
        }
        return dst
    }

    fun toOverlayBitmap(
        binaryMask: ByteArray,
        width: Int,
        height: Int,
        color: Int = Color.argb(110, 0, 200, 120)
    ): Bitmap {
        val pixels = IntArray(width * height)
        for (i in binaryMask.indices) {
            pixels[i] = if (binaryMask[i].toInt() != 0) color else Color.TRANSPARENT
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888)
    }
}
