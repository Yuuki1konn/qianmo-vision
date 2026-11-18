import argparse
from pathlib import Path

import csv
import math
import yaml


VALID_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def load_names(data_yaml: Path) -> list[str]:
    data = yaml.safe_load(data_yaml.read_text(encoding='utf-8'))
    names = data.get('names', [])
    if isinstance(names, dict):
        return [names[k] for k in sorted(names.keys())]
    if isinstance(names, list):
        return names
    return []


def read_labels(path: Path, has_conf: bool, conf_th: float) -> list[tuple[int, float, float, float, float, float]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls_id = int(float(parts[0]))
        x, y, w, h = map(float, parts[1:5])
        conf = float(parts[5]) if has_conf and len(parts) >= 6 else 1.0
        if conf < conf_th:
            continue
        out.append((cls_id, x, y, w, h, conf))
    return out


def xywh_to_xyxy(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, w, h = box
    x1 = x - w / 2
    y1 = y - h / 2
    x2 = x + w / 2
    y2 = y + h / 2
    return x1, y1, x2, y2


def iou(box1: tuple[float, float, float, float], box2: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = xywh_to_xyxy(box1)
    x3, y3, x4, y4 = xywh_to_xyxy(box2)
    inter_x1 = max(x1, x3)
    inter_y1 = max(y1, y3)
    inter_x2 = min(x2, x4)
    inter_y2 = min(y2, y4)
    iw = max(0.0, inter_x2 - inter_x1)
    ih = max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area1 = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area2 = max(0.0, x4 - x3) * max(0.0, y4 - y3)
    denom = area1 + area2 - inter
    return inter / denom if denom > 0 else 0.0


def match_boxes(gt, pred, iou_th: float) -> tuple[list[int], list[int]]:
    matched_gt = set()
    matched_pred = set()
    for gi, g in enumerate(gt):
        g_cls, gx, gy, gw, gh, _ = g
        best_iou = 0.0
        best_pi = -1
        for pi, p in enumerate(pred):
            if pi in matched_pred:
                continue
            p_cls, px, py, pw, ph, _ = p
            if p_cls != g_cls:
                continue
            i = iou((gx, gy, gw, gh), (px, py, pw, ph))
            if i > best_iou:
                best_iou = i
                best_pi = pi
        if best_pi >= 0 and best_iou >= iou_th:
            matched_gt.add(gi)
            matched_pred.add(best_pi)
    return list(matched_gt), list(matched_pred)


def main() -> None:
    parser = argparse.ArgumentParser(description='检测误差分析：统计 FN/FP 并输出难例清单')
    parser.add_argument('--image-dir', type=Path, required=True)
    parser.add_argument('--gt-dir', type=Path, required=True)
    parser.add_argument('--pred-dir', type=Path, required=True)
    parser.add_argument('--data', type=Path, default=Path('configs/yolo_dataset.yaml'))
    parser.add_argument('--output-md', type=Path, default=Path('docs/检测模型误差分析_按类样例.md'))
    parser.add_argument('--output-csv', type=Path, default=Path('runs/analysis/hard_cases.csv'))
    parser.add_argument('--iou', type=float, default=0.5)
    parser.add_argument('--conf', type=float, default=0.25)
    parser.add_argument('--top-k', type=int, default=50)
    args = parser.parse_args()

    names = load_names(args.data)
    nc = len(names)
    images = [p for p in args.image_dir.rglob('*') if p.suffix.lower() in VALID_EXT]

    per_class_gt = [0] * nc
    per_class_tp = [0] * nc
    per_class_fp = [0] * nc
    per_class_fn = [0] * nc

    rows = []
    duplicate_label_files = []

    for img_path in images:
        stem = img_path.stem
        gt_path = args.gt_dir / f'{stem}.txt'
        pred_path = args.pred_dir / f'{stem}.txt'
        gt = read_labels(gt_path, has_conf=False, conf_th=0.0)
        pred = read_labels(pred_path, has_conf=True, conf_th=args.conf)

        if gt_path.exists():
            lines = gt_path.read_text(encoding='utf-8').splitlines()
            if len(lines) != len(set(lines)) and len(lines) > 0:
                duplicate_label_files.append(str(gt_path))

        for g in gt:
            if 0 <= g[0] < nc:
                per_class_gt[g[0]] += 1
        for p in pred:
            if 0 <= p[0] < nc:
                pass

        matched_gt, matched_pred = match_boxes(gt, pred, args.iou)
        matched_gt_set = set(matched_gt)
        matched_pred_set = set(matched_pred)

        fn_counts = [0] * nc
        fp_counts = [0] * nc

        for gi, g in enumerate(gt):
            cls_id = g[0]
            if cls_id < 0 or cls_id >= nc:
                continue
            if gi in matched_gt_set:
                per_class_tp[cls_id] += 1
            else:
                per_class_fn[cls_id] += 1
                fn_counts[cls_id] += 1

        for pi, p in enumerate(pred):
            cls_id = p[0]
            if cls_id < 0 or cls_id >= nc:
                continue
            if pi not in matched_pred_set:
                per_class_fp[cls_id] += 1
                fp_counts[cls_id] += 1

        rows.append({
            'image': str(img_path),
            'fn_total': sum(fn_counts),
            'fp_total': sum(fp_counts),
            **{f'fn_{names[i]}': fn_counts[i] for i in range(nc)},
            **{f'fp_{names[i]}': fp_counts[i] for i in range(nc)},
        })

    rows_sorted_fn = sorted(rows, key=lambda r: r['fn_total'], reverse=True)
    rows_sorted_fp = sorted(rows, key=lambda r: r['fp_total'], reverse=True)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open('w', encoding='utf-8', newline='') as f:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    lines = [
        '# 检测模型误差分析（按类样例）',
        '',
        f'- 评估样本数：{len(images)}',
        f'- IoU 阈值：{args.iou}',
        f'- 预测置信度阈值：{args.conf}',
        '',
        '## 1. 按类统计（基于匹配结果）',
        '',
        '| 类别 | GT | TP | FN | Recall | FP |',
        '|---|---:|---:|---:|---:|---:|',
    ]

    for i, name in enumerate(names):
        gt = per_class_gt[i]
        tp = per_class_tp[i]
        fn = per_class_fn[i]
        fp = per_class_fp[i]
        recall = tp / gt if gt > 0 else 0.0
        lines.append(f'| {name} | {gt} | {tp} | {fn} | {recall:.4f} | {fp} |')

    lines += [
        '',
        '## 2. 漏检最多的样例（Top K）',
        '',
    ]

    for r in rows_sorted_fn[: args.top_k]:
        lines.append(f"- {r['image']} (FN={r['fn_total']}, FP={r['fp_total']})")

    lines += [
        '',
        '## 3. 误检最多的样例（Top K）',
        '',
    ]

    for r in rows_sorted_fp[: args.top_k]:
        lines.append(f"- {r['image']} (FN={r['fn_total']}, FP={r['fp_total']})")

    if duplicate_label_files:
        lines += [
            '',
            '## 4. 存在重复标签的文件（抽样）',
            '',
        ]
        for path in duplicate_label_files[: min(50, len(duplicate_label_files))]:
            lines.append(f'- {path}')

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text('\n'.join(lines), encoding='utf-8')
    print(f'误差分析已生成：{args.output_md}')
    print(f'样例清单已生成：{args.output_csv}')


if __name__ == '__main__':
    main()
