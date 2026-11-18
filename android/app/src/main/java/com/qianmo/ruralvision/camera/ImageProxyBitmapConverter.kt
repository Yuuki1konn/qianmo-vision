package com.qianmo.ruralvision.camera

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer

class ImageProxyBitmapConverter {
    companion object {
        private const val CACHE_POOL_SIZE = 3
    }

    private data class RgbaCache(
        val bitmap: Bitmap,
        val packedBytes: ByteArray,
        val packedBuffer: ByteBuffer
    )

    private var rgbaCaches = emptyArray<RgbaCache>()
    private var rgbaCacheIndex = 0

    fun toBitmap(image: ImageProxy): Bitmap {
        return if (image.planes.size == 1 && image.planes[0].pixelStride == 4) {
            rgba8888ToBitmap(image)
        } else {
            yuvToBitmap(image)
        }
    }

    private fun rgba8888ToBitmap(image: ImageProxy): Bitmap {
        val plane = image.planes[0]
        val width = image.width
        val height = image.height
        val rowStride = plane.rowStride
        val expectedStride = width * 4
        val cache = getOrCreateRgbaCache(width, height)
        val bitmap = cache.bitmap
        val buffer = plane.buffer
        buffer.rewind()

        if (rowStride == expectedStride) {
            bitmap.copyPixelsFromBuffer(buffer)
            return bitmap
        }

        copyRows(buffer, cache.packedBytes, rowStride, expectedStride, height)
        cache.packedBuffer.rewind()
        bitmap.copyPixelsFromBuffer(cache.packedBuffer)
        return bitmap
    }

    private fun getOrCreateRgbaCache(width: Int, height: Int): RgbaCache {
        val needsReset = rgbaCaches.isEmpty() || rgbaCaches.any { cache ->
            cache.bitmap.width != width ||
                cache.bitmap.height != height
        }
        if (needsReset) {
            rgbaCaches = Array(CACHE_POOL_SIZE) {
                val packedBytes = ByteArray(width * height * 4)
                RgbaCache(
                    bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888),
                    packedBytes = packedBytes,
                    packedBuffer = ByteBuffer.wrap(packedBytes)
                )
            }
            rgbaCacheIndex = 0
        }

        val cache = rgbaCaches[rgbaCacheIndex]
        rgbaCacheIndex = (rgbaCacheIndex + 1) % rgbaCaches.size
        return cache
    }

    private fun copyRows(
        source: ByteBuffer,
        destination: ByteArray,
        sourceRowStride: Int,
        destinationRowStride: Int,
        height: Int
    ) {
        for (row in 0 until height) {
            source.position(row * sourceRowStride)
            source.get(destination, row * destinationRowStride, destinationRowStride)
        }
    }

    private fun yuvToBitmap(image: ImageProxy): Bitmap {
        val nv21 = yuv420888ToNv21(image)
        val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
        val out = ByteArrayOutputStream()
        yuvImage.compressToJpeg(Rect(0, 0, image.width, image.height), 85, out)
        val bytes = out.toByteArray()
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }

    private fun yuv420888ToNv21(image: ImageProxy): ByteArray {
        val yBuffer = image.planes[0].buffer
        val uBuffer = image.planes[1].buffer
        val vBuffer = image.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)
        yBuffer.get(nv21, 0, ySize)

        val chromaRowStride = image.planes[1].rowStride
        val chromaPixelStride = image.planes[1].pixelStride
        val width = image.width
        val height = image.height
        var offset = ySize

        if (chromaPixelStride == 2 && chromaRowStride == width) {
            val vBytes = ByteArray(vSize)
            val uBytes = ByteArray(uSize)
            vBuffer.get(vBytes)
            uBuffer.get(uBytes)
            for (i in uBytes.indices) {
                nv21[offset++] = vBytes[i]
                nv21[offset++] = uBytes[i]
            }
            return nv21
        }

        val vBytes = ByteArray(vSize)
        val uBytes = ByteArray(uSize)
        vBuffer.get(vBytes)
        uBuffer.get(uBytes)
        val chromaHeight = height / 2
        val chromaWidth = width / 2

        for (row in 0 until chromaHeight) {
            for (col in 0 until chromaWidth) {
                val vuIndex = row * chromaRowStride + col * chromaPixelStride
                nv21[offset++] = vBytes[vuIndex]
                nv21[offset++] = uBytes[vuIndex]
            }
        }
        return nv21
    }
}
