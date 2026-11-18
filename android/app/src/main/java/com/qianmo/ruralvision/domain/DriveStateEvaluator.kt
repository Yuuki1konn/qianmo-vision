package com.qianmo.ruralvision.domain

import com.qianmo.ruralvision.config.AppConfig
import com.qianmo.ruralvision.postprocess.BoxPostProcessor
import com.qianmo.ruralvision.tts.WarningTtsManager
import kotlin.math.max

class DriveStateEvaluator {
    data class DriveState(
        val statusText: String,
        val warningEvent: WarningTtsManager.WarningEvent? = null,
        val drivableRatio: Float,
        val centerSafe: Boolean,
        val roadNarrow: Boolean
    )

    fun evaluate(
        mask: ByteArray,
        width: Int,
        height: Int,
        boxes: List<BoxPostProcessor.Box> = emptyList()
    ): DriveState {
        val drivableRatio = computeDrivableRatio(mask)
        val centerSafe = isCenterSafe(mask, width, height)
        val roadNarrow = isRoadNarrow(mask, width, height)
        val obstacleEvent = nearestObstacleEvent(boxes)

        if (!centerSafe) {
            return DriveState(
                statusText = "靠近道路边缘",
                warningEvent = WarningTtsManager.WarningEvent(
                    key = "road_edge",
                    text = "请回到道路中间",
                    priority = AppConfig.WarningPriority.ROAD_EDGE
                ),
                drivableRatio = drivableRatio,
                centerSafe = false,
                roadNarrow = roadNarrow
            )
        }

        if (obstacleEvent != null) {
            return DriveState(
                statusText = obstacleEvent.text.removeSuffix("，请注意").removeSuffix("，请减速").removeSuffix("，请避让"),
                warningEvent = obstacleEvent,
                drivableRatio = drivableRatio,
                centerSafe = true,
                roadNarrow = roadNarrow
            )
        }

        if (roadNarrow) {
            return DriveState(
                statusText = "前方可行驶区域变窄",
                warningEvent = WarningTtsManager.WarningEvent(
                    key = "road_narrow",
                    text = "前方道路变窄，请小心通行",
                    priority = AppConfig.WarningPriority.ROAD_NARROW
                ),
                drivableRatio = drivableRatio,
                centerSafe = true,
                roadNarrow = true
            )
        }

        return DriveState(
            statusText = "前方道路正常",
            drivableRatio = drivableRatio,
            centerSafe = true,
            roadNarrow = false
        )
    }

    private fun computeDrivableRatio(mask: ByteArray): Float {
        if (mask.isEmpty()) return 0f
        val positives = mask.count { it.toInt() != 0 }
        return positives.toFloat() / mask.size.toFloat()
    }

    private fun isCenterSafe(mask: ByteArray, width: Int, height: Int): Boolean {
        val centerX = width / 2
        val bandTop = max((height * AppConfig.Segmentation.CENTER_SAFE_RATIO).toInt(), 0)
        val bandBottom = height - 1
        var positives = 0
        var total = 0

        for (y in bandTop..bandBottom) {
            for (x in (centerX - width / 10).coerceAtLeast(0)..(centerX + width / 10).coerceAtMost(width - 1)) {
                total += 1
                if (mask[y * width + x].toInt() != 0) positives += 1
            }
        }
        if (total == 0) return true
        return positives.toFloat() / total.toFloat() >= 0.35f
    }

    private fun isRoadNarrow(mask: ByteArray, width: Int, height: Int): Boolean {
        val horizonY = (height * 0.58f).toInt().coerceIn(0, height - 1)
        var left = -1
        var right = -1
        for (x in 0 until width) {
            if (mask[horizonY * width + x].toInt() != 0) {
                if (left == -1) left = x
                right = x
            }
        }
        if (left == -1 || right == -1) return true
        val roadWidthRatio = (right - left + 1).toFloat() / width.toFloat()
        return roadWidthRatio < AppConfig.Segmentation.NARROW_ROAD_RATIO
    }

    private fun nearestObstacleEvent(boxes: List<BoxPostProcessor.Box>): WarningTtsManager.WarningEvent? {
        if (boxes.isEmpty()) return null
        val centerCandidates = boxes.filter { box ->
            val cx = (box.x1 + box.x2) / 2f
            val cy = (box.y1 + box.y2) / 2f
            cx in AppConfig.WarningHeuristics.CENTER_MIN_X..AppConfig.WarningHeuristics.CENTER_MAX_X &&
                cy >= AppConfig.WarningHeuristics.OBSTACLE_MIN_CENTER_Y
        }
        if (centerCandidates.isEmpty()) return null

        val best = centerCandidates.maxByOrNull { it.score * ((it.y2 - it.y1).coerceAtLeast(0.01f)) } ?: return null
        return when (best.clsId) {
            AppConfig.Detection.Classes.TWO_WHEELER,
            AppConfig.Detection.Classes.TRICYCLE -> {
                if (isVehicleWarningCandidate(best)) {
                    WarningTtsManager.WarningEvent(
                        key = "vehicle",
                        text = "前方有车辆，请注意保持距离",
                        priority = AppConfig.WarningPriority.VEHICLE
                    )
                } else {
                    null
                }
            }

            AppConfig.Detection.Classes.PEDESTRIAN -> {
                WarningTtsManager.WarningEvent("pedestrian", "前方有行人，请注意", AppConfig.WarningPriority.PEDESTRIAN)
            }

            AppConfig.Detection.Classes.ANIMAL -> {
                WarningTtsManager.WarningEvent("animal", "前方有动物，请减速", AppConfig.WarningPriority.ANIMAL)
            }

            AppConfig.Detection.Classes.POTHOLE -> {
                WarningTtsManager.WarningEvent("pothole", "前方有坑洼，请避让", AppConfig.WarningPriority.POTHOLE)
            }

            AppConfig.Detection.Classes.BARRIER -> {
                WarningTtsManager.WarningEvent("barrier", "注意，前方障碍物较近", AppConfig.WarningPriority.NEAR_OBSTACLE)
            }

            else -> null
        }
    }

    private fun isVehicleWarningCandidate(box: BoxPostProcessor.Box): Boolean {
        val centerX = (box.x1 + box.x2) / 2f
        val bottomY = box.y2
        val boxHeight = (box.y2 - box.y1).coerceAtLeast(0f)
        val boxWidth = (box.x2 - box.x1).coerceAtLeast(0f)

        return centerX in AppConfig.WarningHeuristics.VEHICLE_WARN_CENTER_MIN_X..AppConfig.WarningHeuristics.VEHICLE_WARN_CENTER_MAX_X &&
            bottomY >= AppConfig.WarningHeuristics.VEHICLE_WARN_BOTTOM_MIN_Y &&
            boxHeight >= AppConfig.WarningHeuristics.VEHICLE_WARN_HEIGHT_MIN &&
            boxWidth >= AppConfig.WarningHeuristics.VEHICLE_WARN_WIDTH_MIN
    }
}
