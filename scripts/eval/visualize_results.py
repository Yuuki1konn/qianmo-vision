import argparse
from pathlib import Path

import cv2
import numpy as np


VALID_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def visualize_segmentation(image_path: Path, gt_mask_path: Path, pred_mask_path: Path, out_path: Path):
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    gt = cv2.imread(str(gt_mask_path), cv2.IMREAD_GRAYSCALE)
    pred = cv2.imread(str(pred_mask_path), cv2.IMREAD_GRAYSCALE)

    if img is None or gt is None or pred is None:
        return

    h, w = img.shape[:2]
    if gt.shape[:2] != (h, w):
        gt = cv2.resize(gt, (w, h), interpolation=cv2.INTER_NEAREST)
    if pred.shape[:2] != (h, w):
        pred = cv2.resize(pred, (w, h), interpolation=cv2.INTER_NEAREST)

    gt_color = np.zeros_like(img)
    gt_color[..., 1] = (gt > 0).astype(np.uint8) * 255

    pred_color = np.zeros_like(img)
    pred_color[..., 2] = (pred > 0).astype(np.uint8) * 255

    gt_blend = cv2.addWeighted(img, 1.0, gt_color, 0.35, 0)
    pred_blend = cv2.addWeighted(img, 1.0, pred_color, 0.35, 0)

    canvas = np.concatenate([img, gt_blend, pred_blend], axis=1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)


def draw_boxes(image, txt_path: Path, color: tuple, class_names: list[str]):
    if not txt_path.exists():
        return image
    h, w = image.shape[:2]
    out = image.copy()
    for line in txt_path.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls_id = int(parts[0])
        x, y, bw, bh = map(float, parts[1:5])
        x1 = int((x - bw / 2) * w)
        y1 = int((y - bh / 2) * h)
        x2 = int((x + bw / 2) * w)
        y2 = int((y + bh / 2) * h)

        cls_name = class_names[cls_id] if cls_id < len(class_names) else f'cls_{cls_id}'
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, cls_name, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return out


def visualize_detection(image_path: Path, gt_txt: Path, pred_txt: Path, out_path: Path, class_names: list[str]):
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        return

    left = draw_boxes(img, gt_txt, (0, 220, 0), class_names)
    right = draw_boxes(img, pred_txt, (0, 0, 255), class_names)
    canvas = np.concatenate([left, right], axis=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)


def main() -> None:
    parser = argparse.ArgumentParser(description='可视化模型结果（分割：原图/真值/预测；检测：真值框/预测框）')
    parser.add_argument('--task', choices=['segmentation', 'detection'], required=True)
    parser.add_argument('--image-dir', type=Path, required=True)
    parser.add_argument('--gt-dir', type=Path, required=True)
    parser.add_argument('--pred-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--class-names', nargs='*', default=['electric_bike', 'motorcycle', 'tricycle', 'pedestrian', 'animal', 'barrier', 'pothole'])
    args = parser.parse_args()

    images = [p for p in args.image_dir.rglob('*') if p.suffix.lower() in VALID_EXT]

    for img_path in images:
        stem = img_path.stem
        out_path = args.output_dir / f'{stem}_vis.jpg'

        if args.task == 'segmentation':
            gt_stem = stem.replace('_leftImg8bit', '')
            gt = args.gt_dir / f'{gt_stem}.png'
            pred = args.pred_dir / f'{gt_stem}.png'
            visualize_segmentation(img_path, gt, pred, out_path)
        else:
            gt = args.gt_dir / f'{stem}.txt'
            pred = args.pred_dir / f'{stem}.txt'
            visualize_detection(img_path, gt, pred, out_path, args.class_names)

    print(f'可视化完成：{args.output_dir}')


if __name__ == '__main__':
    main()
