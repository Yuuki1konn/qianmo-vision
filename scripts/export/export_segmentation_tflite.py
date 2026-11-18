import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import onnx
from onnx import numpy_helper
import numpy as np

def ensure_onnx_helper_compat() -> None:
    if hasattr(onnx.helper, "float32_to_bfloat16"):
        return

    def float32_to_bfloat16(value):
        import numpy as np

        arr = np.asarray(value, dtype=np.float32)
        bits = arr.view(np.uint32)
        rounding_bias = np.uint32(0x7FFF) + ((bits >> 16) & np.uint32(1))
        bf16 = ((bits + rounding_bias) >> 16).astype(np.uint16)
        if np.isscalar(value):
            return int(bf16.reshape(-1)[0])
        return bf16

    onnx.helper.float32_to_bfloat16 = float32_to_bfloat16


ensure_onnx_helper_compat()

from onnx2tf import convert
import onnx2tf.onnx2tf as onnx2tf_module
import onnx2tf.utils.common_functions as onnx2tf_common

from scripts.train.seg_models import create_model


def export_to_onnx(model_name: str, ckpt_path: Path, onnx_path: Path, input_size: int, device: str):
    model = create_model(model_name).to(device)
    ckpt = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()

    dummy = torch.randn(1, 3, input_size, input_size, device=device)
    torch.onnx.export(
        model,
        dummy,
        str(onnx_path),
        input_names=['input'],
        output_names=['output'],
        opset_version=18,
    )


def patch_convtranspose_kernel_shape(onnx_path: Path) -> None:
    model = onnx.load(str(onnx_path), load_external_data=True)
    initializer_map = {init.name: numpy_helper.to_array(init) for init in model.graph.initializer}
    updated = 0

    for node in model.graph.node:
        if node.op_type != 'ConvTranspose' or len(node.input) < 2:
            continue

        has_kernel_shape = any(attr.name == 'kernel_shape' for attr in node.attribute)
        if has_kernel_shape:
            continue

        weights = initializer_map.get(node.input[1])
        if weights is None or weights.ndim < 3:
            continue

        kernel_shape = list(weights.shape[2:])
        node.attribute.append(onnx.helper.make_attribute('kernel_shape', kernel_shape))
        updated += 1

    if updated:
        onnx.save_model(
            model,
            str(onnx_path),
            save_as_external_data=True,
            all_tensors_to_one_file=True,
            location=onnx_path.name + '.data',
        )
        print(f'已为 {updated} 个 ConvTranspose 节点补充 kernel_shape')


def ensure_onnx2tf_offline_compat(input_size: int) -> None:
    def offline_test_image_data():
        # onnx2tf 默认联网下载示例图，这里改为本地生成，避免离线环境卡死。
        return np.random.default_rng(0).random((20, input_size, input_size, 3), dtype=np.float32)

    onnx2tf_common.download_test_image_data = offline_test_image_data
    onnx2tf_module.download_test_image_data = offline_test_image_data


def convert_onnx_to_tflite(onnx_path: Path, out_dir: Path, int8: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    convert(
        input_onnx_file_path=str(onnx_path),
        output_folder_path=str(out_dir),
        output_dynamic_range_quantized_tflite=int8,
    )

    if int8:
        matches = sorted(out_dir.glob('*dynamic_range_quant.tflite'))
        if matches:
            target = out_dir / 'segmentation_dynamic_range.tflite'
            shutil.copyfile(matches[0], target)
            return target

    for pattern, dst_name in (
        ('*float16.tflite', 'segmentation_fp16.tflite'),
        ('*float32.tflite', 'segmentation_fp32.tflite'),
    ):
        matches = sorted(out_dir.glob(pattern))
        if matches:
            target = out_dir / dst_name
            shutil.copyfile(matches[0], target)
            return target

    raise FileNotFoundError(f'未找到导出的 TFLite 文件: {out_dir}')


def main() -> None:
    parser = argparse.ArgumentParser(description='将分割模型（PyTorch）导出为 TFLite')
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--model-name', type=str, default='unet', choices=['unet', 'deeplabv3plus', 'deeplab'])
    parser.add_argument('--output-dir', type=Path, default=Path('runs/export/segmentation'))
    parser.add_argument('--input-size', type=int, default=640)
    parser.add_argument('--int8', action='store_true')
    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = args.output_dir / 'segmentation.onnx'

    print('步骤1/2：导出 ONNX')
    export_to_onnx(args.model_name, args.checkpoint, onnx_path, args.input_size, device)
    patch_convtranspose_kernel_shape(onnx_path)
    ensure_onnx2tf_offline_compat(args.input_size)
    print(f'ONNX 已生成：{onnx_path}')

    print('步骤2/2：转换 TFLite')
    tflite_path = convert_onnx_to_tflite(onnx_path, args.output_dir, args.int8)
    print(f'TFLite 已生成：{tflite_path}')


if __name__ == '__main__':
    main()
