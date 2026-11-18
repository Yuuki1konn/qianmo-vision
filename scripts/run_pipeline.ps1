param(
  [string]$DataRoot = 'data',
  [string]$SegConfig = 'configs/segmentation.yaml',
  [string]$DetConfig = 'configs/detection.yaml'
)

Write-Host '=== 数据准备阶段 ==='
Write-Host '1) XML -> YOLO（按需）'
Write-Host '2) LabelMe JSON -> PNG 掩码（按需）'
Write-Host '3) resize + normalize'
Write-Host '4) 清洗 + 增强 + 划分 + 可视化质检 + 生成说明文档'

Write-Host '=== 模型训练阶段 ==='
python scripts/train/train_segmentation.py --config $SegConfig
python scripts/train/train_detection.py --config $DetConfig

Write-Host '=== 模型评估阶段 ==='
python scripts/eval/eval_segmentation.py --config $SegConfig --checkpoint runs/segmentation/best.pt
python scripts/eval/eval_detection.py --weights runs/detection/yolov8_rural/weights/best.pt --data configs/yolo_dataset.yaml

Write-Host '=== 模型导出阶段 ==='
python scripts/export/export_segmentation_tflite.py --checkpoint runs/segmentation/best.pt --model-name unet --int8
python scripts/export/export_detection_tflite.py --weights runs/detection/yolov8_rural/weights/best.pt --int8 --data configs/yolo_dataset.yaml

Write-Host '=== 一致性验证阶段 ==='
python scripts/export/validate_tflite.py --onnx runs/export/segmentation/segmentation.onnx --tflite runs/export/segmentation/segmentation_int8.tflite --image-dir data/processed/segmentation/images/val
