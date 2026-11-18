import argparse
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image


CENTER_SAFE_RATIO = 0.55
NARROW_ROAD_RATIO = 0.18
OVERLAY_COLOR = np.array([0, 200, 120], dtype=np.uint8)
OVERLAY_ALPHA = 110 / 255.0


def is_ascii_path(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def prepare_model_path(model_path: Path) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    model_path = model_path.resolve()
    external_data = model_path.with_name(model_path.name + ".data")
    if is_ascii_path(model_path) and (not external_data.exists() or is_ascii_path(external_data)):
        return model_path, None

    temp_dir = tempfile.TemporaryDirectory(prefix="seg_model_ascii_")
    temp_root = Path(temp_dir.name)
    copied_model = temp_root / model_path.name
    shutil.copy2(model_path, copied_model)
    if external_data.exists():
        shutil.copy2(external_data, temp_root / external_data.name)
    return copied_model, temp_dir


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def preprocess_image(image_path: Path, input_size: int) -> tuple[Image.Image, Image.Image, np.ndarray]:
    original = Image.open(image_path).convert("RGB")
    resized = original.resize((input_size, input_size), Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    tensor = np.transpose(arr, (2, 0, 1))[None, ...]
    return original, resized, tensor


def mask_bbox(mask: np.ndarray) -> dict[str, int] | None:
    positive = np.argwhere(mask > 0)
    if positive.size == 0:
        return None
    top, left = positive.min(axis=0).tolist()
    bottom, right = positive.max(axis=0).tolist()
    return {
        "left": int(left),
        "top": int(top),
        "right": int(right),
        "bottom": int(bottom),
        "width": int(right - left + 1),
        "height": int(bottom - top + 1),
    }


def compute_drive_state(mask: np.ndarray) -> dict[str, object]:
    height, width = mask.shape
    drivable_ratio = float(mask.mean())

    center_x = width // 2
    band_top = max(int(height * CENTER_SAFE_RATIO), 0)
    band_left = max(center_x - width // 10, 0)
    band_right = min(center_x + width // 10, width - 1)
    center_band = mask[band_top:height, band_left:band_right + 1]
    center_safe = True if center_band.size == 0 else float(center_band.mean()) >= 0.35

    horizon_y = min(max(int(height * 0.58), 0), height - 1)
    horizon_row = mask[horizon_y]
    positives = np.flatnonzero(horizon_row > 0)
    if positives.size == 0:
        road_narrow = True
        horizon_width_ratio = 0.0
    else:
        horizon_width_ratio = float((positives[-1] - positives[0] + 1) / width)
        road_narrow = horizon_width_ratio < NARROW_ROAD_RATIO

    if not center_safe:
        status_text = "靠近道路边缘"
    elif road_narrow:
        status_text = "前方可行驶区域变窄"
    else:
        status_text = "前方道路正常"

    return {
        "drivable_ratio": drivable_ratio,
        "center_safe": center_safe,
        "road_narrow": road_narrow,
        "horizon_width_ratio": horizon_width_ratio,
        "status_text": status_text,
        "mask_bbox": mask_bbox(mask),
    }


def compute_region_coverage(mask: np.ndarray) -> dict[str, float]:
    height, width = mask.shape
    thirds = [
        ("bottom_left", mask[int(height * 0.6):height, 0:int(width / 3)]),
        ("bottom_center", mask[int(height * 0.6):height, int(width / 3):int(width * 2 / 3)]),
        ("bottom_right", mask[int(height * 0.6):height, int(width * 2 / 3):width]),
    ]
    return {
        name: (float(region.mean()) if region.size else 0.0)
        for name, region in thirds
    }


def compute_vertical_coverage(mask: np.ndarray) -> dict[str, float]:
    height, _ = mask.shape
    bands = [
        ("top", mask[0:int(height / 3), :]),
        ("middle", mask[int(height / 3):int(height * 2 / 3), :]),
        ("bottom", mask[int(height * 2 / 3):height, :]),
    ]
    positive_rows = np.flatnonzero(mask.any(axis=1))
    first_positive_row_ratio = None
    if positive_rows.size > 0:
        first_positive_row_ratio = float(positive_rows[0] / height)
    return {
        **{
            name: (float(region.mean()) if region.size else 0.0)
            for name, region in bands
        },
        "first_positive_row_ratio": first_positive_row_ratio,
    }


def overlay_mask_on_image(original: Image.Image, mask_192: np.ndarray) -> Image.Image:
    mask_full = Image.fromarray((mask_192 * 255).astype(np.uint8), mode="L").resize(
        original.size,
        Image.Resampling.NEAREST,
    )
    base = np.asarray(original.convert("RGB"), dtype=np.uint8)
    mask = np.asarray(mask_full, dtype=np.uint8) > 0
    overlay = base.copy()
    overlay[mask] = np.clip(
        base[mask] * (1.0 - OVERLAY_ALPHA) + OVERLAY_COLOR * OVERLAY_ALPHA,
        0,
        255,
    ).astype(np.uint8)
    return Image.fromarray(overlay, mode="RGB")


def probability_stats(probs: np.ndarray) -> dict[str, float]:
    return {
        "min": float(probs.min()),
        "p25": float(np.quantile(probs, 0.25)),
        "p50": float(np.quantile(probs, 0.50)),
        "p75": float(np.quantile(probs, 0.75)),
        "p90": float(np.quantile(probs, 0.90)),
        "max": float(probs.max()),
        "mean": float(probs.mean()),
    }


def analyze_image(
    session: ort.InferenceSession,
    image_path: Path,
    output_dir: Path,
    threshold: float,
) -> dict[str, object]:
    input_meta = session.get_inputs()[0]
    input_name = input_meta.name
    _, _, input_size, _ = input_meta.shape
    output_name = session.get_outputs()[0].name

    original, resized, tensor = preprocess_image(image_path, input_size)
    logits = session.run([output_name], {input_name: tensor})[0][0, 0]
    probs = sigmoid(logits)
    mask = (probs >= threshold).astype(np.uint8)

    case_dir = output_dir / image_path.stem
    case_dir.mkdir(parents=True, exist_ok=True)
    resized.save(case_dir / "input_192.png")
    Image.fromarray((mask * 255).astype(np.uint8), mode="L").save(case_dir / "mask_192.png")
    overlay_mask_on_image(original, mask).save(case_dir / "overlay.png")

    report = {
        "image_path": str(image_path.resolve()),
        "threshold": threshold,
        "input_size": int(input_size),
        "probability_stats": probability_stats(probs),
        "drive_state": compute_drive_state(mask),
        "bottom_region_coverage": compute_region_coverage(mask),
        "vertical_coverage": compute_vertical_coverage(mask),
    }
    (case_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="用 ONNX 分析分割问题图并导出 overlay/mask/report")
    parser.add_argument("--model", type=Path, required=True, help="ONNX 模型路径")
    parser.add_argument("--image", type=Path, nargs="+", required=True, help="待分析图片路径")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    parser.add_argument("--threshold", type=float, default=0.5, help="二值化阈值")
    args = parser.parse_args()

    prepared_model, temp_dir = prepare_model_path(args.model)
    try:
        session = ort.InferenceSession(str(prepared_model), providers=["CPUExecutionProvider"])
        args.output_dir.mkdir(parents=True, exist_ok=True)
        summary = {}
        for image_path in args.image:
            report = analyze_image(session, image_path, args.output_dir, args.threshold)
            summary[image_path.stem] = report
            state = report["drive_state"]
            print(
                f"{image_path.name}: status={state['status_text']} "
                f"drivable_ratio={state['drivable_ratio']:.3f} "
                f"center_safe={state['center_safe']} "
                f"road_narrow={state['road_narrow']}"
            )
        (args.output_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    main()
