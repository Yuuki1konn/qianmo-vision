$ErrorActionPreference = "Stop"

$dirs = @(
  "data/raw",
  "data/raw/bdd100k",
  "data/raw/cityscapes",
  "data/raw/kitti",
  "data/raw/idd",
  "data/raw/rugd",
  "data/raw/twhd",
  "data/raw/local_rural/images",
  "data/raw/local_rural/videos",
  "data/raw/labelimg_xml",
  "data/raw/labelme_json",
  "data/processed/detection/images_all",
  "data/processed/detection/labels_all",
  "data/processed/detection/images_aug",
  "data/processed/detection/labels_aug",
  "data/processed/detection/images/train",
  "data/processed/detection/images/val",
  "data/processed/detection/images/test",
  "data/processed/detection/labels/train",
  "data/processed/detection/labels/val",
  "data/processed/detection/labels/test",
  "data/processed/segmentation/images_all",
  "data/processed/segmentation/masks_all",
  "data/processed/segmentation/images_aug",
  "data/processed/segmentation/masks_aug",
  "data/processed/segmentation/images/train",
  "data/processed/segmentation/images/val",
  "data/processed/segmentation/images/test",
  "data/processed/segmentation/masks/train",
  "data/processed/segmentation/masks/val",
  "data/processed/segmentation/masks/test",
  "data/bad_samples",
  "runs",
  "models"
)

foreach ($d in $dirs) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}

Write-Host "数据目录初始化完成。"