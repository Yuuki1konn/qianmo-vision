# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

农村二轮车道路识别系统（阡陌智行）。端到端基线：道路可行驶区域分割 + 二轮车/障碍物检测 → TFLite 导出 → Android 端实时推理 + TTS 语音告警。

## 常用命令

### 环境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 训练

```powershell
python scripts/train/train_segmentation.py --config configs/segmentation_bdd_city_idd_relaxed.yaml
python scripts/train/train_detection.py --config configs/detection_coarse_balanced.yaml
```

### 评估

```powershell
python scripts/eval/eval_segmentation.py --checkpoint runs/segmentation/best.pt --config configs/segmentation.yaml
python scripts/eval/eval_detection.py --weights runs/detection/.../weights/best.pt --data configs/yolo_dataset.yaml
```

### 导出

```powershell
python scripts/export/export_segmentation_tflite.py --checkpoint runs/segmentation/.../best.pt --model-name unet --input-size 192
python scripts/export/export_detection_tflite.py --weights runs/detection/.../weights/best.pt --imgsz 512 --copy-to-assets
python scripts/export/validate_tflite.py --onnx <onnx> --tflite <tflite> --image-dir <dir> --max-samples 5
```

### Android

```powershell
cd android
./gradlew.bat app:assembleDebug
./gradlew.bat app:lintDebug
./gradlew.bat app:testDebugUnitTest
```

## 架构

### 数据层（`scripts/data/`）

多源公开数据集（BDD100K、Cityscapes、IDD、RUGD、TWHD、RDD2020、N-RDD2024）通过专用脚本转换为统一的 YOLO 格式（检测）或 PNG 掩码（分割），经清洗、增强、类别平衡、去重后按 8:1:1 划分。

关键类别映射：
- 检测粗分类 6 类：二轮车(0)、行人(1)、动物(2)、路障(3)、坑洼(4)、三轮车(5) — 见 `configs/coarse_detection_class_map.json`
- 分割正类：可行驶区域（road / drivable area），具体语义由各数据集的准备脚本控制

### 训练层（`scripts/train/`）

- **分割**：`train_segmentation.py` 驱动，模型见 `seg_models.py`（自定义 U-Net、DeepLabV3+ with ResNet50 backbone）。损失 = BCE + Dice。支持混合精度、channels_last、断点恢复。多数据源通过配置的 `train_sources`/`val_sources` 列表组合为 ConcatDataset。
- **检测**：`train_detection.py` 是 ultralytics YOLO 的薄封装。由于 ultralytics 线程池在 Windows 下可能卡死，训练脚本会 monkey-patch ThreadPool → SerialPool。

### 导出层（`scripts/export/`）

PyTorch → ONNX → TFLite 两阶段导出：
- **分割**：直接 ONNX export → onnx2tf 转换。会自动修补 ConvTranspose 节点缺失的 kernel_shape，并替换 onnx2tf 的下载测试图调用（避免离线环境卡死）。
- **检测**：YOLOv8 ONNX export → Split 节点重写（移除 split 输入使 TFLite 兼容）→ 暴露中间输出 `dfl_out` / `cls_out`（供 Android 端 Kotlin 解码，无需 TFLite 内建 NMS）。使用本地 vendored onnx2tf（`.tools/onnx2tf_py310/`）。

### Android 端（`android/`）

Kotlin 工程，包名 `com.qianmo.ruralvision`，关键模块：

| 目录 | 职责 |
|---|---|
| `camera/` | CameraX 帧采集，Bitmap 转换，预处理（缩放/旋转/归一化）到 ByteBuffer |
| `inference/` | `SegmentationEngine`（TFLite GPU/CPU/NNAPI 自动选择），`DetectionModule` 接口 + `OnnxDetectionModule` / TFLite 检测实现，`YoloV8TfliteIntermediateDetectionParser` 解码中间输出 |
| `pipeline/` | `LatestFramePerceptionCoordinator` — 核心调度：只处理最新帧，跳过积压帧。热感知 FPS 上限，检测慢推理自动 backoff |
| `postprocess/` | 分割掩码阈值化/形态学操作，检测框 NMS |
| `render/` | `OverlayView` — Canvas 叠加绘制掩码、检测框、状态文字 |
| `domain/` | `DriveStateEvaluator` — 根据掩码和检测框判定路况（偏离道路、障碍物距离、路面变窄） |
| `tts/` | `WarningTtsManager` — 中文 TTS 语音告警，带最小间隔 |
| `config/` | `AppConfig` — 模型路径、阈值、FPS 上限、热降级参数、告警优先级 |
| `debug/` | 调试抓帧（frame/mask/overlay/meta.txt） |

**推理后端策略**：验收要求检测走 TFLite-GPU（`REQUIRE_GPU_RUNTIME = true`），失败则进入"检测未就绪"状态，不会回退到 ONNX。分割允许回退 CPU/NNAPI。

### 配置（`configs/`）

YAML 驱动训练和数据处理。检测配置指定 `data_yaml`（指向 `yolo_dataset*.yaml` 描述数据集路径和类别），分割配置直接内嵌数据集路径、数据源列表和训练超参。多阶段实验产生 _balanced、_dedup、_imgsz704 等变体配置。

## 重要路径

- 模型资产：`android/app/src/main/assets/`（segmentation_fp16_192.tflite、detection.tflite 等）
- 训练产物：`runs/`（gitignored，需从训练备份恢复）
- 原始/处理后数据：`data/`（gitignored）
- 离线 onnx2tf：`.tools/onnx2tf_py310/`
- 本地 ultralytics 配置：`.yolo_config/`
