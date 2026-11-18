package com.qianmo.ruralvision.inference

import com.qianmo.ruralvision.postprocess.BoxPostProcessor

interface DetectionOutputParser {
    fun createOutputMap(engine: DetectionEngine): MutableMap<Int, Any>

    fun parse(outputs: Map<Int, Any>): List<BoxPostProcessor.Box>
}

class UnsupportedDetectionOutputParser : DetectionOutputParser {
    override fun createOutputMap(engine: DetectionEngine): MutableMap<Int, Any> {
        return mutableMapOf()
    }

    override fun parse(outputs: Map<Int, Any>): List<BoxPostProcessor.Box> {
        return emptyList()
    }
}
