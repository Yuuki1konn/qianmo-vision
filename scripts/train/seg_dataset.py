from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset


VALID_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


class SegmentationDataset(Dataset):
    def __init__(
        self,
        image_dir: str,
        mask_dir: str,
        image_size: tuple[int, int] = (640, 640),
        mask_suffix: str = ".png",
        use_mask_list: bool = False,
        mask_threshold: int = 0,
        positive_values: list[int] | None = None,
        image_stem_strip: str = "",
    ):
        self.image_dir = Path(image_dir)
        self.mask_dir = Path(mask_dir)
        self.image_size = image_size
        self.mask_suffix = mask_suffix
        self.use_mask_list = use_mask_list
        self.mask_threshold = mask_threshold
        self.positive_values = positive_values
        self.image_stem_strip = image_stem_strip

        if self.use_mask_list:
            self.samples: list[tuple[Path, Path]] = []
            masks = sorted([p for p in self.mask_dir.rglob("*") if p.suffix.lower() == ".png"])
            for mask_path in masks:
                stem = mask_path.name
                if self.mask_suffix and stem.endswith(self.mask_suffix):
                    stem = stem[: -len(self.mask_suffix)]
                else:
                    stem = mask_path.stem
                image_path = None
                for suffix in VALID_EXT:
                    candidate = self.image_dir / f"{stem}{suffix}"
                    if candidate.exists():
                        image_path = candidate
                        break
                if image_path is None:
                    continue
                self.samples.append((image_path, mask_path))
        else:
            self.images = sorted([p for p in self.image_dir.rglob("*") if p.suffix.lower() in VALID_EXT])

    def __len__(self) -> int:
        if self.use_mask_list:
            return len(self.samples)
        return len(self.images)

    def __getitem__(self, index: int):
        if self.use_mask_list:
            image_path, mask_path = self.samples[index]
        else:
            image_path = self.images[index]
            stem = image_path.stem
            if self.image_stem_strip and stem.endswith(self.image_stem_strip):
                stem = stem[: -len(self.image_stem_strip)]
            if self.mask_suffix == ".png":
                mask_path = self.mask_dir / f"{stem}.png"
            else:
                mask_path = self.mask_dir / f"{stem}{self.mask_suffix}"

        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

        if image is None:
            raise FileNotFoundError(f'读取图像失败: {image_path}')
        if mask is None:
            raise FileNotFoundError(f'读取掩码失败: {mask_path}')

        image = cv2.resize(image, self.image_size, interpolation=cv2.INTER_LINEAR)
        mask = cv2.resize(mask, self.image_size, interpolation=cv2.INTER_NEAREST)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        if self.positive_values:
            mask = np.isin(mask, self.positive_values).astype(np.float32)
        else:
            mask = (mask > self.mask_threshold).astype(np.float32)

        image = np.transpose(image, (2, 0, 1))
        mask = np.expand_dims(mask, axis=0)

        return torch.tensor(image, dtype=torch.float32), torch.tensor(mask, dtype=torch.float32)
