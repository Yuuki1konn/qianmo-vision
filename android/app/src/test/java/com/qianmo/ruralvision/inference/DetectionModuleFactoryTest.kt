package com.qianmo.ruralvision.inference

import com.qianmo.ruralvision.config.AppConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DetectionModuleFactoryTest {
    @Test
    fun `default backend stays on strict tflite only`() {
        assertEquals(AppConfig.Detection.BACKEND_TFLITE, AppConfig.Detection.BACKEND)
        assertEquals(
            listOf(AppConfig.Detection.BACKEND_TFLITE),
            DetectionModuleFactory.configuredBackendCandidates(AppConfig.Detection.BACKEND)
        )
        assertEquals(
            listOf(AppConfig.Detection.BACKEND_TFLITE),
            DetectionModuleFactory.configuredBackendCandidates(AppConfig.Detection.BACKEND_AUTO)
        )
    }

    @Test
    fun `strict tflite acceptance requires gpu runtime`() {
        assertTrue(DetectionModuleFactory.isAcceptedTfliteRuntime("TFLite-GPU"))
        assertFalse(DetectionModuleFactory.isAcceptedTfliteRuntime("TFLite-CPU"))
        assertFalse(DetectionModuleFactory.isAcceptedTfliteRuntime("TFLite-NNAPI"))
    }
}
