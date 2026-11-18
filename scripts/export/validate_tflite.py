import argparse
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import tensorflow as tf
from tqdm import tqdm


VALID_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def preprocess(img_path: Path, size: int):
    img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f'读取图像失败: {img_path}')
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_LINEAR)
    x = img.astype(np.float32) / 255.0
    x = np.transpose(x, (2, 0, 1))[None, ...]
    return x


def run_onnx(session: ort.InferenceSession, x: np.ndarray):
    input_name = session.get_inputs()[0].name
    out = session.run(None, {input_name: x})[0]
    return out


def run_tflite(interpreter: tf.lite.Interpreter, x: np.ndarray):
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    x_nhwc = np.transpose(x, (0, 2, 3, 1)).astype(np.float32)
    interpreter.set_tensor(input_details[0]['index'], x_nhwc)
    interpreter.invoke()
    out = interpreter.get_tensor(output_details[0]['index'])

    if out.ndim == 4 and out.shape[1] != 1 and out.shape[-1] == 1:
        out = np.transpose(out, (0, 3, 1, 2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description='验证 TFLite 与 ONNX 输出一致性（平均误差）')
    parser.add_argument('--onnx', type=Path, required=True)
    parser.add_argument('--tflite', type=Path, required=True)
    parser.add_argument('--image-dir', type=Path, required=True)
    parser.add_argument('--input-size', type=int, default=640)
    parser.add_argument('--max-samples', type=int, default=50)
    args = parser.parse_args()

    imgs = [p for p in args.image_dir.rglob('*') if p.suffix.lower() in VALID_EXT][:args.max_samples]
    if not imgs:
        raise RuntimeError('未找到可用图像')

    onnx_sess = ort.InferenceSession(str(args.onnx), providers=['CPUExecutionProvider'])
    tflite_interpreter = tf.lite.Interpreter(model_path=str(args.tflite))
    tflite_interpreter.allocate_tensors()

    l1_errors = []
    for p in tqdm(imgs, desc='一致性验证'):
        x = preprocess(p, args.input_size)
        y_onnx = run_onnx(onnx_sess, x)
        y_tflite = run_tflite(tflite_interpreter, x)

        min_shape = tuple(min(a, b) for a, b in zip(y_onnx.shape, y_tflite.shape))
        slices = tuple(slice(0, s) for s in min_shape)
        y1 = y_onnx[slices]
        y2 = y_tflite[slices]

        l1 = float(np.mean(np.abs(y1 - y2)))
        l1_errors.append(l1)

    mean_l1 = float(np.mean(l1_errors))
    max_l1 = float(np.max(l1_errors))

    print(f'样本数: {len(l1_errors)}')
    print(f'平均 L1 误差: {mean_l1:.6f}')
    print(f'最大 L1 误差: {max_l1:.6f}')

    if mean_l1 < 0.02:
        print('结论：TFLite 与 ONNX 输出基本一致')
    else:
        print('结论：误差偏高，建议检查量化或输入预处理')


if __name__ == '__main__':
    main()
