import argparse
import random
import sys
import time
from pathlib import Path
from contextlib import nullcontext

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import torch.nn as nn
import torch.optim as optim
import yaml
from torch.utils.data import ConcatDataset, DataLoader, Subset
from tqdm import tqdm

from scripts.train.seg_dataset import SegmentationDataset
from scripts.train.seg_models import create_model


class DiceLoss(nn.Module):
    def __init__(self, smooth: float = 1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, logits, targets):
        probs = torch.sigmoid(logits)
        intersection = (probs * targets).sum(dim=(1, 2, 3))
        union = probs.sum(dim=(1, 2, 3)) + targets.sum(dim=(1, 2, 3))
        dice = (2 * intersection + self.smooth) / (union + self.smooth)
        return 1 - dice.mean()


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


def train_one_epoch(model, loader, optimizer, bce_loss, dice_loss, device, scaler, autocast_ctx, channels_last, max_steps):
    model.train()
    total_loss = 0.0

    steps = 0
    total = max_steps if max_steps else None
    for images, masks in tqdm(loader, desc='训练', leave=False, total=total):
        if channels_last:
            images = images.to(device, non_blocking=True).contiguous(memory_format=torch.channels_last)
        else:
            images = images.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)

        optimizer.zero_grad()
        with autocast_ctx():
            logits = model(images)
            loss = bce_loss(logits, masks) + dice_loss(logits, masks)
        if scaler is None:
            loss.backward()
            optimizer.step()
        else:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

        total_loss += loss.item()
        steps += 1
        if max_steps and steps >= max_steps:
            break

    return total_loss / max(1, steps)


def evaluate(model, loader, bce_loss, dice_loss, device, autocast_ctx, channels_last, max_steps):
    model.eval()
    total_loss = 0.0
    total_iou = 0.0
    total_dice = 0.0
    total_pa = 0.0

    steps = 0
    total = max_steps if max_steps else None
    with torch.no_grad():
        for images, masks in tqdm(loader, desc='验证', leave=False, total=total):
            if channels_last:
                images = images.to(device, non_blocking=True).contiguous(memory_format=torch.channels_last)
            else:
                images = images.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            with autocast_ctx():
                logits = model(images)
                loss = bce_loss(logits, masks) + dice_loss(logits, masks)
            iou, dice, pa = calc_metrics(logits, masks)

            total_loss += loss.item()
            total_iou += iou
            total_dice += dice
            total_pa += pa
            steps += 1
            if max_steps and steps >= max_steps:
                break

    n = max(1, steps)
    return total_loss / n, total_iou / n, total_dice / n, total_pa / n


