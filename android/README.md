# Android 端集成与验收说明

本目录已经是一个可构建、可安装、可在真机上联调的 Android 工程，不再是早期的模板骨架说明页。

当前工程包含：

- `app/src/main/java` 下的实际 Kotlin 源码
- `app/src/main/res` 下的布局与资源
- `app/src/main/assets` 下的分割与检测模型（模型文件不入库，需从 Releases 下载，见根目录 README）
- `gradlew`、`gradlew.bat`、`gradle/wrapper/` 等 Gradle Wrapper 文件
- `build.gradle.kts / settings.gradle.kts / AndroidManifest.xml`

## 当前默认验收口径

软著申请前，当前工程按下面的标准验收：

- 分割与检测都以 `TFLite` 为主执行链路
- 检测默认走严格 `TFLite` 路径，不再自动回退 `ONNX`
- 真机结果优先，不以模拟器结果作为最终结论
- 运行日志、界面状态和调试抓帧元数据都必须能说明实际 runtime / model

当前默认检测配置位于 `app/src/main/java/com/qianmo/ruralvision/config/AppConfig.kt`：

- `BACKEND = BACKEND_TFLITE`
- `REQUIRE_GPU_RUNTIME = true`

这意味着检测若没有以 `TFLite-GPU` 启动成功，会直接进入“检测未就绪”状态，而不是默默切到 `ONNX`。

## 模型资产

当前主资产如下：

- `app/src/main/assets/segmentation_fp16_192.tflite`
- `app/src/main/assets/segmentation_dynamic_range_192.tflite`
- `app/src/main/assets/detection.tflite`
- `app/src/main/assets/detection_512.onnx`

说明：

- 分割主显示链路优先使用 `segmentation_fp16_192.tflite`
- 分割在设备不支持时仍允许回退到 CPU / NNAPI，但验收时要以实际 runtime 为准
- 检测验收链路以 `detection.tflite` 为准
- `detection_512.onnx` 为备用 ONNX 后端，主要用于历史调试或备用研究，不作为当前默认验收成功路径

## 当前可验证能力

当前版本可以验证以下主链路：

- CameraX 相机预览
- 图像转 Bitmap
- 分割模型推理
- 可行驶区域掩码叠加
- 检测模型推理与框绘制
- 中文语音提醒
- 调试抓帧导出

调试抓帧按钮会导出：

- `frame.png`
- `mask.png`
- `overlay.png`
- `meta.txt`

`meta.txt` 当前会记录：

- 分割 runtime
- 分割 model name
- 检测 runtime
- 检测 model name
- 检测状态文本
- 推理耗时与路况判定字段

## 本地构建与检查

建议优先执行：

```powershell
./gradlew.bat app:assembleDebug
./gradlew.bat app:lintDebug
./gradlew.bat app:testDebugUnitTest
```

当前要求是：

- `assembleDebug` 必须通过
- `lintDebug` 必须没有 error
- `testDebugUnitTest` 至少覆盖严格 TFLite 后端策略的基础逻辑

## 真机验收建议

推荐以当前已连接真机为主做验收，顺序如下：

1. 覆盖安装最新 `app-debug.apk`
2. 清空旧 logcat
3. 启动 `com.qianmo.ruralvision/.MainActivity`
4. 验证相机权限、实时预览、分割掩码、检测框、语音提醒
5. 连续运行 3 到 5 分钟观察稳定性
6. 至少保存 2 到 3 组调试抓帧作为留档

验收关注点：

- 分割 runtime 应显示为 `GPU`
- 检测 runtime 应显示为 `TFLite-GPU`
- 若出现 `ONNX`、`TFLite-CPU`、`TFLite-NNAPI`、`检测未就绪` 或 `检测运行失败`，都不能作为软著前通过结果

## 目录说明

主工程路径：

- `app/src/main/java/com/qianmo/ruralvision/MainActivity.kt`
- `app/src/main/java/com/qianmo/ruralvision/pipeline/LatestFramePerceptionCoordinator.kt`
- `app/src/main/java/com/qianmo/ruralvision/inference/SegmentationEngine.kt`
- `app/src/main/java/com/qianmo/ruralvision/inference/DetectionModuleFactory.kt`
- `app/src/main/java/com/qianmo/ruralvision/inference/DetectionEngine.kt`
- `app/src/main/java/com/qianmo/ruralvision/inference/OnnxDetectionModule.kt`
- `app/src/main/java/com/qianmo/ruralvision/render/OverlayView.kt`
- `app/src/main/java/com/qianmo/ruralvision/debug/DebugCaptureWriter.kt`

早期骨架（已从仓库剔除，仅本地留档）：

- `template/` —— 旧版本代码快照，不是当前实际运行入口，已加入 `.gitignore`。
