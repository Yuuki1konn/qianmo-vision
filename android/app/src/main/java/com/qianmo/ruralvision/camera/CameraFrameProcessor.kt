package com.qianmo.ruralvision.camera

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import java.nio.ByteBuffer
import java.nio.ByteOrder

class CameraFrameProcessor {
    data class PreprocessResult(
        val inputBuffer: ByteBuffer,
        val previewBitmap: Bitmap
    )

    private data class CacheKey(
        val inputWidth: Int,
        val inputHeight: Int,
        val tensorLayout: TensorLayout
    )

    private data class PreprocessCache(
        val bitmap: Bitmap,
        val canvas: Canvas,
        val pixels: IntArray,
        val inputBuffer: ByteBuffer
    )

    private val caches = mutableMapOf<CacheKey, PreprocessCache>()
    private val drawMatrix = Matrix()
    private val sourceBounds = RectF()
    private val transformedBounds = RectF()
    private val bitmapPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)

    fun preprocess(
        frame: Bitmap,
        inputWidth: Int = 640,
        inputHeight: Int = inputWidth,
        rotationDegrees: Int = 0,
        mirrorX: Boolean = false,
        tensorLayout: TensorLayout = TensorLayout.NHWC
    ): PreprocessResult {
        val cache = getOrCreateCache(inputWidth, inputHeight, tensorLayout)
        drawIntoBitmap(
            frame = frame,
            target = cache,
            rotationDegrees = rotationDegrees,
            mirrorX = mirrorX
        )
        val inputBuffer = bitmapToFloatBuffer(cache, tensorLayout)
        return PreprocessResult(
            inputBuffer = inputBuffer,
            previewBitmap = cache.bitmap
        )
    }

    private fun getOrCreateCache(
        inputWidth: Int,
        inputHeight: Int,
        tensorLayout: TensorLayout
    ): PreprocessCache {
        val key = CacheKey(inputWidth, inputHeight, tensorLayout)
        return caches.getOrPut(key) {
            val bitmap = Bitmap.createBitmap(inputWidth, inputHeight, Bitmap.Config.ARGB_8888)
            val buffer = ByteBuffer.allocateDirect(inputWidth * inputHeight * 3 * 4)
                .order(ByteOrder.nativeOrder())
            PreprocessCache(
                bitmap = bitmap,
                canvas = Canvas(bitmap),
                pixels = IntArray(inputWidth * inputHeight),
                inputBuffer = buffer
            )
        }
    }

    private fun drawIntoBitmap(
        frame: Bitmap,
        target: PreprocessCache,
        rotationDegrees: Int,
        mirrorX: Boolean
    ) {
        target.bitmap.eraseColor(Color.TRANSPARENT)

        drawMatrix.reset()
        sourceBounds.set(0f, 0f, frame.width.toFloat(), frame.height.toFloat())
        transformedBounds.set(sourceBounds)

        val centerX = frame.width / 2f
        val centerY = frame.height / 2f
        if (mirrorX) {
            drawMatrix.postScale(-1f, 1f, centerX, centerY)
        }
        if (rotationDegrees != 0) {
            drawMatrix.postRotate(rotationDegrees.toFloat(), centerX, centerY)
        }

        drawMatrix.mapRect(transformedBounds)
        drawMatrix.postTranslate(-transformedBounds.left, -transformedBounds.top)
        drawMatrix.postScale(
            target.bitmap.width / transformedBounds.width(),
            target.bitmap.height / transformedBounds.height()
        )

        target.canvas.drawBitmap(frame, drawMatrix, bitmapPaint)
    }

    private fun bitmapToFloatBuffer(
        cache: PreprocessCache,
        tensorLayout: TensorLayout = TensorLayout.NHWC
    ): ByteBuffer {
        val bitmap = cache.bitmap
        val pixels = cache.pixels
        val buffer = cache.inputBuffer
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        buffer.rewind()

        when (tensorLayout) {
            TensorLayout.NHWC -> {
                for (pixel in pixels) {
                    val r = ((pixel shr 16) and 0xFF) / 255.0f
                    val g = ((pixel shr 8) and 0xFF) / 255.0f
                    val b = (pixel and 0xFF) / 255.0f
                    buffer.putFloat(r)
                    buffer.putFloat(g)
                    buffer.putFloat(b)
                }
            }

            TensorLayout.NCHW -> {
                for (channel in 0 until 3) {
                    for (pixel in pixels) {
                        val value = when (channel) {
                            0 -> ((pixel shr 16) and 0xFF) / 255.0f
                            1 -> ((pixel shr 8) and 0xFF) / 255.0f
                            else -> (pixel and 0xFF) / 255.0f
                        }
                        buffer.putFloat(value)
                    }
                }
            }
        }
        buffer.rewind()
        return buffer
    }
}
