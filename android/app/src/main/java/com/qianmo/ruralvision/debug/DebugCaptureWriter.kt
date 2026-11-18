package com.qianmo.ruralvision.debug

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.Environment
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DebugCaptureWriter(
    private val context: Context
) {
    private val timestampFormat = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)

    fun save(capture: DebugCapture): File {
        val rootDir = context.getExternalFilesDir(Environment.DIRECTORY_PICTURES) ?: context.filesDir
        val debugRoot = File(rootDir, "debug_captures")
        if (!debugRoot.exists()) {
            debugRoot.mkdirs()
        }

        val captureDir = File(debugRoot, timestampFormat.format(Date(capture.capturedAtMs)))
        if (!captureDir.exists()) {
            captureDir.mkdirs()
        }

        val maskBitmap = buildMaskBitmap(capture.maskData, capture.maskWidth, capture.maskHeight)
        val overlayBitmap = buildOverlayBitmap(capture.frameBitmap, maskBitmap)

        try {
            writeBitmap(File(captureDir, "frame.png"), capture.frameBitmap)
            writeBitmap(File(captureDir, "mask.png"), maskBitmap)
            writeBitmap(File(captureDir, "overlay.png"), overlayBitmap)
            writeMetadata(File(captureDir, "meta.txt"), capture)
        } finally {
            maskBitmap.recycle()
            overlayBitmap.recycle()
            capture.frameBitmap.recycle()
        }

        return captureDir
    }

    private fun buildMaskBitmap(maskData: ByteArray, width: Int, height: Int): Bitmap {
        val pixels = IntArray(width * height)
        val positiveColor = Color.rgb(0, 200, 120)
        for (index in pixels.indices) {
            pixels[index] = if (maskData[index].toInt() != 0) positiveColor else Color.BLACK
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888)
    }

    private fun buildOverlayBitmap(frameBitmap: Bitmap, maskBitmap: Bitmap): Bitmap {
        val bitmap = Bitmap.createBitmap(frameBitmap.width, frameBitmap.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawBitmap(frameBitmap, 0f, 0f, null)
        val maskPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            alpha = 110
            isFilterBitmap = false
        }
        canvas.drawBitmap(maskBitmap, 0f, 0f, maskPaint)
        return bitmap
    }

    private fun writeBitmap(file: File, bitmap: Bitmap) {
        FileOutputStream(file).use { output ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)
        }
    }

    private fun writeMetadata(file: File, capture: DebugCapture) {
        val lines = listOf(
            "captured_at_ms=${capture.capturedAtMs}",
            "frame_index=${capture.frameIndex}",
            "segmentation_runtime=${capture.segmentationRuntime}",
            "segmentation_model_name=${capture.segmentationModelName}",
            "detection_runtime=${capture.detectionRuntime}",
            "detection_model_name=${capture.detectionModelName}",
            "total_ms=${capture.totalMs}",
            "preprocess_ms=${capture.preprocessMs}",
            "segmentation_ms=${capture.segmentationMs}",
            "detection_ms=${capture.detectionMs}",
            "status_text=${capture.statusText}",
            "perf_text=${capture.perfText}",
            "mode_text=${capture.modeText}",
            "detection_state_text=${capture.detectionStateText}",
            "drivable_ratio=${capture.drivableRatio}",
            "center_safe=${capture.centerSafe}",
            "road_narrow=${capture.roadNarrow}",
            "mask_width=${capture.maskWidth}",
            "mask_height=${capture.maskHeight}"
        )
        file.writeText(lines.joinToString(separator = System.lineSeparator()))
    }
}
