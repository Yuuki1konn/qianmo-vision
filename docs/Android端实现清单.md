# Android 端实现清单

## 1. 当前状态

Android 端已经不是纯模板目录了，当前仓库下的 [android](../android) 已经具备：

- `app` 模块
- `build.gradle.kts / settings.gradle.kts`
- `AndroidManifest.xml`
- `res/layout/activity_main.xml`
- `assets` 中的分割模型
- `MainActivity + CameraX + 分割推理 + Overlay + TTS` 主链路代码

当前默认采用：

- 分割模型：
  - `segmentation_fp16_192.tflite`
- 备用分割模型：
  - `segmentation_dynamic_range_192.tflite`
- 检测备用模型：
  - `detection_512.onnx`

这里要特别说明：

- 当前已经是**最小 Android Studio 工程骨架**
- 但还**没有完成本地 Android 编译验证**
- 主要原因是当前环境没有 `Gradle Wrapper` 和 Android SDK

## 2. 当前目标

把现有训练与导出结果接入 Android 端，形成一个能实时显示道路区域、目标框和中文语音提醒的最小可用版本。

## 3. 最小可用版本范围

第一版优先保证这些：

- 相机预览
- 分割掩码叠加
- 底部一条状态文案
- 中文语音提醒

第二阶段再补：

- 检测框叠加
- 检测风险联动
- 更复杂的性能降级策略

暂时不要做：

- 地图导航
- 复杂设置页
- 历史记录
- 多页面切换

## 4. 当前已接入的主链路

对应文件：

- [MainActivity.kt](../android/app/src/main/java/com/qianmo/ruralvision/MainActivity.kt)
- [CameraFrameProcessor.kt](../android/app/src/main/java/com/qianmo/ruralvision/camera/CameraFrameProcessor.kt)
- [ImageProxyBitmapConverter.kt](../android/app/src/main/java/com/qianmo/ruralvision/camera/ImageProxyBitmapConverter.kt)
- [SegmentationEngine.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/SegmentationEngine.kt)
- [MaskPostProcessor.kt](../android/app/src/main/java/com/qianmo/ruralvision/postprocess/MaskPostProcessor.kt)
- [LatestFramePerceptionCoordinator.kt](../android/app/src/main/java/com/qianmo/ruralvision/pipeline/LatestFramePerceptionCoordinator.kt)
- [OverlayView.kt](../android/app/src/main/java/com/qianmo/ruralvision/render/OverlayView.kt)
- [WarningTtsManager.kt](../android/app/src/main/java/com/qianmo/ruralvision/tts/WarningTtsManager.kt)
- [DriveStateEvaluator.kt](../android/app/src/main/java/com/qianmo/ruralvision/domain/DriveStateEvaluator.kt)

当前这条链路已经覆盖：

- CameraX 预览
- 最新帧策略
- 分割推理
- 可行驶区域叠加
- 状态文案生成
- 中文语音提醒骨架

同时已经预留检测接入位：

- [DetectionModule.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionModule.kt)
- [DetectionOutputParser.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionOutputParser.kt)
- [YoloV8TfliteDetectionParser.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/YoloV8TfliteDetectionParser.kt)
- [YoloV8TensorDecoder.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/YoloV8TensorDecoder.kt)
- [DetectionModuleFactory.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionModuleFactory.kt)
- [OnnxDetectionModule.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/OnnxDetectionModule.kt)
- [DetectionTensorInspector.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionTensorInspector.kt)
- [LatestFramePerceptionCoordinator.kt](../android/app/src/main/java/com/qianmo/ruralvision/pipeline/LatestFramePerceptionCoordinator.kt)

当前默认使用 `NoOpDetectionModule`，也就是：

- 主链已经兼容“未来加入检测”
- 但现在不会真的跑检测推理

当前检测后端策略：

- 默认保留 `ONNX Runtime Android` 备用链
- `TFLite` 检测导出仍在继续排障

当前默认按训练侧类别顺序约定：

- `0 -> two_wheeler`
- `1 -> pedestrian`
- `2 -> animal`
- `3 -> barrier`
- `4 -> pothole`
- `5 -> tricycle`

## 5. 还没有完成的部分

这些是后面必须继续补的，不然不能算完整产品：

- Gradle Wrapper
- Android Studio 真机编译验证
- 检测模型资产接入
- 检测输出解析与 NMS
- 分割与检测联合状态规则

