import argparse
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import onnx
from onnx import helper
from ultralytics import YOLO


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = REPO_ROOT / ".tools" / "onnx2tf_py310"
ONNX2TF_VERSION = "1.29.24"
ONNX_GRAPH_SURGEON_VERSION = "0.6.1"


def ensure_local_onnx2tf() -> object:
    tool_sentinel = TOOL_DIR / "onnx2tf"
    if not tool_sentinel.exists():
        TOOL_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--no-deps",
                "--target",
                str(TOOL_DIR),
                f"onnx2tf=={ONNX2TF_VERSION}",
                f"onnx-graphsurgeon=={ONNX_GRAPH_SURGEON_VERSION}",
            ],
            check=True,
        )

    sys.path.insert(0, str(TOOL_DIR))
    if not hasattr(onnx.helper, "float32_to_bfloat16"):
        def float32_to_bfloat16(value: float) -> int:
            return struct.unpack("=I", struct.pack("=f", value))[0] >> 16

        onnx.helper.float32_to_bfloat16 = float32_to_bfloat16

    import onnx2tf

    return onnx2tf


def export_base_onnx(
    weights: Path,
    imgsz: int,
    target_dir: Path
) -> Path:
    model = YOLO(str(weights))
    exported = Path(
        model.export(
            format="onnx",
            imgsz=imgsz,
            opset=17,
            simplify=True,
        )
    )
    target_path = target_dir / f"detection_{imgsz}.onnx"
    if exported.resolve() != target_path.resolve():
        shutil.copy2(exported, target_path)
    return target_path


def rewrite_equal_splits_for_tflite(
    source_model: Path,
    target_model: Path
) -> Path:
    model = onnx.load(source_model)
    for opset in model.opset_import:
        if opset.domain == "":
            opset.version = max(opset.version, 18)

    rewritten_nodes = []
    for node in model.graph.node:
        if node.op_type == "Split" and len(node.input) == 2:
            attrs = {attr.name: onnx.helper.get_attribute_value(attr) for attr in node.attribute}
            axis = attrs.get("axis", 0)
            rewritten_nodes.append(
                helper.make_node(
                    "Split",
                    inputs=[node.input[0]],
                    outputs=list(node.output),
                    name=node.name,
                    axis=axis,
                    num_outputs=len(node.output),
                )
            )
        else:
            rewritten_nodes.append(node)

    del model.graph.node[:]
    model.graph.node.extend(rewritten_nodes)
    onnx.checker.check_model(model)
    onnx.save(model, target_model)
    return target_model


def expose_intermediate_outputs(
    source_model: Path,
    target_model: Path
) -> Path:
    model = onnx.load(source_model)
    model.graph.node.extend(
        [
            helper.make_node(
                "Identity",
                inputs=["/model.22/dfl/Reshape_1_output_0"],
                outputs=["dfl_out"],
                name="alias_dfl_out",
            ),
            helper.make_node(
                "Identity",
                inputs=["/model.22/Sigmoid_output_0"],
                outputs=["cls_out"],
                name="alias_cls_out",
            ),
        ]
    )

    while model.graph.output:
        model.graph.output.pop()
    model.graph.output.extend(
        [
            helper.make_tensor_value_info("dfl_out", onnx.TensorProto.FLOAT, [1, 4, None]),
            helper.make_tensor_value_info("cls_out", onnx.TensorProto.FLOAT, [1, 6, None]),
        ]
    )

    onnx.checker.check_model(model)
    onnx.save(model, target_model)
    return target_model


def convert_to_tflite(
    onnx_model: Path,
    target_dir: Path,
    use_float16: bool
) -> Path:
    onnx2tf = ensure_local_onnx2tf()
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rv_onnx2tf_") as temp_dir:
        work_dir = Path(temp_dir) / "build"
        onnx2tf.convert(
            input_onnx_file_path=str(onnx_model),
            output_folder_path=str(work_dir),
            not_use_onnxsim=True,
            verbosity="error",
            enable_batchmatmul_unfold=True,
            output_signaturedefs=False,
        )

        suffix = "float16" if use_float16 else "float32"
        tflite_model = work_dir / f"{onnx_model.stem}_{suffix}.tflite"
        if not tflite_model.exists():
            raise FileNotFoundError(f"未找到导出的 TFLite 文件: {tflite_model}")
        copied_path = target_dir / tflite_model.name
        shutil.copy2(tflite_model, copied_path)
        return copied_path


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 Android 可用的 YOLOv8 检测 TFLite（中间输出解码版）")
    parser.add_argument("--weights", type=Path, help="训练好的 YOLO 权重文件")
    parser.add_argument("--onnx", type=Path, help="已有的 ONNX 检测模型")
    parser.add_argument("--imgsz", type=int, default=512)
    parser.add_argument("--target-dir", type=Path, default=Path("runs/export/detection_tflite_512"))
    parser.add_argument("--output-name", type=str, default="detection.tflite")
    parser.add_argument("--copy-to-assets", action="store_true", help="同时复制到 android assets")
    parser.add_argument("--float32", action="store_true", help="输出 float32 TFLite；默认输出 float16")
    args = parser.parse_args()

    if not args.weights and not args.onnx:
        parser.error("至少提供 --weights 或 --onnx 其中之一")

    target_dir = (REPO_ROOT / args.target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if args.onnx:
        base_onnx = args.onnx.resolve()
    else:
        base_onnx = export_base_onnx(args.weights.resolve(), args.imgsz, target_dir)

    splitnum_onnx = rewrite_equal_splits_for_tflite(
        base_onnx,
        target_dir / f"{base_onnx.stem}_splitnum_op18.onnx",
    )
    intermediate_onnx = expose_intermediate_outputs(
        splitnum_onnx,
        target_dir / f"{base_onnx.stem}_intermediate_named.onnx",
    )

    exported_tflite = convert_to_tflite(
        intermediate_onnx,
        target_dir,
        use_float16=not args.float32,
    )

    final_tflite = target_dir / args.output_name
    shutil.copy2(exported_tflite, final_tflite)
    print("导出完成")
    print(f"ONNX 基础模型: {base_onnx}")
    print(f"Split 重写模型: {splitnum_onnx}")
    print(f"中间输出模型: {intermediate_onnx}")
    print(f"TFLite 模型: {final_tflite}")

    if args.copy_to_assets:
        assets_path = REPO_ROOT / "android/app/src/main/assets" / args.output_name
        shutil.copy2(final_tflite, assets_path)
        print(f"已复制到 Android assets: {assets_path}")


if __name__ == "__main__":
    main()
