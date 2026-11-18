from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset


VALID_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


class YoloDetectionDataset(Dataset):
    """YOLO 格式检测数据加载器（用于调试与自定义训练场景）。"""

    def __init__(self, image_dir: str, label_dir: str, image_size: tuple[int, int] = (640, 640)):
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.image_size = image_size
        self.images = sorted([p for p in self.image_dir.rglob('*') if p.suffix.lower() in VALID_EXT])

    def __len__(self):
        return len(self.images)

    def _load_labels(self, txt_path: Path):
        boxes = []
        labels = []
        if not txt_path.exists():
            return np.zeros((0, 4), dtype=np.float32), np.zeros((0,), dtype=np.int64)

        for line in txt_path.read_text(encoding='utf-8').splitlines():
            parts = line.split()
            if len(parts) != 5:
                continue
            cls_id = int(parts[0])
            x, y, w, h = map(float, parts[1:5])
            boxes.append([x, y, w, h])
            labels.append(cls_id)

        if not boxes:
            return np.zeros((0, 4), dtype=np.float32), np.zeros((0,), dtype=np.int64)

        return np.array(boxes, dtype=np.float32), np.array(labels, dtype=np.int64)

    def __getitem__(self, idx: int):
        img_path = self.images[idx]
        img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f'读取图像失败: {img_path}')

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, self.image_size, interpolation=cv2.INTER_LINEAR)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))

        txt = self.label_dir / f'{img_path.stem}.txt'
        boxes, labels = self._load_labels(txt)

        target = {
            'boxes_yolo': torch.tensor(boxes, dtype=torch.float32),
            'labels': torch.tensor(labels, dtype=torch.int64),
            'image_id': torch.tensor([idx], dtype=torch.int64),
        }

        return torch.tensor(img, dtype=torch.float32), target