## 6. 接入顺序

### 第一步：在 Android Studio 打开工程

建议直接打开：

- [android](../android)

安装与首次打开可直接参考：

- [Android Studio安装与首次联调.md](../docs/Android Studio安装与首次联调.md)

要做的事：

- 让 Android Studio 同步 Gradle
- 安装缺失 SDK
- 让 IDE 生成或补齐 Gradle Wrapper

### 第二步：跑通当前分割主链

当前默认资产已经在：

- `segmentation_fp16_192.tflite`
- `segmentation_dynamic_range_192.tflite`

要验证：

- 相机权限
- 预览是否正常
- 掩码是否叠加
- 底部状态是否刷新
- 中文语音是否能播报

### 第三步：接入检测模型

对应文件：

- [DetectionEngine.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionEngine.kt)
- [DetectionTensorInspector.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionTensorInspector.kt)
- [BoxPostProcessor.kt](../android/app/src/main/java/com/qianmo/ruralvision/postprocess/BoxPostProcessor.kt)

要做的事：

- 加载检测模型
- 先读取输入/输出张量报告
- 完成输出解析
- NMS
- 输出关键类别与风险等级
- 把 `NoOpDetectionModule()` 替换为真实 `TfLiteDetectionModule(...)`

当前更推荐的实际接入顺序：

1. 先用 `detection.onnx + ONNX Runtime Android`
2. 跑通检测框和类别
3. 再决定是否继续死磕 `detection.tflite`

接入时建议同时参考：

- [检测模型接入检查清单.md](../docs/检测模型接入检查清单.md)

### 第四步：联动状态与语音

对应文件：

- [DriveStateEvaluator.kt](../android/app/src/main/java/com/qianmo/ruralvision/domain/DriveStateEvaluator.kt)
- [中文语音提醒规则表.md](../docs/中文语音提醒规则表.md)

要做的事：

- 对齐真实检测类别 ID
- 调整风险优先级
- 优化播报节流

## 7. 推荐线程模型

建议至少拆成三条：

- 相机采集线程
- 推理线程
- 渲染线程

规则：

- 推理线程永远只拿最新一帧
- 老帧直接丢弃
- 渲染永远显示最近一次有效结果

## 8. 默认状态栏规则

顶部：

- `识别中`
- `流畅 / 一般 / 降级`
- `语音开 / 语音关`

底部：

- 只显示一条状态

参考：

- [界面状态与降级规则.md](../docs/界面状态与降级规则.md)

## 9. 建议的第一版判定逻辑

### 分割用于：

- 计算主可行驶区域
- 判断是否偏离道路
- 判断前方是否变窄

### 检测用于：

- 行人
- 动物
- 坑洼
- 障碍物

### 最终状态生成

从高优先级开始判断：

1. 偏离道路
2. 障碍物过近
3. 动物
4. 行人
5. 坑洼
6. 道路变窄
7. 道路正常

## 10. 性能策略

### 目标

- 至少 `12 FPS`
- 理想 `15~20 FPS`

### 如果性能不够

按顺序处理：

1. 降低预览渲染分辨率
2. 分割降频
3. 切换到 `segmentation_dynamic_range.tflite`
4. 检测降频

### 不建议

- 两个分割模型同时实时跑
- 每帧都做重后处理
- 主线程做推理

## 11. 你接下来最值得先做的文件

如果按开发顺序，建议优先完成：

1. [MainActivity.kt](../android/app/src/main/java/com/qianmo/ruralvision/MainActivity.kt)
2. [SegmentationEngine.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/SegmentationEngine.kt)
3. [LatestFramePerceptionCoordinator.kt](../android/app/src/main/java/com/qianmo/ruralvision/pipeline/LatestFramePerceptionCoordinator.kt)
4. [OverlayView.kt](../android/app/src/main/java/com/qianmo/ruralvision/render/OverlayView.kt)
5. [WarningTtsManager.kt](../android/app/src/main/java/com/qianmo/ruralvision/tts/WarningTtsManager.kt)

## 12. 当前建议

如果你时间紧，第一版先只做：

- 分割显示
- 底部状态
- 语音提醒

检测框可以稍后再补，因为：

- 分割是当前项目最稳定、最成熟的主能力
- 它最能直接体现“道路识别系统”的核心价值
