import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description='评估检测模型指标（mAP/Precision/Recall）')
    parser.add_argument('--weights', type=Path, required=True, help='YOLO 权重路径')
    parser.add_argument('--data', type=Path, default=Path('configs/yolo_dataset.yaml'))
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--device', type=str, default='0')
    args = parser.parse_args()

    model = YOLO(str(args.weights))
    metrics = model.val(data=str(args.data), imgsz=args.imgsz, device=args.device)

    print('评估完成')
    print(f"mAP@0.5: {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")


if __name__ == '__main__':
    main()
