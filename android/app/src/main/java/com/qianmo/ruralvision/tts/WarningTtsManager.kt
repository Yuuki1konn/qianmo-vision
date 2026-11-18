package com.qianmo.ruralvision.tts

import android.media.AudioAttributes
import android.media.AudioManager
import android.media.ToneGenerator
import android.speech.tts.TextToSpeech
import android.util.Log
import android.content.Context
import java.util.Locale

class WarningTtsManager(context: Context) : TextToSpeech.OnInitListener {
    companion object {
        private const val TAG = "WarningTtsManager"
        private const val READY_UTTERANCE_ID = "voice_ready"
    }

    data class WarningEvent(
        val key: String,
        val text: String,
        val priority: Int
    )

    private val tts = TextToSpeech(context, this)
    private val fallbackTone = ToneGenerator(AudioManager.STREAM_MUSIC, 85)
    private var ready = false
    private var initFailed = false
    private val lastSpeakAtMs = mutableMapOf<String, Long>()
    private var enabled = true
    private var lastPriority = Int.MIN_VALUE
    private var pendingEvent: WarningEvent? = null
    private var readyAnnounced = false

    override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            ready = false
            initFailed = true
            Log.w(TAG, "TextToSpeech init failed with status=$status")
            return
        }

        tts.setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build()
        )
        tts.setSpeechRate(0.95f)
        tts.setPitch(1.0f)

        val locale = resolveLocale()
        ready = locale != null
        initFailed = !ready
        if (!ready) {
            Log.w(TAG, "No supported TTS locale found for warning prompts.")
            return
        }

        if (enabled && !readyAnnounced) {
            readyAnnounced = true
            speakImmediate("语音提示已开启", READY_UTTERANCE_ID)
        }
        pendingEvent?.let { event ->
            pendingEvent = null
            speakWarning(event, minIntervalMs = 0L)
        }
    }

    fun setEnabled(value: Boolean) {
        enabled = value
        if (!enabled) {
            tts.stop()
        }
    }

    fun isReady(): Boolean = ready

    fun isEnabled(): Boolean = enabled

    fun statusText(): String {
        return when {
            !enabled -> "语音已关闭"
            initFailed -> "提示音模式"
            ready -> "语音已就绪"
            else -> "语音初始化中"
        }
    }

    fun speakWarning(
        event: WarningEvent,
        minIntervalMs: Long = 4000L,
        allowInterrupt: Boolean = true
    ) {
        if (!enabled) return
        if (!ready) {
            if (initFailed) {
                playFallbackTone(event, minIntervalMs)
                return
            }
            if (pendingEvent == null || event.priority >= (pendingEvent?.priority ?: Int.MIN_VALUE)) {
                pendingEvent = event
            }
            return
        }

        val now = System.currentTimeMillis()
        val lastTime = lastSpeakAtMs[event.key] ?: 0L
        if (now - lastTime < minIntervalMs) return

        val queueMode = if (allowInterrupt || event.priority >= lastPriority) {
            TextToSpeech.QUEUE_FLUSH
        } else {
            TextToSpeech.QUEUE_ADD
        }

        lastPriority = event.priority
        lastSpeakAtMs[event.key] = now
        tts.speak(event.text, queueMode, null, event.key)
    }

    private fun speakImmediate(
        text: String,
        utteranceId: String
    ) {
        if (!ready || !enabled) return
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
    }

    private fun playFallbackTone(
        event: WarningEvent,
        minIntervalMs: Long
    ) {
        val now = System.currentTimeMillis()
        val lastTime = lastSpeakAtMs[event.key] ?: 0L
        if (now - lastTime < minIntervalMs) return

        val durationMs = when {
            event.priority >= 90 -> 260
            event.priority >= 70 -> 190
            else -> 140
        }
        lastPriority = event.priority
        lastSpeakAtMs[event.key] = now
        fallbackTone.startTone(ToneGenerator.TONE_PROP_BEEP, durationMs)
    }

    private fun resolveLocale(): Locale? {
        val candidates = listOf(
            Locale.SIMPLIFIED_CHINESE,
            Locale.CHINA,
            Locale.getDefault()
        )
        for (candidate in candidates) {
            val result = tts.setLanguage(candidate)
            if (result != TextToSpeech.LANG_MISSING_DATA && result != TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.i(TAG, "TTS language ready: ${candidate.toLanguageTag()}")
                return candidate
            }
        }
        return null
    }

    fun release() {
        tts.stop()
        tts.shutdown()
        fallbackTone.release()
    }
}
