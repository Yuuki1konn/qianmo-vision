import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import torch
import yaml

from scripts.train.seg_models import create_model


VALID_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def postprocess_mask(binary: np.ndarray, close_kernel: int, min_area: int) -> np.ndarray:
    mask = binary.copy()
    if close_kernel and close_kernel > 1:
        kernel = np.ones((close_kernel, close_kernel), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    if min_area and min_area > 0:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), connectivity=8)
        filtered = np.zeros_like(mask)
        for idx in range(1, num_labels):
            area = int(stats[idx, cv2.CC_STAT_AREA])
            if area >= min_area:
                filtered[labels == idx] = 255
        mask = filtered

    return mask


def main() -> None:
    parser = argparse.ArgumentParser(description='生成分割预测掩码')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--image-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--threshold', type=float, default=0.5)
    parser.add_argument('--close-kernel', type=int, default=0, help='闭运算核大小，0 表示不做后处理')
    parser.add_argument('--min-area', type=int, default=0, help='去除小连通域面积阈值，0 表示不过滤')
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
    image_size = tuple(cfg.get('image_size', [640, 640]))
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    model = create_model(cfg.get('model_name', 'unet')).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()

    images = sorted([p for p in args.image_dir.rglob('*') if p.suffix.lower() in VALID_EXT])
    if args.limit > 0:
        images = images[:args.limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with torch.no_grad():
        for image_path in images:
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                continue

            resized = cv2.resize(image, image_size, interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = torch.tensor(np.transpose(rgb, (2, 0, 1)), dtype=torch.float32).unsqueeze(0).to(device)

            logits = model(tensor)
            probs = torch.sigmoid(logits)[0, 0].cpu().numpy()
            pred = (probs > args.threshold).astype(np.uint8) * 255
            pred = postprocess_mask(pred, args.close_kernel, args.min_area)

            out_path = args.output_dir / f'{image_path.stem}.png'
            cv2.imwrite(str(out_path), pred)

    print(f'预测完成: {len(images)} 张 -> {args.output_dir}')


if __name__ == '__main__':
    main()
