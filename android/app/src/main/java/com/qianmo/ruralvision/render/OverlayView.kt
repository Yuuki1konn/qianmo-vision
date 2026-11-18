package com.qianmo.ruralvision.render

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.text.TextPaint
import android.text.TextUtils
import android.util.AttributeSet
import android.view.View
import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import kotlin.math.max
import kotlin.math.min

class OverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    data class OverlayState(
        val maskData: ByteArray? = null,
        val maskWidth: Int = 0,
        val maskHeight: Int = 0,
        val boxes: List<BoxPostProcessor.Box> = emptyList(),
        val statusText: String = "前方道路正常",
        val perfText: String = "识别中",
        val voiceEnabled: Boolean = true,
        val voiceStatusText: String = "语音初始化中",
        val modeText: String = "普通模式",
        val detectionStateText: String = "未启用检测",
        val segmentationDetailText: String = "分割: 未启动",
        val detectionDetailText: String = "检测: 未启用"
    )

    private var overlayState = OverlayState()
    private val drawRect = Rect()
    private val cardRect = RectF()
    private val chipRect = RectF()
    private val boxRect = RectF()
    private var maskBitmapCache: Bitmap? = null
    private var maskPixelsCache = IntArray(0)
    private val density = resources.displayMetrics.density
    private val scaledDensity = resources.displayMetrics.scaledDensity
    private val cornerRadius = dp(24f)

    private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = dp(2.5f)
    }
    private val maskPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        alpha = 120
        isFilterBitmap = true
    }
    private val cardPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(192, 8, 15, 24)
        style = Paint.Style.FILL
    }
    private val cardStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(64, 255, 255, 255)
        style = Paint.Style.STROKE
        strokeWidth = dp(1f)
    }
    private val titleChipPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(235, 21, 98, 126)
        style = Paint.Style.FILL
    }
    private val statusAccentPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val statusTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = sp(22f)
        isFakeBoldText = true
    }
    private val compactStatusTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = sp(18f)
        isFakeBoldText = true
    }
    private val perfTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(245, 250, 255)
        textSize = sp(18f)
        isFakeBoldText = true
    }
    private val compactPerfTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(245, 250, 255)
        textSize = sp(15f)
        isFakeBoldText = true
    }
    private val metaTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(192, 217, 233)
        textSize = sp(13f)
    }
    private val compactMetaTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(192, 217, 233)
        textSize = sp(11f)
    }
    private val chipTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = sp(12f)
        isFakeBoldText = true
    }
    private val compactChipTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = sp(10f)
        isFakeBoldText = true
    }
    private val boxLabelTextPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = sp(11f)
        isFakeBoldText = true
    }
    private val boxLabelFillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    fun updateOverlay(state: OverlayState) {
        overlayState = state
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        drawMask(canvas)
        drawBoxes(canvas)
        drawTopStatus(canvas)
        drawBottomStatus(canvas)
    }

    private fun drawMask(canvas: Canvas) {
        val maskData = overlayState.maskData ?: return
        if (overlayState.maskWidth <= 0 || overlayState.maskHeight <= 0) return
        val mask = buildMaskBitmap(maskData, overlayState.maskWidth, overlayState.maskHeight) ?: return
        drawRect.set(0, 0, width, height)
        canvas.drawBitmap(mask, null, drawRect, maskPaint)
    }

    private fun buildMaskBitmap(maskData: ByteArray, width: Int, height: Int): Bitmap? {
        val requiredPixels = width * height
        if (requiredPixels <= 0 || maskData.size < requiredPixels) return null

        if (maskPixelsCache.size != requiredPixels) {
            maskPixelsCache = IntArray(requiredPixels)
        }
        val cachedBitmap = maskBitmapCache
        if (cachedBitmap == null || cachedBitmap.width != width || cachedBitmap.height != height) {
            maskBitmapCache = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        }

        val color = Color.argb(110, 0, 200, 120)
        for (i in 0 until requiredPixels) {
            maskPixelsCache[i] = if (maskData[i].toInt() != 0) color else Color.TRANSPARENT
        }
        val bitmap = maskBitmapCache ?: return null
        bitmap.setPixels(maskPixelsCache, 0, width, 0, 0, width, height)
        return bitmap
    }

    private fun drawBoxes(canvas: Canvas) {
        for (box in overlayState.boxes) {
            val color = classColor(box.clsId)
            boxPaint.color = color

            val left = box.x1 * width
            val top = box.y1 * height
            val right = box.x2 * width
            val bottom = box.y2 * height
            canvas.drawRect(left, top, right, bottom, boxPaint)

            val label = "${classLabel(box.clsId)} ${"%.0f".format(box.score * 100)}%"
            val labelWidth = boxLabelTextPaint.measureText(label)
            val labelHeight = dp(22f)
            val labelPadding = dp(8f)
            val labelLeft = left.coerceAtLeast(paddingLeft.toFloat())
            val labelTop = (top - labelHeight - dp(6f)).coerceAtLeast(paddingTop.toFloat())
            boxRect.set(
                labelLeft,
                labelTop,
                min(labelLeft + labelWidth + labelPadding * 2, width - paddingRight.toFloat()),
                labelTop + labelHeight
            )
            boxLabelFillPaint.color = Color.argb(220, Color.red(color), Color.green(color), Color.blue(color))
            canvas.drawRoundRect(boxRect, dp(11f), dp(11f), boxLabelFillPaint)
            canvas.drawText(
                label,
                boxRect.left + labelPadding,
                boxRect.centerY() + boxLabelTextPaint.textSize * 0.34f,
                boxLabelTextPaint
            )
        }
    }

    private fun drawTopStatus(canvas: Canvas) {
        val landscape = isLandscape()
        val left = paddingLeft.toFloat()
        val top = paddingTop.toFloat()
        val availableWidth = width - paddingLeft.toFloat() - paddingRight.toFloat()
        val cardWidth = if (landscape) {
            min(availableWidth * 0.56f, dp(360f))
        } else {
            availableWidth
        }
        val right = left + cardWidth
        val cardHeight = if (landscape) dp(118f) else dp(150f)
        val perfPaint = if (landscape) compactPerfTextPaint else perfTextPaint
        val metaPaint = if (landscape) compactMetaTextPaint else metaTextPaint
        val chipPaint = if (landscape) compactChipTextPaint else chipTextPaint

        cardRect.set(left, top, right, top + cardHeight)
        canvas.drawRoundRect(cardRect, cornerRadius, cornerRadius, cardPaint)
        canvas.drawRoundRect(cardRect, cornerRadius, cornerRadius, cardStrokePaint)

        chipRect.set(
            left + if (landscape) dp(12f) else dp(14f),
            top + if (landscape) dp(12f) else dp(14f),
            left + if (landscape) dp(86f) else dp(120f),
            top + if (landscape) dp(34f) else dp(40f)
        )
        canvas.drawRoundRect(chipRect, dp(13f), dp(13f), titleChipPaint)
        canvas.drawText(
            "阡陌智行",
            chipRect.left + if (landscape) dp(10f) else dp(12f),
            chipRect.centerY() + chipPaint.textSize * 0.34f,
            chipPaint
        )

        val line1Y = top + if (landscape) dp(50f) else dp(62f)
        val line2Y = top + if (landscape) dp(68f) else dp(86f)
        val line3Y = top + if (landscape) dp(86f) else dp(110f)
        val line4Y = top + if (landscape) dp(104f) else dp(134f)
        val textLeft = left + if (landscape) dp(14f) else dp(16f)
        val maxTextWidth = cardRect.width() - if (landscape) dp(24f) else dp(32f)
        canvas.drawText(
            ellipsize(overlayState.perfText, perfPaint, maxTextWidth),
            textLeft,
            line1Y,
            perfPaint
        )
        canvas.drawText(
            ellipsize("${overlayState.modeText} · ${overlayState.voiceStatusText}", metaPaint, maxTextWidth),
            textLeft,
            line2Y,
            metaPaint
        )
        canvas.drawText(
            ellipsize(overlayState.segmentationDetailText, metaPaint, maxTextWidth),
            textLeft,
            line3Y,
            metaPaint
        )
        canvas.drawText(
            ellipsize(overlayState.detectionDetailText, metaPaint, maxTextWidth),
            textLeft,
            line4Y,
            metaPaint
        )
    }

    private fun drawBottomStatus(canvas: Canvas) {
        val landscape = isLandscape()
        val left = paddingLeft.toFloat()
        val availableWidth = width - paddingLeft.toFloat() - paddingRight.toFloat()
        val cardWidth = if (landscape) {
            min(availableWidth * 0.54f, dp(320f))
        } else {
            availableWidth
        }
        val right = left + cardWidth
        val bottom = height - paddingBottom.toFloat()
        val cardHeight = if (landscape) dp(82f) else dp(104f)
        val minTop = paddingTop.toFloat() + if (landscape) dp(110f) else dp(140f)
        val top = max(bottom - cardHeight, minTop)
        val accentColor = statusColor(overlayState.statusText)
        val statusPaint = if (landscape) compactStatusTextPaint else statusTextPaint
        val metaPaint = if (landscape) compactMetaTextPaint else metaTextPaint

        statusAccentPaint.color = accentColor
        cardRect.set(left, top, right, bottom)
        canvas.drawRoundRect(cardRect, cornerRadius, cornerRadius, cardPaint)
        canvas.drawRoundRect(cardRect, cornerRadius, cornerRadius, cardStrokePaint)

        chipRect.set(
            left + if (landscape) dp(14f) else dp(16f),
            top + if (landscape) dp(14f) else dp(18f),
            left + if (landscape) dp(58f) else dp(78f),
            top + if (landscape) dp(58f) else dp(72f)
        )
        canvas.drawRoundRect(chipRect, dp(18f), dp(18f), statusAccentPaint)

        val labelColor = Color.argb(240, 255, 255, 255)
        val indicatorPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = labelColor
            style = Paint.Style.FILL
        }
        canvas.drawCircle(chipRect.centerX(), chipRect.centerY(), dp(8f), indicatorPaint)

        val textLeft = chipRect.right + if (landscape) dp(12f) else dp(16f)
        val titleY = top + if (landscape) dp(30f) else dp(38f)
        val statusY = top + if (landscape) dp(58f) else dp(74f)
        val maxWidth = right - textLeft - if (landscape) dp(12f) else dp(16f)
        canvas.drawText("当前提示", textLeft, titleY, metaPaint)
        canvas.drawText(
            ellipsize(overlayState.statusText, statusPaint, maxWidth),
            textLeft,
            statusY,
            statusPaint
        )
    }

    private fun ellipsize(text: String, paint: TextPaint, maxWidth: Float): String {
        if (maxWidth <= 0f) return text
        return TextUtils.ellipsize(text, paint, maxWidth, TextUtils.TruncateAt.END).toString()
    }

    private fun classLabel(clsId: Int): String {
        return when (clsId) {
            0 -> "两轮车"
            1 -> "行人"
            2 -> "动物"
            3 -> "障碍"
            4 -> "坑洼"
            5 -> "三轮车"
            else -> "目标$clsId"
        }
    }

    private fun classColor(clsId: Int): Int {
        return when (clsId) {
            0 -> Color.rgb(30, 136, 229)
            1 -> Color.rgb(67, 160, 71)
            2 -> Color.rgb(255, 167, 38)
            3 -> Color.rgb(229, 57, 53)
            4 -> Color.rgb(141, 110, 99)
            5 -> Color.rgb(142, 36, 170)
            else -> Color.rgb(0, 188, 212)
        }
    }

    private fun statusColor(statusText: String): Int {
        return when {
            statusText.contains("边缘") -> Color.rgb(239, 83, 80)
            statusText.contains("变窄") -> Color.rgb(255, 179, 0)
            else -> Color.rgb(0, 200, 120)
        }
    }

    private fun isLandscape(): Boolean = width > height

    private fun dp(value: Float): Float = value * density

    private fun sp(value: Float): Float = value * scaledDensity
}
