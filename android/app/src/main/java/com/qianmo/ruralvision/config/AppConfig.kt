package com.qianmo.ruralvision.config

object AppConfig {
    object Segmentation {
        const val GPU_MODEL_NAME = "segmentation_fp16_192.tflite"
        const val CPU_MODEL_NAME = "segmentation_dynamic_range_192.tflite"
        const val MODEL_NAME = CPU_MODEL_NAME
        const val USE_GPU_IF_AVAILABLE = true
        const val ALLOW_UNSUPPORTED_GPU = true
        const val USE_NNAPI_IF_AVAILABLE = false
        const val INPUT_SIZE = 192
        const val THRESHOLD = 0.5f
        const val ENABLE_MORPH_CLOSE = false
        const val NARROW_ROAD_RATIO = 0.18f
        const val CENTER_SAFE_RATIO = 0.55f
    }

    object Camera {
        const val ANALYSIS_WIDTH = 480
        const val ANALYSIS_HEIGHT = 360
    }

    object Detection {
        const val BACKEND_AUTO = "auto"
        const val BACKEND_ONNX = "onnx"
        const val BACKEND_TFLITE = "tflite"
        const val ENABLED = true
        const val BACKEND = BACKEND_TFLITE
        const val MODEL_NAME = "detection.tflite"
        const val ONNX_MODEL_NAME = "detection_512.onnx"
        const val USE_GPU_IF_AVAILABLE = true
        const val ALLOW_UNSUPPORTED_GPU = true
        const val REQUIRE_GPU_RUNTIME = true
        const val USE_NNAPI_IF_AVAILABLE = false
        const val USE_ONNX_NNAPI_IF_AVAILABLE = true
        const val USE_ONNX_XNNPACK_IF_AVAILABLE = true
        const val DEFAULT_INPUT_SIZE = 512
        const val SCORE_THRESHOLD = 0.35f
        const val IOU_THRESHOLD = 0.45f
        const val RUN_EVERY_N_FRAMES = 6
        const val SLOW_INFERENCE_THRESHOLD_MS = 300L
        const val SLOW_INFERENCE_BACKOFF_FRAMES = 12L
        const val SLOW_INFERENCE_MEDIUM_THRESHOLD_MS = 450L
        const val SLOW_INFERENCE_MEDIUM_BACKOFF_FRAMES = 18L
        const val SLOW_INFERENCE_HIGH_THRESHOLD_MS = 650L
        const val SLOW_INFERENCE_HIGH_BACKOFF_FRAMES = 24L
        const val SLOW_INFERENCE_EXTREME_THRESHOLD_MS = 1200L
        const val SLOW_INFERENCE_EXTREME_BACKOFF_FRAMES = 36L
        const val LOG_TENSOR_SHAPES = false

        object Classes {
            const val TWO_WHEELER = 0
            const val PEDESTRIAN = 1
            const val ANIMAL = 2
            const val BARRIER = 3
            const val POTHOLE = 4
            const val TRICYCLE = 5
        }
    }

    object Runtime {
        const val NUM_THREADS = 4
        const val TARGET_FPS = 15
        const val MIN_ACCEPTABLE_FPS = 12
        const val TTS_INTERVAL_MS = 4000L
        const val ENABLE_SUSTAINED_PACING = true
        const val MAX_PROCESSING_FPS_CPU = 4.0f
        const val THERMAL_LIGHT_MAX_FPS_CPU = 3.5f
        const val THERMAL_MODERATE_MAX_FPS_CPU = 3.0f
        const val THERMAL_SEVERE_MAX_FPS_CPU = 2.0f
        const val THERMAL_CRITICAL_MAX_FPS_CPU = 1.0f
        const val MAX_PROCESSING_FPS_GPU = 12.0f
        const val THERMAL_LIGHT_MAX_FPS_GPU = 10.0f
        const val THERMAL_MODERATE_MAX_FPS_GPU = 8.0f
        const val THERMAL_SEVERE_MAX_FPS_GPU = 6.0f
        const val THERMAL_CRITICAL_MAX_FPS_GPU = 2.0f
    }

    object WarningPriority {
        const val ROAD_EDGE = 100
        const val NEAR_OBSTACLE = 90
        const val ANIMAL = 80
        const val VEHICLE = 75
        const val PEDESTRIAN = 70
        const val POTHOLE = 60
        const val ROAD_NARROW = 50
    }

    object WarningHeuristics {
        const val CENTER_MIN_X = 0.25f
        const val CENTER_MAX_X = 0.75f
        const val OBSTACLE_MIN_CENTER_Y = 0.35f

        // Single-camera distance proxy for vehicles:
        // warn only when the box is roughly in front of the user and large/low enough in frame.
        const val VEHICLE_WARN_CENTER_MIN_X = 0.28f
        const val VEHICLE_WARN_CENTER_MAX_X = 0.72f
        const val VEHICLE_WARN_BOTTOM_MIN_Y = 0.58f
        const val VEHICLE_WARN_HEIGHT_MIN = 0.18f
        const val VEHICLE_WARN_WIDTH_MIN = 0.10f
    }
}
