package com.qianmo.ruralvision.inference

import com.qianmo.ruralvision.camera.TensorLayout
import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import java.nio.ByteBuffer

interface DetectionModule {
    val available: Boolean
    val inputSize: Int
    val tensorLayout: TensorLayout
    val backendLabel: String

    fun detect(input: ByteBuffer): List<BoxPostProcessor.Box>

    fun close()
}

class NoOpDetectionModule : DetectionModule {
    override val available: Boolean = false
    override val inputSize: Int = AppConfig.Detection.DEFAULT_INPUT_SIZE
    override val tensorLayout: TensorLayout = TensorLayout.NHWC
    override val backendLabel: String = "未启用"

    override fun detect(input: ByteBuffer): List<BoxPostProcessor.Box> = emptyList()

    override fun close() = Unit
}

class TfLiteDetectionModule(
    private val engine: DetectionEngine,
    private val parser: DetectionOutputParser,
    override val inputSize: Int
) : DetectionModule {
    private val outputs: MutableMap<Int, Any> = parser.createOutputMap(engine)

    override val available: Boolean = outputs.isNotEmpty()
    override val tensorLayout: TensorLayout = TensorLayout.NHWC
    override val backendLabel: String = "TFLite-${engine.runtimeLabel}"

    override fun detect(input: ByteBuffer): List<BoxPostProcessor.Box> {
        if (!available) return emptyList()
        outputs.values.forEach { value ->
            if (value is ByteBuffer) {
                value.rewind()
            }
        }
        engine.run(input, outputs)
        return parser.parse(outputs)
    }

    override fun close() {
        engine.close()
    }
}
