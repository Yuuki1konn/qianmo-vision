import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import yaml
from torch.utils.data import ConcatDataset, DataLoader

from scripts.train.seg_dataset import SegmentationDataset
from scripts.train.seg_models import create_model


def calc_metrics(logits, targets, threshold=0.5):
    probs = torch.sigmoid(logits)
    preds = (probs > threshold).float()

    tp = (preds * targets).sum().item()
    fp = (preds * (1 - targets)).sum().item()
    fn = ((1 - preds) * targets).sum().item()
    tn = ((1 - preds) * (1 - targets)).sum().item()

    iou = tp / (tp + fp + fn + 1e-7)
    dice = (2 * tp) / (2 * tp + fp + fn + 1e-7)
    pixel_acc = (tp + tn) / (tp + tn + fp + fn + 1e-7)
    return iou, dice, pixel_acc


def build_dataset(cfg: dict, split: str):
    image_size = tuple(cfg.get('image_size', [640, 640]))
    mask_threshold = int(cfg.get('mask_threshold', 0))
    sources_key = f'{split}_sources'
    if sources_key in cfg:
        datasets = []
        for src in cfg[sources_key]:
            datasets.append(
                SegmentationDataset(
                    image_dir=src['image_dir'],
                    mask_dir=src['mask_dir'],
                    image_size=image_size,
                    mask_suffix=str(src.get('mask_suffix', '.png')),
                    use_mask_list=bool(src.get('use_mask_list', False)),
                    mask_threshold=int(src.get('mask_threshold', mask_threshold)),
                    positive_values=src.get('positive_values'),
                    image_stem_strip=str(src.get('image_stem_strip', cfg.get('image_stem_strip', ''))),
                )
            )
        return ConcatDataset(datasets)

    return SegmentationDataset(
        image_dir=cfg[f'{split}_images'],
        mask_dir=cfg[f'{split}_masks'],
        image_size=image_size,
        mask_suffix=str(cfg.get('mask_suffix', '.png')),
        use_mask_list=bool(cfg.get('use_mask_list', False)),
        mask_threshold=mask_threshold,
        positive_values=cfg.get('positive_values'),
        image_stem_strip=str(cfg.get('image_stem_strip', '')),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='评估分割模型指标（mIoU / Dice / Pixel Accuracy）')
    parser.add_argument('--config', type=Path, default=Path('configs/segmentation.yaml'))
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--split', choices=['val', 'test'], default='val')
    parser.add_argument('--num-workers', type=int, default=None)
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    dataset = build_dataset(cfg, args.split)
    loader = DataLoader(
        dataset,
        batch_size=int(cfg.get('batch_size', 8)),
        shuffle=False,
        num_workers=int(args.num_workers if args.num_workers is not None else cfg.get('num_workers', 4)),
    )

    model = create_model(cfg.get('model_name', 'unet')).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()

    iou_sum = 0.0
    dice_sum = 0.0
    pa_sum = 0.0

    with torch.no_grad():
        for images, masks in loader:
            images = images.to(device)
            masks = masks.to(device)
            logits = model(images)
            iou, dice, pa = calc_metrics(logits, masks)
            iou_sum += iou
            dice_sum += dice
            pa_sum += pa

    n = max(1, len(loader))
    print(f'mIoU: {iou_sum / n:.4f}')
    print(f'Dice: {dice_sum / n:.4f}')
    print(f'Pixel Accuracy: {pa_sum / n:.4f}')


if __name__ == '__main__':
    main()
