package com.qianmo.ruralvision.inference

import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import android.content.Context

object DetectionTensorInspector {
    fun inspectModel(
        context: Context,
        modelName: String? = null
    ): String {
        val resolvedModelName = modelName ?: DetectionModuleFactory.defaultModelName(context)
        return when {
            resolvedModelName.endsWith(".onnx", ignoreCase = true) -> inspectOnnxModel(context, resolvedModelName)
            else -> inspectTfliteModel(context, resolvedModelName)
        }
    }

    private fun inspectTfliteModel(context: Context, modelName: String): String {
        val engine = DetectionEngine(context, modelName)
        return try {
            buildString {
                appendLine("检测模型张量检查")
                appendLine("backend=TFLite")
                appendLine("model=$modelName")
                appendLine("inputs=${engine.getInputCount()}")
                repeat(engine.getInputCount()) { index ->
                    appendLine(
                        "input[$index]: dtype=${engine.getInputDataType(index)} shape=${engine.getInputShape(index).contentToString()}"
                    )
                }
                appendLine("outputs=${engine.getOutputCount()}")
                repeat(engine.getOutputCount()) { index ->
                    appendLine(
                        "output[$index]: dtype=${engine.getOutputDataType(index)} shape=${engine.getOutputShape(index).contentToString()}"
                    )
                }
            }.trim()
        } finally {
            engine.close()
        }
    }

    private fun inspectOnnxModel(context: Context, modelName: String): String {
        val env = OrtEnvironment.getEnvironment()
        val options = OrtSession.SessionOptions()
        val modelBytes = context.assets.open(modelName).use { it.readBytes() }
        val modelBuffer = java.nio.ByteBuffer.allocateDirect(modelBytes.size)
            .order(java.nio.ByteOrder.nativeOrder())
        modelBuffer.put(modelBytes)
        modelBuffer.rewind()
        val session = env.createSession(modelBuffer, options)
        return try {
            buildString {
                appendLine("检测模型张量检查")
                appendLine("backend=ONNX")
                appendLine("model=$modelName")
                appendLine("inputs=${session.inputInfo.size}")
                session.inputInfo.entries.forEach { (name, nodeInfo) ->
                    val info = nodeInfo.info as TensorInfo
                    appendLine("input[$name]: dtype=${info.type} shape=${info.shape.contentToString()}")
                }
                appendLine("outputs=${session.outputInfo.size}")
                session.outputInfo.entries.forEach { (name, nodeInfo) ->
                    val info = nodeInfo.info as TensorInfo
                    appendLine("output[$name]: dtype=${info.type} shape=${info.shape.contentToString()}")
                }
            }.trim()
        } finally {
            session.close()
            env.close()
        }
    }
}
