import argparse
import os
import shutil
from pathlib import Path

import yaml


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


def resolve_images_from_data_yaml(data_yaml: Path, split: str) -> Path:
    data = yaml.safe_load(data_yaml.read_text(encoding='utf-8'))
    root = Path(data.get('path', '.'))
    split_dir = data.get(split)
    if not split_dir:
        raise ValueError(f'找不到 split={split} 的图像目录')
    return (root / split_dir).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description='检测模型推理并输出预测标签')
    parser.add_argument('--weights', type=Path, required=True, help='YOLO 权重路径')
    parser.add_argument('--data', type=Path, default=Path('configs/yolo_dataset.yaml'))
    parser.add_argument('--split', choices=['train', 'val', 'test'], default='val')
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--device', type=str, default='0')
    parser.add_argument('--conf', type=float, default=0.25)
    parser.add_argument('--project', type=Path, default=Path('runs/pred'))
    parser.add_argument('--name', type=str, default='det')
    args = parser.parse_args()

    ensure_ultralytics_config_dir()
    patch_ultralytics_threadpool()
    from ultralytics import YOLO

    image_dir = resolve_images_from_data_yaml(args.data, args.split)
    model = YOLO(str(args.weights))
    project_dir = args.project.resolve()
    model.predict(
        source=str(image_dir),
        imgsz=args.imgsz,
        device=args.device,
        conf=args.conf,
        save_txt=True,
        save_conf=True,
        project=str(project_dir),
        name=args.name,
        exist_ok=True,
        verbose=False,
        workers=0,
    )

    out_dir = project_dir / args.name / "labels"
    print(f'预测完成：{out_dir}')


if __name__ == '__main__':
    main()