def main() -> None:
    parser = argparse.ArgumentParser(description='训练道路分割模型（U-Net / DeepLab）')
    parser.add_argument('--config', type=Path, default=Path('configs/segmentation.yaml'))
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
    seed = int(cfg.get('seed', 42))

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'使用设备: {device}')

    if device == 'cuda' and bool(cfg.get('cudnn_benchmark', True)):
        torch.backends.cudnn.benchmark = True

    matmul_precision = cfg.get('matmul_precision')
    if matmul_precision:
        torch.set_float32_matmul_precision(str(matmul_precision))

    model = create_model(cfg.get('model_name', 'unet')).to(device)

    def maybe_subset(dataset, max_samples, rng):
        if max_samples is None:
            return dataset
        try:
            max_samples = int(max_samples)
        except (TypeError, ValueError):
            return dataset
        if max_samples <= 0 or len(dataset) <= max_samples:
            return dataset
        indices = list(range(len(dataset)))
        rng.shuffle(indices)
        return Subset(dataset, indices[:max_samples])

    def build_dataset(split: str):
        sources_key = f'{split}_sources'
        if sources_key in cfg:
            datasets = []
            for idx, src in enumerate(cfg[sources_key]):
                ds = SegmentationDataset(
                    image_dir=src['image_dir'],
                    mask_dir=src['mask_dir'],
                    image_size=image_size,
                    mask_suffix=str(src.get('mask_suffix', '.png')),
                    use_mask_list=bool(src.get('use_mask_list', False)),
                    mask_threshold=int(src.get('mask_threshold', cfg.get('mask_threshold', 0))),
                    positive_values=src.get('positive_values'),
                    image_stem_strip=str(src.get('image_stem_strip', cfg.get('image_stem_strip', ''))),
                )
                max_samples = src.get('max_samples')
                rng = random.Random(seed + idx + (0 if split == 'train' else 1000))
                ds = maybe_subset(ds, max_samples, rng)
                datasets.append(ds)
            return ConcatDataset(datasets)
        ds = SegmentationDataset(
            image_dir=cfg[f'{split}_images'],
            mask_dir=cfg[f'{split}_masks'],
            image_size=image_size,
            mask_suffix=str(cfg.get('mask_suffix', '.png')),
            use_mask_list=bool(cfg.get('use_mask_list', False)),
            mask_threshold=int(cfg.get('mask_threshold', 0)),
            positive_values=cfg.get('positive_values'),
            image_stem_strip=str(cfg.get('image_stem_strip', '')),
        )
        max_samples = cfg.get(f'max_{split}_samples')
        rng = random.Random(seed + (0 if split == 'train' else 1000))
        return maybe_subset(ds, max_samples, rng)

    image_size = tuple(cfg.get('image_size', [640, 640]))
    train_set = build_dataset('train')
    val_set = build_dataset('val')

    if len(train_set) == 0:
        raise ValueError('训练集为空，请检查配置与数据路径。')
    if len(val_set) == 0:
        raise ValueError('验证集为空，请检查配置与数据路径。')

    print(f'训练集样本: {len(train_set)}')
    print(f'验证集样本: {len(val_set)}')

    num_workers = int(cfg.get('num_workers', 4))
    pin_memory = bool(cfg.get('pin_memory', device == 'cuda'))
    persistent_workers = bool(cfg.get('persistent_workers', num_workers > 0))
    prefetch_factor = int(cfg.get('prefetch_factor', 2))
    loader_kwargs = {
        'batch_size': int(cfg.get('batch_size', 8)),
        'num_workers': num_workers,
        'pin_memory': pin_memory,
    }
    if num_workers > 0:
        loader_kwargs['persistent_workers'] = persistent_workers
        loader_kwargs['prefetch_factor'] = prefetch_factor

    train_loader = DataLoader(train_set, shuffle=True, **loader_kwargs)
    val_loader = DataLoader(val_set, shuffle=False, **loader_kwargs)

    optimizer = optim.AdamW(model.parameters(), lr=float(cfg.get('learning_rate', 3e-4)))
    bce_loss = nn.BCEWithLogitsLoss()
    dice_loss = DiceLoss()

    use_amp = bool(cfg.get('amp', True)) and device == 'cuda'
    if use_amp:
        scaler = torch.amp.GradScaler('cuda')
        def autocast_ctx():
            return torch.amp.autocast(device_type='cuda')
    else:
        scaler = None
        autocast_ctx = nullcontext
    channels_last = bool(cfg.get('channels_last', False)) and device == 'cuda'
    if channels_last:
        model = model.to(memory_format=torch.channels_last)

    save_dir = Path(cfg.get('save_dir', 'runs/segmentation'))
    save_dir.mkdir(parents=True, exist_ok=True)

    resume_from = cfg.get('resume_from')
    resume_optimizer = bool(cfg.get('resume_optimizer', True))
    start_epoch = 1
    best_iou = -1.0
    best_iou_mode = str(cfg.get('best_iou_mode', 'auto')).lower()

    if resume_from:
        ckpt_path = Path(resume_from)
        if ckpt_path.exists():
            ckpt = torch.load(ckpt_path, map_location=device)
            model.load_state_dict(ckpt.get('model_state_dict', ckpt))
            if resume_optimizer and 'optimizer_state_dict' in ckpt:
                try:
                    optimizer.load_state_dict(ckpt['optimizer_state_dict'])
                except Exception:
                    print('警告: 优化器状态加载失败，已忽略。')
            if scaler is not None and resume_optimizer and 'scaler_state_dict' in ckpt:
                try:
                    scaler.load_state_dict(ckpt['scaler_state_dict'])
                except Exception:
                    print('警告: AMP 状态加载失败，已忽略。')
            if 'epoch' in ckpt:
                start_epoch = int(ckpt['epoch']) + 1
            should_resume_best = best_iou_mode == 'resume'
            if best_iou_mode == 'auto':
                existing_best = save_dir / 'best.pt'
                should_resume_best = existing_best.exists() and existing_best.resolve() == ckpt_path.resolve()
            if should_resume_best and 'val_iou' in ckpt:
                try:
                    best_iou = float(ckpt['val_iou'])
                except (TypeError, ValueError):
                    best_iou = -1.0
            print(f'已从断点恢复: {ckpt_path} (start_epoch={start_epoch})')
        else:
            print(f'警告: resume_from 不存在: {ckpt_path}')

    epochs = int(cfg.get('epochs', 80))

    val_interval = int(cfg.get('val_interval', 1))
    max_train_steps = cfg.get('max_train_steps')
    max_val_steps = cfg.get('max_val_steps')

    for epoch in range(start_epoch, epochs + 1):
        t0 = time.time()
        train_loss = train_one_epoch(
            model,
            train_loader,
            optimizer,
            bce_loss,
            dice_loss,
            device,
            scaler,
            autocast_ctx,
            channels_last,
            max_train_steps,
        )

        do_val = (epoch % val_interval == 0)
        if do_val:
            val_loss, val_iou, val_dice, val_pa = evaluate(
                model,
                val_loader,
                bce_loss,
                dice_loss,
                device,
                autocast_ctx,
                channels_last,
                max_val_steps,
            )
        else:
            val_loss = val_iou = val_dice = val_pa = float('nan')

        dt = time.time() - t0

        if do_val:
            print(
                f'[Epoch {epoch}/{epochs}] '
                f'train_loss={train_loss:.4f} '
                f'val_loss={val_loss:.4f} '
                f'mIoU={val_iou:.4f} '
                f'Dice={val_dice:.4f} '
                f'PA={val_pa:.4f} '
                f'time={dt:.1f}s'
            )
        else:
            print(
                f'[Epoch {epoch}/{epochs}] '
                f'train_loss={train_loss:.4f} '
                f'val=skip '
                f'time={dt:.1f}s'
            )

        ckpt = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'val_iou': val_iou,
            'config': cfg,
        }
        if scaler is not None:
            ckpt['scaler_state_dict'] = scaler.state_dict()
        torch.save(ckpt, save_dir / 'last.pt')

        if do_val and val_iou > best_iou:
            best_iou = val_iou
            torch.save(ckpt, save_dir / 'best.pt')
            print(f'保存最佳模型: mIoU={best_iou:.4f}')


if __name__ == '__main__':
    main()
