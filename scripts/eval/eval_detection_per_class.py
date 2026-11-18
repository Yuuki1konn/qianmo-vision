import argparse
from pathlib import Path

import os
import shutil
import yaml


def load_names(data_yaml: Path) -> list[str]:
    data = yaml.safe_load(data_yaml.read_text(encoding='utf-8'))
    names = data.get('names', [])
    if isinstance(names, dict):
        return [names[k] for k in sorted(names.keys())]
    if isinstance(names, list):
        return names
    return []


def ensure_ultralytics_config_dir() -> None:
    if "YOLO_CONFIG_DIR" not in os.environ:
        os.environ["YOLO_CONFIG_DIR"] = str(Path(".yolo_config").resolve())

    config_root = Path(os.environ["YOLO_CONFIG_DIR"]) / "Ultralytics"
    config_root.mkdir(parents=True, exist_ok=True)

    target_font = config_root / "Arial.ttf"
    system_font = Path(r"C:\Windows\Fonts\arial.ttf")
    if not target_font.exists() and system_font.exists():
        shutil.copy2(system_font, target_font)


class SerialPool:
    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def imap(self, func, iterable):
        for item in iterable:
            yield func(item)


def patch_ultralytics_threadpool() -> None:
    from ultralytics.data import dataset as yolo_dataset

    yolo_dataset.ThreadPool = SerialPool
    yolo_dataset.NUM_THREADS = 1


def to_list(arr, n: int) -> list[float]:
    if arr is None:
        return [0.0] * n
    if hasattr(arr, 'tolist'):
        arr = arr.tolist()
    if not isinstance(arr, list):
        return [0.0] * n
    if len(arr) < n:
        arr = arr + [0.0] * (n - len(arr))
    return arr


def main() -> None:
    parser = argparse.ArgumentParser(description='评估检测模型并输出按类指标')
    parser.add_argument('--weights', type=Path, required=True, help='YOLO 权重路径')
    parser.add_argument('--data', type=Path, default=Path('configs/yolo_dataset.yaml'))
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--device', type=str, default='0')
    parser.add_argument('--output-md', type=Path, default=Path('docs/检测模型按类指标.md'))
    args = parser.parse_args()

    ensure_ultralytics_config_dir()
    from ultralytics import YOLO
    names = load_names(args.data)
    model = YOLO(str(args.weights))
    patch_ultralytics_threadpool()
    metrics = model.val(data=str(args.data), imgsz=args.imgsz, device=args.device, workers=0)

    nc = len(names)
    idx = list(getattr(metrics.box, 'ap_class_index', list(range(nc))))
    p_raw = to_list(metrics.box.p, len(idx))
    r_raw = to_list(metrics.box.r, len(idx))
    ap50_raw = to_list(metrics.box.ap50, len(idx))
    ap_raw = to_list(metrics.box.ap, len(idx))

    p = [0.0] * nc
    r = [0.0] * nc
    ap50 = [0.0] * nc
    ap = [0.0] * nc
    for j, cls_id in enumerate(idx):
        if 0 <= cls_id < nc:
            p[cls_id] = p_raw[j]
            r[cls_id] = r_raw[j]
            ap50[cls_id] = ap50_raw[j]
            ap[cls_id] = ap_raw[j]

    lines = [
        '# 检测模型按类指标',
        '',
        '## 1. 总体指标',
        '',
        f'- mAP@0.5: {metrics.box.map50:.4f}',
        f'- mAP@0.5:0.95: {metrics.box.map:.4f}',
        f'- Precision: {metrics.box.mp:.4f}',
        f'- Recall: {metrics.box.mr:.4f}',
        '',
        '## 2. 按类指标',
        '',
        '| 类别 | Precision | Recall | AP@0.5 | AP@0.5:0.95 |',
        '|---|---:|---:|---:|---:|',
    ]

    for i, name in enumerate(names):
        lines.append(f'| {name} | {p[i]:.4f} | {r[i]:.4f} | {ap50[i]:.4f} | {ap[i]:.4f} |')

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text('\n'.join(lines), encoding='utf-8')
    print(f'评估完成，按类指标已写入：{args.output_md}')


if __name__ == '__main__':
    main()
