import argparse
import os
import shutil
from pathlib import Path

import yaml


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


def ensure_ultralytics_config_dir() -> None:
    if "YOLO_CONFIG_DIR" not in os.environ:
        os.environ["YOLO_CONFIG_DIR"] = str(Path(".yolo_config").resolve())

    config_root = Path(os.environ["YOLO_CONFIG_DIR"]) / "Ultralytics"
    config_root.mkdir(parents=True, exist_ok=True)

    target_font = config_root / "Arial.ttf"
    system_font = Path(r"C:\Windows\Fonts\arial.ttf")
    if not target_font.exists() and system_font.exists():
        shutil.copy2(system_font, target_font)


def main() -> None:
    parser = argparse.ArgumentParser(description='训练二轮车检测模型（YOLOv8）')
    parser.add_argument('--config', type=Path, default=Path('configs/detection.yaml'))
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))

    ensure_ultralytics_config_dir()
    from ultralytics import YOLO

    patch_ultralytics_threadpool()
    model = YOLO(cfg.get('model', 'yolov8n.pt'))
    results = model.train(
        data=cfg.get('data_yaml', 'configs/yolo_dataset.yaml'),
        epochs=int(cfg.get('epochs', 120)),
        batch=int(cfg.get('batch', 16)),
        imgsz=int(cfg.get('imgsz', 640)),
        device=cfg.get('device', 0),
        project=cfg.get('project', 'runs/detection'),
        name=cfg.get('name', 'yolov8_rural'),
        workers=int(cfg.get('workers', 8)),
        amp=bool(cfg.get('amp', True)),
        pretrained=bool(cfg.get('pretrained', True)),
        exist_ok=bool(cfg.get('exist_ok', True)),
        verbose=bool(cfg.get('verbose', True)),
        resume=bool(cfg.get('resume', False)),
    )

    print('训练完成')
    print(results)


if __name__ == '__main__':
    main()
