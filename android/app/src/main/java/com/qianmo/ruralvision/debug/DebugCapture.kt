package com.qianmo.ruralvision.debug

import android.graphics.Bitmap

data class DebugCapture(
    val frameBitmap: Bitmap,
    val maskData: ByteArray,
    val maskWidth: Int,
    val maskHeight: Int,
    val frameIndex: Long,
    val totalMs: Long,
    val preprocessMs: Long,
    val segmentationMs: Long,
    val detectionMs: Long,
    val statusText: String,
    val perfText: String,
    val modeText: String,
    val detectionStateText: String,
    val drivableRatio: Float,
    val centerSafe: Boolean,
    val roadNarrow: Boolean,
    val segmentationRuntime: String,
    val segmentationModelName: String,
    val detectionRuntime: String,
    val detectionModelName: String,
    val capturedAtMs: Long = System.currentTimeMillis()
)
