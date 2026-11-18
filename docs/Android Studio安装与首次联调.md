# Android Studio 安装与首次联调

这份文档只解决一件事：

- 让你把当前项目的 Android 端尽快在本机打开、同步、运行起来

当前项目目录：

- [android](../android)

## 1. Android Studio 要不要自己下载

要。

通常需要你自己从官方页面下载安装 Android Studio。

推荐只走官方渠道：

- Android Studio 下载页：
  - https://developer.android.com/studio/
- Android Studio 安装说明：
  - https://developer.android.com/studio/install
- 中文站：
  - https://developer.android.google.cn/studio

说明：

- Android Studio 安装时通常会一起处理 Android SDK
- 一般不需要你另外单独找 JDK 再折腾一遍

## 2. Windows 上最短安装步骤

1. 打开官方下载安装包
2. 运行安装程序
3. 保持默认组件安装
4. 首次启动 Android Studio
5. 按向导安装推荐的 SDK / Build Tools

如果安装过程中网络较慢，不要着急先改项目代码，先把 IDE 和 SDK 装完整。

## 3. 装完后怎么打开这个项目

建议直接打开：

- [android](../android)

也就是：

- 不要打开整个仓库根目录
- 先只把 `android` 当成 Android Studio 工程打开

## 4. 第一次打开后你应该做什么

顺序建议如下：

1. 等 Android Studio 完成 Gradle Sync
2. 如果提示缺少 SDK，按提示安装
3. 如果提示缺少 `Gradle Wrapper`
   - 让 Android Studio 自动处理
   - 或新建一个空 Android 工程后，把当前 `app` 模块迁进去
4. 等 IDE 索引完成
5. 再连接手机或启动模拟器

## 5. 当前项目里已经准备好的内容

### 分割模型资产

- `segmentation_fp16_192.tflite`
- `segmentation_dynamic_range_192.tflite`

### 检测备用资产

- `detection_512.onnx`

### 主要入口文件

- [MainActivity.kt](../android/app/src/main/java/com/qianmo/ruralvision/MainActivity.kt)
- [LatestFramePerceptionCoordinator.kt](../android/app/src/main/java/com/qianmo/ruralvision/pipeline/LatestFramePerceptionCoordinator.kt)
- [OverlayView.kt](../android/app/src/main/java/com/qianmo/ruralvision/render/OverlayView.kt)

## 6. 第一次运行时，什么算正常

正常情况应该是：

1. App 能安装到手机或模拟器
2. 首次会请求相机权限
3. 同意后能看到相机预览
4. 能看到绿色可行驶区域叠加
5. 顶部能看到：
   - `识别中`
   - `流畅 / 一般 / 降级`
   - `仅分割` 或 `分割 + 检测`

## 7. 第一次不要急着开检测

建议第一轮只先验证分割主链：

1. 相机权限是否正常
2. 预览是否正常
3. 分割掩码是否正常
4. 底部状态是否会变化
5. 顶部性能状态是否刷新

原因很简单：

- 分割链现在最成熟
- 检测部署链还在收尾
- 先把主链跑通，后面加检测会稳很多

## 8. 如果你想尝试开检测

当前更推荐的临时路线是：

- 分割：`TFLite`
- 检测：`ONNX Runtime Android`

对应配置在：

- [AppConfig.kt](../android/app/src/main/java/com/qianmo/ruralvision/config/AppConfig.kt)

你后面需要看的主要开关：

- `Detection.ENABLED`
- `Detection.BACKEND`

## 9. 第一次联调时建议关注的日志

当前 `MainActivity` 已经预留了检测张量检查日志：

- [DetectionTensorInspector.kt](../android/app/src/main/java/com/qianmo/ruralvision/inference/DetectionTensorInspector.kt)

如果你打开检测开关，建议在 Logcat 里搜索：

- `RuralVision`

这样你能看到：

- 检测张量报告
- 检测模型是否加载失败
- 当前运行状态

## 10. 当前最现实的联调顺序

1. 安装 Android Studio
2. 打开 [android](../android)
3. 先跑分割主链
4. 再尝试 ONNX 检测备用链
5. 最后再决定是否继续追检测 TFLite 导出

## 11. 当前你最不需要担心的事

你现在不用再怀疑两件事：

1. 分割模型有没有准备好
   - 已经准备好了
2. 检测模型有没有训练好
   - 已经训练好了，默认记这版：
   - `runs/detect/runs/detection/yolov8_rural_coarse_plus_pothole_idd_det_balanced_yolov8s_imgsz704/weights/best.pt`

当前真正的重点是：

- Android Studio 装好
- 工程同步成功
- 先把分割链跑起来
