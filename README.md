<div align="center">

# QianMo Vision · 阡陌智行

**端侧实时感知基线：可行驶区域分割 + 二轮车/障碍物检测 + 中文语音告警**

<sub>*qiānmò* (阡陌) — the footpaths that crisscross farm fields.</sub>

![Kotlin](https://img.shields.io/badge/Kotlin-1.9.24-7F52FF?logo=kotlin&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%E2%89%A52.4-EE4C2C?logo=pytorch&logoColor=white)
![TFLite](https://img.shields.io/badge/TensorFlow%20Lite-2.17-FF6F00?logo=tensorflow&logoColor=white)
![Android](https://img.shields.io/badge/Android-8.0%2B-3DDC84?logo=android&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue.svg)
![GitHub release](https://img.shields.io/github/v/release/Yuuki1konn/qianmo-vision?label=models)

</div>

---

## 这是什么

骑电动车走农村土路、田间路、村道时，最怕的是「路到底在哪」和「前面那个东西是啥」。

这个项目把这两件事拆成两个模型跑在手机上：

- **分割**：U-Net 输出可行驶区域掩码，回答「路在哪」
- **检测**：YOLOv8s 输出二轮车 / 行人 / 动物 / 路障 / 坑洼 / 三轮车，回答「危险是什么」

两个结果在端侧合成一条路况状态，再交给中文 TTS 念出来。全程离线，不联网、不上传画面。

## 架构

```text
┌──────────────┐  RGBA Bitmap   ┌──────────────────────────────────┐
│  CameraX     │ ─────────────▶ │ 最新帧调度器（单线程 / 丢积压帧）  │
│  480×360     │                └───────────────┬──────────────────┘
└──────────────┘                                │
        ┌───────────────────────────────────────┼──────────────────────┐
        ▼                                       ▼                      │
 预处理 192×192                           预处理 512×512                │
        │                                       │                      │
        ▼                                       ▼                      │
 U-Net（TFLite GPU/CPU 自动回退）        YOLOv8s（TFLite GPU）           │
        │ 可行驶掩码                            │ 6 类检测框              │
        └──────────────▶ DriveStateEvaluator ◀──┘                      │
                              │ 路况判定 + 预警优先级                      │
                 ┌────────────┴────────────┐                           │
                 ▼                         ▼                           │
        OverlayView 实时叠加        WarningTtsManager ───────────────────┘
```

## 工程亮点

- **只处理最新帧**：CameraX `STRATEGY_KEEP_ONLY_LATEST` + 单线程 `AtomicReference` 交接，推理慢时直接丢帧，不做队列堆积
- **热感知降级**：监听 `PowerManager` 热状态，联动处理 FPS 上限与检测退避帧数，越热越省
- **检测后处理搬到 Kotlin**：导出时把 YOLOv8 的 DFL / Sigmoid 张量提成模型输出 `dfl_out[1,4,N]` / `cls_out[1,6,N]`，TFLite 图里不含 NMS，不依赖 `SELECT_TF_OPS`
- **严格后端策略**：检测要求 TFLite-GPU 且不回退 ONNX，起不来就明确显示「检测未就绪」，不假装能跑

## 目录结构

```text
configs/          训练与数据处理配置（分割内嵌数据源，检测指向 yolo 数据集 yaml）
scripts/
  data/           多源公开数据 → YOLO txt / 二值掩码，含清洗、去重、平衡、划分
  train/          train_segmentation.py / train_detection.py（ultralytics 薄封装）
  eval/           指标评估、按类指标、难例挖掘、可视化
  export/         PyTorch → ONNX → TFLite，含一致性验证
android/          Kotlin 端侧工程（包名 com.qianmo.ruralvision）
docs/             架构、数据、模型对比、语音规则、答辩材料等过程文档
```

Android 端模块划分：

| 目录 | 职责 |
| --- | --- |
| `camera/` | CameraX 取流、Bitmap 转换、旋转/缩放/归一化预处理 |
| `inference/` | 分割 / 检测引擎、TFLite 与 ONNX 后端、YOLO 张量解码 |
| `pipeline/` | 最新帧调度、帧率节流、检测退避、调试抓帧 |
| `postprocess/` | 掩码阈值与形态学、检测框 NMS |
| `domain/` | 路况判定（偏离道路 / 障碍物 / 路面变窄） |
| `render/` | Canvas 叠加掩码、检测框、状态文案 |
| `tts/` | 中文语音告警（带最小间隔与优先级） |
| `config/` | 模型路径、阈值、FPS 上限、热降级参数 |

## 快速开始

### 1. 训练环境

```bash
conda env create -f environment.conda.yml
conda activate rural_vision
# 或：python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

### 2. 数据准备

公开数据集按 [`docs/数据集推荐与下载优先级.md`](docs/数据集推荐与下载优先级.md) 下载，再用 `scripts/data/` 下的脚本转成统一格式：

- 分割：BDD100K drivable / Cityscapes road / IDD road → 二值 PNG 掩码
- 检测：TWHD / RDD2020 / N-RDD2024 / IDD 等 → YOLO txt，再粗分成 6 类

数据量较大，`data/`、`runs/` 都不入库，需本地重新生成。

### 3. 训练

```bash
python scripts/train/train_segmentation.py --config configs/segmentation_bdd_city_idd_relaxed.yaml
python scripts/train/train_detection.py --config configs/detection_coarse_plus_pothole_idd_det_balanced_yolov8s_imgsz704.yaml
```

### 4. 评估

```bash
python scripts/eval/eval_segmentation.py --checkpoint runs/segmentation_bdd_city_idd_relaxed/best.pt --config configs/segmentation_bdd_city_idd_relaxed.yaml
python scripts/eval/eval_detection.py --weights runs/detection/.../weights/best.pt --data configs/yolo_dataset_coarse_plus_pothole_idd_det_balanced.yaml
```

### 5. 导出 TFLite

```bash
# 分割
python scripts/export/export_segmentation_tflite.py --checkpoint runs/segmentation_bdd_city_idd_relaxed/best.pt --model-name unet --input-size 192

# 检测（输出带 dfl_out / cls_out 的中间张量版，并复制到 assets）
python scripts/export/export_detection_tflite.py --weights runs/detection/.../weights/best.pt --imgsz 512 --copy-to-assets
```

> 导出依赖离线版 onnx2tf。仓库不包含 `.tools/`（本地 vendored 目录），离线环境请先 `pip install onnx2tf`，或按 `scripts/export/export_detection_tflite.py` 里的 `ensure_local_onnx2tf()` 放置同名目录。

### 6. Android 构建

```bash
cd android
./gradlew.bat app:assembleDebug     # 出包
./gradlew.bat app:lintDebug         # 静态检查
./gradlew.bat app:testDebugUnitTest # 单测
```

真机需要 Android 8.0+ 且支持 GPU delegate；检测模型跑不起来时会显示「检测未就绪」并只保留分割。

## 模型资产（必读）

**模型文件不入库**（体积大且是二进制），请到 [Releases → models-v1](https://github.com/Yuuki1konn/qianmo-vision/releases/tag/models-v1) 下载后放进 `android/app/src/main/assets/`：

| 文件 | 大小 | 用途 |
| --- | --- | --- |
| `segmentation_fp16_192.tflite` | 59.2 MB | 分割主模型，GPU 路径（FP16） |
| `segmentation_dynamic_range_192.tflite` | 29.7 MB | 分割 CPU / NNAPI 回退（动态量化） |
| `detection.tflite` | 21.3 MB | 检测模型，TFLite-GPU，输出 `dfl_out` / `cls_out` |
| `detection_512.onnx` | 42.6 MB | 检测 ONNX 备用后端（当前默认路线不启用） |

校验值（SHA-256）：

```text
9539c69283085be8e1ed3cc6c779e176c55f4f84ac95a7e77db0dcce07ad9bec  detection_512.onnx
fd37898e066ba558fc3d3396f30c74ec4364dac79b1f30121b4ed41408e70256  detection.tflite
5eecbfc9e09c4c311fe2a989972965232b7ea6ad15641696d3c1c5ba7aea1c00  segmentation_dynamic_range_192.tflite
e0020089c03d71d1c746feb4e33f6af31c5bdccb485b2e5cbe8a728c6ac9f7a3  segmentation_fp16_192.tflite
```

> 仓库里 `detection_512.onnx` 与 `detection.tflite` 是同一份 YOLOv8s 权重的两种产物，选一种即可跑通。

## 指标

**分割**（U-Net + ResNet34 风格编码器，relaxed 版，BDD100K + Cityscapes + IDD）：

| 指标 | 数值 |
| --- | --- |
| mIoU | 0.8411 |
| Dice | 0.9128 |
| Pixel Accuracy | 0.9715 |

**检测**（YOLOv8s，imgsz 704，6 类，含坑洼补样本版）：

| 指标 | 数值 |
| --- | --- |
| Precision | 0.4978 |
| Recall | 0.3021 |
| mAP@0.5 | 0.3029 |
| mAP@0.5:0.95 | 0.1702 |

分类别 AP@0.5：two_wheeler 0.363 / pedestrian 0.291 / tricycle 0.451 / pothole 0.548 / barrier 0.093 / animal 0.071。

**端侧**：相机 480×360；分割输入 192×192；检测输入 512×512、每 6 帧一次；处理帧率上限 GPU 12 FPS、CPU 4 FPS；TTS 最小间隔 4 s。

## 已知限制

- 检测精度偏低，主要卡在 `barrier` 与 `animal` 的召回（农村长尾场景样本太少），不是调参能补的缺口，需要补数据
- 分割训练用 512×512，部署只喂 192×192，边界细节有损失
- 暂无自动化单元测试，验证依赖真机与调试抓帧（`debug/`）
- 检测强制 GPU，低端机或模拟器上只能看分割

## 技术栈

| 层 | 栈 |
| --- | --- |
| 训练 | PyTorch ≥2.4、torchvision、torchmetrics、Albumentations、Ultralytics ≥8.3 |
| 数据/评估 | OpenCV、NumPy、scikit-image、scikit-learn、pandas、Matplotlib、TensorBoard |
| 导出 | ONNX ≥1.16、onnxruntime ≥1.19、onnx2tf 1.29.24、TensorFlow ≥2.17 |
| 端侧 | Kotlin 1.9.24、AGP 8.7.3、JDK 17、CameraX 1.4.2、TFLite 2.17 + GPU delegate、ONNX Runtime Android 1.24.3 |
| 平台 | compileSdk 35 / minSdk 26 / targetSdk 35 |

更多细节见 [`docs/系统架构说明.md`](docs/系统架构说明.md)、[`docs/技术文档.md`](docs/技术文档.md)、[`docs/分割模型最终结论.md`](docs/分割模型最终结论.md)。

## 许可证

MIT，见 [`LICENSE`](LICENSE)。
