package com.qianmo.ruralvision.inference

data class DetectionRuntimeSetup(
    val module: DetectionModule,
    val requested: Boolean,
    val ready: Boolean,
    val modeText: String,
    val stateText: String,
    val runtimeLabel: String,
    val modelName: String
)
