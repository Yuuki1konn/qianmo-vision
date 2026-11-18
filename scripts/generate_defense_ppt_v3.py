from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "doc"
ASSET = OUT / "_assets"
RUNS = ROOT / "runs"

PPTX = OUT / "阡陌智行结题答辩PPT_最终精美版_v3.pptx"
MD = OUT / "阡陌智行结题答辩PPT_最终精美版_v3_逐页讲稿.md"

IMG = {
    "normal": ASSET / "ui_normal.jpg",
    "edge": ASSET / "ui_edge.jpg",
    "pedestrian": ASSET / "ui_pedestrian.jpg",
    "vehicle": ASSET / "ui_vehicle_landscape.png",
    "materials": OUT / "closing_report_materials_list.png",
    "seg_compare": RUNS / "compare_strict_relaxed" / "city" / "frankfurt_000000_001236_leftImg8bit_compare.jpg",
    "det_pred": RUNS / "detect" / "runs" / "detection" / "yolov8_rural_coarse_balanced_dedup_yolov8s_imgsz704" / "val_batch0_pred.jpg",
    "det_results": RUNS / "detect" / "runs" / "detection" / "yolov8_rural_coarse_balanced_dedup_yolov8s_imgsz704" / "results.png",
    "det_pr": RUNS / "detect" / "runs" / "detection" / "yolov8_rural_coarse_balanced_dedup_yolov8s_imgsz704" / "BoxPR_curve.png",
    "det_conf": RUNS / "detect" / "runs" / "detection" / "yolov8_rural_coarse_balanced_dedup_yolov8s_imgsz704" / "confusion_matrix.png",
}


class C:
    navy = RGBColor(0x13, 0x34, 0x57)
    blue = RGBColor(0x1F, 0x74, 0xC9)
    sky = RGBColor(0xD9, 0xEC, 0xFA)
    pale = RGBColor(0xF5, 0xFA, 0xFE)
    mint = RGBColor(0x23, 0xA4, 0x7E)
    orange = RGBColor(0xF0, 0x8A, 0x2E)
    red = RGBColor(0xD8, 0x51, 0x61)
    text = RGBColor(0x24, 0x36, 0x4F)
    muted = RGBColor(0x65, 0x76, 0x8B)
    line = RGBColor(0xB9, 0xD8, 0xF0)
    white = RGBColor(0xFF, 0xFF, 0xFF)


FONT = "Microsoft YaHei"
SW, SH = 13.333, 7.5


@dataclass
class Note:
    title: str
    seconds: str
    script: str


NOTES: list[Note] = []


def add_note(title: str, seconds: str, script: str) -> None:
    NOTES.append(Note(title, seconds, script))


def style(shape, fill: RGBColor, line: RGBColor | None = None, width: float = 1.0, transparency: float = 0.0):
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.fill.transparency = transparency
    shape.line.color.rgb = line or fill
    shape.line.width = Pt(width)


def add_text(slide, text: str, x: float, y: float, w: float, h: float, size: int = 16,
             color: RGBColor = C.text, bold: bool = False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = Pt(0)
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return box


def add_multiline(slide, lines: Iterable[str], x: float, y: float, w: float, h: float,
                  size: int = 14, color: RGBColor = C.text, bullet: bool = False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    first = True
    for line in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = ("• " if bullet else "") + line
        p.font.name = FONT
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(5)
    return box


def add_round(slide, x: float, y: float, w: float, h: float, fill=C.white, line=C.line, radius=True):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    style(shape, fill, line, 1.0)
    return shape


def add_header(slide, no: int, title: str, subtitle: str = ""):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SW), Inches(0.16))
    style(bar, C.blue)
    add_text(slide, f"{no:02d}", 0.56, 0.34, 0.55, 0.3, 12, C.white, True, PP_ALIGN.CENTER)
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.52), Inches(0.28), Inches(0.66), Inches(0.42))
    style(badge, C.navy)
    add_text(slide, f"{no:02d}", 0.57, 0.36, 0.55, 0.18, 11, C.white, True, PP_ALIGN.CENTER)
    add_text(slide, title, 1.3, 0.28, 8.8, 0.45, 23, C.navy, True)
    if subtitle:
        add_text(slide, subtitle, 1.32, 0.78, 10.5, 0.24, 10, C.muted)
    add_footer(slide)


def add_footer(slide):
    add_text(slide, "阡陌智行 | 大学生创新训练计划项目结题答辩", 0.65, 7.08, 5.2, 0.18, 8, C.muted)


def add_chip(slide, text: str, x: float, y: float, w: float, fill=C.sky, color=C.navy):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.34))
    style(shape, fill, fill, 0.5)
    add_text(slide, text, x + 0.05, y + 0.08, w - 0.1, 0.12, 8, color, True, PP_ALIGN.CENTER)


def add_picture_fit(slide, path: Path, x: float, y: float, w: float, h: float, border: bool = True):
    if not path.exists():
        add_round(slide, x, y, w, h, C.white, C.red)
        add_text(slide, f"缺少图片：{path.name}", x + 0.1, y + h / 2 - 0.12, w - 0.2, 0.24, 12, C.red, True, PP_ALIGN.CENTER)
        return
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    rw, rh = iw * scale, ih * scale
    px, py = x + (w - rw) / 2, y + (h - rh) / 2
    if border:
        add_round(slide, x, y, w, h, C.white, C.line)
    slide.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(rw), Inches(rh))


def arrow(slide, x: float, y: float, w: float, h: float, color=C.blue, direction="right"):
    shape_type = MSO_SHAPE.RIGHT_ARROW if direction == "right" else MSO_SHAPE.DOWN_ARROW
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    style(shape, color, color)
    return shape


def flow_node(slide, x, y, w, h, title, body="", fill=C.white, accent=C.blue, size=14):
    add_round(slide, x, y, w, h, fill, C.line)
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.08))
    style(strip, accent)
    add_text(slide, title, x + 0.12, y + 0.18, w - 0.24, 0.24, size, C.navy, True, PP_ALIGN.CENTER)
    if body:
        add_text(slide, body, x + 0.14, y + 0.55, w - 0.28, h - 0.62, max(size - 3, 8), C.text, False, PP_ALIGN.CENTER)


def metric(slide, x, y, label, value, fill=C.white, color=C.blue):
    add_round(slide, x, y, 1.55, 0.78, fill, C.line)
    add_text(slide, label, x + 0.08, y + 0.13, 1.38, 0.13, 8, C.muted, True, PP_ALIGN.CENTER)
    add_text(slide, value, x + 0.08, y + 0.35, 1.38, 0.22, 17, color, True, PP_ALIGN.CENTER)


def slide_cover(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SW), Inches(SH))
    style(bg, C.pale)
    left = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(7.8), Inches(SH))
    style(left, RGBColor(0xE9, 0xF5, 0xFD))
    add_text(slide, "阡陌智行", 0.75, 1.05, 5.8, 0.75, 40, C.navy, True)
    add_text(slide, "农村老年电动车出行助手", 0.82, 1.88, 5.8, 0.42, 20, C.blue, True)
    add_text(slide, "大学生创新训练计划项目结题答辩", 0.83, 2.48, 5.2, 0.3, 13, C.muted)
    add_text(slide, "当前软件成果：阡陌智行农村道路识别系统（Android版）", 0.83, 3.02, 6.25, 0.32, 13, C.text)
    for i, t in enumerate(["道路分割", "目标检测", "端侧部署", "提示留证"]):
        add_chip(slide, t, 0.83 + i * 1.25, 3.63, 1.0, C.white, C.blue)
    add_picture_fit(slide, IMG["normal"], 8.2, 0.55, 4.0, 6.25, True)
    info = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(6.2), Inches(6.5), Inches(0.62))
    style(info, C.navy, C.navy)
    add_text(slide, "项目负责人：卜裕鑫    成员：卞明轩、李昌隆、窦书航    指导教师：刘岩", 1.05, 6.4, 6.05, 0.15, 9, C.white, True, PP_ALIGN.CENTER)
    add_note("封面", "20秒", "开场说明项目名称、应用场景和当前软件成果。强调本次答辩围绕 Android 端道路识别与辅助提示系统展开。")


def slide_background(slide):
    add_header(slide, 2, "研究背景：为什么要做阡陌智行", "农村非结构化道路场景复杂，低成本移动端辅助识别有实际需求")
    add_text(slide, "问题链路", 0.76, 1.2, 2.0, 0.3, 15, C.blue, True)
    nodes = [
        ("场景复杂", "土路、窄路、坑洼、混行等场景多"),
        ("规则法受限", "缺少清晰车道线，固定规则稳定性不足"),
        ("移动端需求", "二轮车场景更需要低成本、实时、易部署"),
    ]
    for i, (t, b) in enumerate(nodes):
        x = 0.78 + i * 2.2
        flow_node(slide, x, 1.75, 1.8, 1.18, t, b, C.white, [C.blue, C.orange, C.mint][i], 13)
        if i < 2:
            arrow(slide, x + 1.82, 2.18, 0.36, 0.22)
    add_picture_fit(slide, IMG["edge"], 7.45, 1.1, 4.75, 5.55, True)
    add_text(slide, "项目聚焦：移动端道路识别 + 风险提示", 0.92, 4.05, 5.7, 0.4, 23, C.navy, True)
    add_multiline(slide, [
        "不是做纯算法论文，而是把识别结果落到手机端运行。",
        "先完成软件闭环：看见道路、识别风险、给出提示、保存证据。",
    ], 0.96, 4.75, 5.65, 0.9, 14, C.text, True)
    add_note("研究背景", "30秒", "讲清楚项目从场景出发：农村道路没有稳定标线，传统规则方法难适配，所以选择移动端视觉识别和提示。")


def slide_scope(slide):
    add_header(slide, 3, "研究目标与本阶段完成范围", "主动讲清楚做了什么，也讲清楚没有把什么写成已完成")
    flow_node(slide, 0.78, 1.35, 4.2, 3.25, "原始设想", "道路识别\n障碍物检测\n语音提醒\n后续硬件联动探索", C.white, C.orange, 18)
    arrow(slide, 5.2, 2.7, 0.7, 0.35, C.blue)
    flow_node(slide, 6.1, 1.35, 5.75, 3.25, "当前已完成", "道路可行驶区域分割\n风险目标检测\n文字提示 + 语音/提示音提醒\nAndroid端部署 + 调试抓帧留证", C.white, C.mint, 18)
    add_round(slide, 1.15, 5.25, 10.3, 0.72, RGBColor(0xFF, 0xF4, 0xE8), RGBColor(0xF4, 0xC1, 0x8B))
    add_text(slide, "说明：本阶段以软件识别与提示闭环为结题成果；紧急制动等硬件联动仅作为后续展望。", 1.35, 5.48, 9.9, 0.18, 13, C.text, True, PP_ALIGN.CENTER)
    add_note("目标与范围", "35秒", "这里要稳：原始想法更大，但本阶段完成的是软件核心闭环，硬件联动不作为已完成成果。")


def slide_system(slide):
    add_header(slide, 4, "阡陌智行系统总体方案", "主链路：采集 -> 预处理 -> 推理 -> 判定 -> 渲染 -> 留证")
    steps = [
        ("采集", "CameraX\n实时画面"),
        ("预处理", "旋转/缩放\n归一化"),
        ("推理", "U-Net + YOLOv8s\n端侧模型"),
        ("判定", "位置/类别/优先级\n规则层"),
        ("渲染", "掩码/检测框\n状态文字"),
        ("留证", "原图/MASK/元数据\n抓帧保存"),
    ]
    for i, (t, b) in enumerate(steps):
        x = 0.55 + i * 2.08
        flow_node(slide, x, 1.55, 1.62, 1.28, t, b, C.white, [C.blue, C.mint, C.orange, C.blue, C.mint, C.orange][i], 14)
        if i < len(steps) - 1:
            arrow(slide, x + 1.64, 2.05, 0.32, 0.22, C.blue)
    add_round(slide, 0.85, 4.05, 11.55, 1.25, RGBColor(0xEA, 0xF6, 0xFF), C.line)
    add_text(slide, "系统输出", 1.1, 4.27, 1.5, 0.25, 15, C.navy, True)
    for i, t in enumerate(["道路掩码", "目标检测框", "中文状态提示", "语音/提示音", "抓帧留证材料"]):
        add_chip(slide, t, 2.2 + i * 1.75, 4.28, 1.45, C.white, C.blue)
    add_text(slide, "流程图只表达本项目已完成的软件识别、提示与留证链路。", 1.1, 5.05, 6.5, 0.18, 10, C.muted)
    add_note("系统总体方案", "35秒", "用一条链说明系统怎么跑：相机画面进来，预处理后进入模型推理，再由规则层转成用户能理解的提示，并保存结果。")


def slide_seg_flow(slide):
    add_header(slide, 5, "道路分割流程：U-Net 识别可行驶区域", "回答“哪一块是路”，输出像素级道路掩码")
    labels = [
        ("输入图像", "相机帧/训练图"),
        ("编码器", "下采样\n提取语义"),
        ("瓶颈层", "聚合深层特征"),
        ("解码器", "上采样\n恢复空间"),
        ("道路掩码", "道路/非道路\n二值输出"),
        ("界面叠加", "半透明显示\n辅助理解"),
    ]
    y = 1.45
    for i, (t, b) in enumerate(labels):
        x = 0.55 + i * 2.05
        flow_node(slide, x, y, 1.62, 1.18, t, b, C.white, [C.blue, C.blue, C.orange, C.mint, C.mint, C.orange][i], 13)
        if i < len(labels) - 1:
            arrow(slide, x + 1.64, y + 0.48, 0.32, 0.2, C.blue)
    add_text(slide, "为什么适合本项目", 0.75, 3.35, 2.2, 0.25, 15, C.blue, True)
    add_multiline(slide, [
        "U-Net 是编码器-解码器结构，适合像素级分割。",
        "跳跃连接保留边界细节，便于恢复道路轮廓。",
        "结构相对清晰，训练、导出和端侧部署更容易控制。",
    ], 0.82, 3.85, 5.6, 1.05, 13, C.text, True)
    add_picture_fit(slide, IMG["edge"], 7.0, 3.25, 4.55, 2.55, True)
    add_text(slide, "实机画面中的绿色区域即道路分割掩码叠加效果", 7.1, 5.9, 4.35, 0.2, 9, C.muted, False, PP_ALIGN.CENTER)
    add_note("道路分割流程", "35秒", "分割负责回答哪一块是路。U-Net 的编码器提取语义，解码器恢复像素级结果，跳跃连接帮助保留道路边界。")


def slide_seg_evidence(slide):
    add_header(slide, 6, "分割模型对比证据：Strict 与 Relaxed", "主显示采用 relaxed；strict 保留为更保守的边界参考")
    add_picture_fit(slide, IMG["seg_compare"], 0.62, 1.2, 12.05, 4.25, True)
    for i, t in enumerate(["原图", "真实标注", "strict预测", "relaxed预测"]):
        add_chip(slide, t, 0.95 + i * 3.0, 1.32, 0.82, [C.white, C.sky, RGBColor(0xEF, 0xF1, 0xFF), RGBColor(0xE8, 0xFA, 0xF2)][i], C.navy)
    add_round(slide, 0.72, 5.75, 11.75, 0.65, RGBColor(0xEA, 0xF6, 0xFF), C.line)
    add_text(slide, "结论：relaxed 对可行驶区域覆盖更连贯，更适合界面主显示；strict 更保守，可作为安全边界参考。", 0.95, 5.96, 11.25, 0.17, 12, C.text, True, PP_ALIGN.CENTER)
    add_note("分割对比证据", "35秒", "这里展示训练对比证据。strict 更保守，relaxed 覆盖更连续，所以主界面采用 relaxed，strict 可以作为安全边界参考。")


def slide_detect_flow(slide):
    add_header(slide, 7, "目标检测流程：YOLOv8s 识别风险目标", "回答“前方有什么，在哪里”，输出类别、框和置信度")
    stages = [
        ("输入图像", "道路场景帧"),
        ("Backbone", "提取多层特征"),
        ("Neck", "融合多尺度信息"),
        ("Head", "输出框/类别/置信度"),
        ("风险目标", "行人/车辆/动物/坑洼等"),
    ]
    for i, (t, b) in enumerate(stages):
        x = 0.75 + i * 2.35
        flow_node(slide, x, 1.55, 1.75, 1.25, t, b, C.white, [C.blue, C.mint, C.orange, C.blue, C.mint][i], 13)
        if i < len(stages) - 1:
            arrow(slide, x + 1.78, 2.05, 0.35, 0.2, C.blue)
    add_text(slide, "检测类别", 0.85, 3.55, 1.5, 0.26, 15, C.blue, True)
    classes = ["two_wheeler", "pedestrian", "animal", "barrier", "pothole", "tricycle"]
    for i, cls in enumerate(classes):
        add_chip(slide, cls, 0.9 + (i % 3) * 1.75, 4.02 + (i // 3) * 0.55, 1.35, C.white, C.blue)
    add_round(slide, 6.7, 3.55, 5.35, 1.55, RGBColor(0xEA, 0xF6, 0xFF), C.line)
    add_text(slide, "为什么选择 YOLOv8s", 6.95, 3.82, 2.5, 0.25, 14, C.navy, True)
    add_multiline(slide, ["单阶段检测，适合实时场景。", "相比 YOLOv8n，YOLOv8s 表达能力更强，Recall 和 mAP 更好。"], 7.0, 4.2, 4.8, 0.6, 12, C.text, True)
    add_note("目标检测流程", "35秒", "检测负责回答前方有什么目标。YOLOv8s 由 Backbone、Neck、Head 组成，输出框、类别和置信度。")


def slide_detect_evidence(slide):
    add_header(slide, 8, "检测训练与预测证据", "主讲页只放代表性预测图，曲线与混淆矩阵放在备份页")
    add_picture_fit(slide, IMG["det_pred"], 0.65, 1.2, 7.4, 5.15, True)
    add_round(slide, 8.35, 1.3, 3.75, 4.5, C.white, C.line)
    add_text(slide, "这张图说明什么", 8.65, 1.6, 3.2, 0.3, 16, C.navy, True)
    add_multiline(slide, [
        "模型能在验证图中输出目标框、类别和置信度。",
        "类别覆盖行人、两轮车、三轮车、动物、障碍物等。",
        "检测结果已可支撑原型演示，但复杂场景仍存在漏检和误检。",
    ], 8.65, 2.2, 3.15, 1.35, 13, C.text, True)
    add_text(slide, "证据来源：runs/detect/.../yolov8s_imgsz704/val_batch0_pred.jpg", 8.65, 5.25, 3.1, 0.35, 8, C.muted)
    add_note("检测训练与预测证据", "35秒", "这页证明我们不仅训练了模型，也看过验证预测结果。检测能支撑原型演示，但还没有夸大成成熟高精度产品。")


def slide_training(slide):
    add_header(slide, 9, "训练数据与训练流程", "分割和检测是两条训练线，最后都形成可导出的权重")
    data = [("BDD100K", "可行驶区域定义"), ("Cityscapes", "城市道路标注稳定"), ("IDD", "复杂道路补充")]
    for i, (t, b) in enumerate(data):
        flow_node(slide, 0.65 + i * 2.0, 1.35, 1.55, 0.95, t, b, C.white, C.blue, 12)
    arrow(slide, 6.55, 1.65, 0.55, 0.25, C.blue)
    flow_node(slide, 7.25, 1.28, 2.0, 1.08, "数据预处理", "筛选/标注/尺寸统一", C.white, C.mint, 13)
    arrow(slide, 9.45, 1.65, 0.55, 0.25, C.blue)
    flow_node(slide, 10.18, 1.28, 1.85, 1.08, "验证指标", "mIoU / mAP / Recall", C.white, C.orange, 13)
    add_text(slide, "两条训练主线", 0.8, 3.0, 2.0, 0.3, 15, C.blue, True)
    flow_node(slide, 1.0, 3.55, 4.2, 1.35, "道路分割训练", "PyTorch 原生训练 U-Net\n损失函数：BCE + Dice\n输出：道路分割权重", C.white, C.blue, 15)
    flow_node(slide, 7.2, 3.55, 4.2, 1.35, "目标检测训练", "Ultralytics 训练 YOLOv8s\n底层基于 PyTorch\n输出：检测模型权重", C.white, C.mint, 15)
    arrow(slide, 5.45, 4.1, 1.25, 0.28, C.blue)
    flow_node(slide, 5.45, 5.25, 2.25, 0.95, "训练产物", "best.pt / last.pt", C.white, C.orange, 14)
    add_note("训练数据与训练流程", "35秒", "分割训练和检测训练不是完全同一条线。分割主要用 PyTorch 自己写训练流程，检测用 Ultralytics 训练 YOLOv8s，底层仍是 PyTorch。")


def slide_model_choice(slide):
    add_header(slide, 10, "模型选择依据：对比之后再定方案", "不是只说用了什么，而是说明为什么最后这样选")
    rows = [
        ("道路定义", "strict", "更保守，仅强调 direct drivable", "relaxed", "覆盖 direct + alternative，更符合界面显示", "主显示选 relaxed"),
        ("检测模型", "YOLOv8n", "更轻更快，但表达能力弱一些", "YOLOv8s", "Recall 与 mAP 表现更好", "主模型选 YOLOv8s"),
        ("输入尺寸", "640", "计算开销更低", "704", "对远处小目标更友好", "训练主配置保留 704"),
    ]
    y = 1.35
    for idx, (topic, a, ad, b, bd, result) in enumerate(rows):
        add_text(slide, topic, 0.72, y + 0.22, 1.2, 0.22, 13, C.blue, True)
        flow_node(slide, 2.0, y, 2.45, 0.85, a, ad, C.white, C.line, 11)
        add_text(slide, "vs", 4.62, y + 0.28, 0.35, 0.18, 12, C.muted, True, PP_ALIGN.CENTER)
        flow_node(slide, 5.1, y, 3.0, 0.85, b, bd, C.white, [C.mint, C.blue, C.orange][idx], 11)
        arrow(slide, 8.35, y + 0.27, 0.5, 0.2, C.blue)
        flow_node(slide, 9.05, y, 2.95, 0.85, "最终选择", result, RGBColor(0xEA, 0xF6, 0xFF), C.blue, 11)
        y += 1.45
    add_text(slide, "选择原则：兼顾识别效果、Recall、端侧部署可行性和答辩可解释性。", 1.15, 5.98, 10.8, 0.2, 13, C.navy, True, PP_ALIGN.CENTER)
    add_note("模型选择依据", "40秒", "这里讲我们不是随便选模型，而是做过定义、模型规模和输入尺寸对比。最后选择 relaxed、YOLOv8s 和 704 是综合取舍。")


def slide_export(slide):
    add_header(slide, 11, "模型导出与部署链路", "训练权重不是直接上手机，需要转换成 Android 可运行格式")
    stages = [
        ("训练产物", "best.pt / last.pt"),
        ("中间表示", "ONNX\n检查与转换"),
        ("端侧格式", "TFLite\nAndroid部署"),
        ("运行资产", "Android assets\n模型文件"),
        ("推理执行", "TFLite Interpreter\n执行前向推理"),
    ]
    for i, (t, b) in enumerate(stages):
        x = 0.7 + i * 2.45
        flow_node(slide, x, 1.65, 1.8, 1.25, t, b, C.white, [C.orange, C.blue, C.mint, C.blue, C.mint][i], 13)
        if i < len(stages) - 1:
            arrow(slide, x + 1.84, 2.15, 0.38, 0.2, C.blue)
    add_round(slide, 0.9, 4.25, 11.5, 1.05, RGBColor(0xEA, 0xF6, 0xFF), C.line)
    add_multiline(slide, [
        "U-Net / YOLOv8s 是模型结构；.pt / .onnx / .tflite 是不同阶段的文件表示。",
        "ONNX 更像中间桥梁，TFLite 更适合 Android 端落地。Interpreter 是运行模型的推理执行器。",
    ], 1.15, 4.52, 11.0, 0.45, 13, C.text, True)
    add_note("导出与部署链路", "35秒", "老师如果问训练模型和部署模型的区别，就按这页讲：结构、训练框架、文件格式和推理执行器是四个层次。")


def slide_android(slide):
    add_header(slide, 12, "Android 端运行链路", "从相机画面到界面提示，需要线程调度和端侧优化")
    steps = [
        ("CameraX", "采集最新帧"),
        ("预处理", "旋转/缩放/归一化"),
        ("分割推理", "TFLite\n192输入"),
        ("检测节流", "每 N 帧检测\n当前 N=6"),
        ("UI渲染", "mask + box + 提示"),
        ("提醒/留证", "TTS/提示音\n抓帧保存"),
    ]
    for i, (t, b) in enumerate(steps):
        x = 0.5 + i * 2.08
        flow_node(slide, x, 1.35, 1.6, 1.2, t, b, C.white, [C.blue, C.mint, C.orange, C.blue, C.mint, C.orange][i], 12)
        if i < len(steps) - 1:
            arrow(slide, x + 1.63, 1.83, 0.3, 0.18, C.blue)
    add_picture_fit(slide, IMG["vehicle"], 0.85, 3.35, 5.4, 2.55, True)
    add_round(slide, 6.75, 3.35, 5.0, 2.55, C.white, C.line)
    add_text(slide, "端侧优化", 7.05, 3.65, 1.5, 0.24, 15, C.blue, True)
    add_multiline(slide, [
        "优先处理最新帧，避免旧帧排队造成延迟。",
        "检测模块做节流，保证界面流畅。",
        "优先尝试 GPU Delegate，必要时退回 CPU。",
        "TTS 播报加入间隔控制，避免重复打扰。",
    ], 7.05, 4.05, 4.35, 1.2, 12, C.text, True)
    add_note("Android运行链路", "35秒", "手机端不是把模型搬过去就结束，还要处理相机帧、推理频率、UI渲染、语音提醒和抓帧留证。")


def slide_rules(slide):
    add_header(slide, 13, "规则判定层：把模型结果变成中文提示", "模型负责感知，规则层负责解释")
    inputs = [("道路中心安全性", "mask中心区域"), ("道路宽度", "横向扫描估计"), ("目标类别", "行人/车辆/坑洼等"), ("目标位置", "是否在前方关键区域")]
    for i, (t, b) in enumerate(inputs):
        flow_node(slide, 0.7, 1.2 + i * 1.05, 2.35, 0.76, t, b, C.white, C.blue if i < 2 else C.mint, 11)
        arrow(slide, 3.2, 1.45 + i * 1.05, 0.45, 0.18, C.blue)
    flow_node(slide, 4.0, 2.55, 2.25, 1.1, "优先级规则", "道路边缘 > 障碍物 > 动物 > 车辆 > 行人 > 坑洼", C.white, C.orange, 12)
    arrow(slide, 6.45, 2.95, 0.55, 0.2, C.blue)
    outputs = ["前方道路正常", "靠近道路边缘", "前方有行人", "前方有车辆，请注意保持距离", "前方有坑洼，请避让"]
    add_round(slide, 7.25, 1.25, 4.4, 3.9, RGBColor(0xEA, 0xF6, 0xFF), C.line)
    add_text(slide, "输出提示", 7.55, 1.55, 1.5, 0.25, 15, C.navy, True)
    for i, o in enumerate(outputs):
        add_chip(slide, o, 7.55, 2.0 + i * 0.52, 3.3, C.white, C.blue)
    add_text(slide, "要点：模型输出是 mask 和 box，不会直接输出中文；中文提示由业务规则综合判断生成。", 1.1, 5.85, 10.8, 0.22, 13, C.navy, True, PP_ALIGN.CENTER)
    add_note("规则判定层", "35秒", "这页把推理和判定区分开：模型给掩码和框，规则层再根据中心区域、道路宽度、目标类别和位置生成提示。")


def slide_runtime(slide):
    add_header(slide, 14, "实机运行效果展示", "测试场景实机运行效果：看得懂、能运行、可解释")
    imgs = [("正常道路", IMG["normal"], "掩码连续，提示“前方道路正常”"), ("行人提示", IMG["pedestrian"], "检测框与文字提示同步出现"), ("车辆/横屏", IMG["vehicle"], "横屏下仍能显示检测框与提示")]
    for i, (t, p, cap) in enumerate(imgs):
        x = 0.65 + i * 4.1
        add_picture_fit(slide, p, x, 1.25, 3.55, 4.55, True)
        add_text(slide, t, x + 0.12, 5.98, 3.25, 0.24, 14, C.navy, True, PP_ALIGN.CENTER)
        add_text(slide, cap, x + 0.12, 6.28, 3.25, 0.2, 9, C.muted, False, PP_ALIGN.CENTER)
    add_note("实机运行效果", "35秒", "这一页直接展示成果。说明这是测试场景实机运行效果，展示道路掩码、目标框、提示文字和横屏适配。")


def slide_metrics(slide):
    add_header(slide, 15, "结果验证：指标怎么看", "分割结果较好；检测达到原型验证水平，仍需提升 Recall")
    add_round(slide, 0.75, 1.25, 5.5, 3.05, C.white, C.line)
    add_text(slide, "道路分割指标", 1.05, 1.55, 2.2, 0.28, 17, C.navy, True)
    metric(slide, 1.1, 2.15, "mIoU", "0.8411", RGBColor(0xEA, 0xF6, 0xFF))
    metric(slide, 2.9, 2.15, "Dice", "0.9128", RGBColor(0xEA, 0xF6, 0xFF), C.mint)
    metric(slide, 4.7, 2.15, "PA", "0.9715", RGBColor(0xEA, 0xF6, 0xFF), C.orange)
    add_text(slide, "评价：道路区域覆盖较稳定，是当前成果里的亮点。", 1.1, 3.3, 4.7, 0.22, 12, C.text, True)
    add_round(slide, 6.75, 1.25, 5.5, 3.05, C.white, C.line)
    add_text(slide, "目标检测指标", 7.05, 1.55, 2.2, 0.28, 17, C.navy, True)
    metric(slide, 7.1, 2.15, "Precision", "0.5441", RGBColor(0xEA, 0xF6, 0xFF))
    metric(slide, 8.9, 2.15, "Recall", "0.3689", RGBColor(0xEA, 0xF6, 0xFF), C.red)
    metric(slide, 10.7, 2.15, "mAP@0.5", "0.3838", RGBColor(0xEA, 0xF6, 0xFF), C.orange)
    add_text(slide, "评价：已具备原型演示价值，但漏检和复杂场景鲁棒性仍需提升。", 7.1, 3.3, 4.7, 0.22, 12, C.text, True)
    add_round(slide, 1.05, 5.05, 10.95, 0.82, RGBColor(0xFF, 0xF4, 0xE8), RGBColor(0xF4, 0xC1, 0x8B))
    add_text(slide, "答辩口径：分割结果比较理想；检测结果达到原型系统可用水平，后续重点提升 Recall 和复杂场景泛化能力。", 1.28, 5.33, 10.45, 0.18, 12, C.text, True, PP_ALIGN.CENTER)
    add_note("结果验证", "40秒", "不要夸大检测指标。可以说分割较好，检测具备原型验证价值，但 Recall 仍是后续优化重点。")


def slide_outputs(slide):
    add_header(slide, 16, "阶段成果：软件原型与材料闭环", "项目形成了可演示软件，也形成了文档和软著申请支撑材料")
    add_picture_fit(slide, IMG["materials"], 0.75, 1.15, 6.25, 4.65, True)
    add_round(slide, 7.35, 1.25, 4.7, 4.35, C.white, C.line)
    add_text(slide, "阶段成果", 7.7, 1.55, 1.6, 0.28, 17, C.navy, True)
    add_multiline(slide, [
        "Android 软件原型 V1.0.0。",
        "《操作手册》用于说明功能与使用流程。",
        "《源程序鉴别材料》用于代码成果佐证。",
        "软著申请材料用于后续成果登记。",
    ], 7.7, 2.1, 4.0, 1.5, 13, C.text, True)
    add_text(slide, "成果不是停留在离线模型层面，而是完成了软件原型、实机运行和材料整理。", 7.7, 4.95, 3.95, 0.28, 11, C.blue, True)
    add_note("阶段成果", "30秒", "这页讲成果闭环：软件能跑，文档也整理出来，能支撑结题和软著材料。")


def slide_tradeoffs(slide):
    add_header(slide, 17, "技术难点与工程取舍", "真正的难点是把算法结果稳定落到手机端")
    items = [
        ("训练精度", "端侧实时性", "训练分辨率更高，手机端要考虑 FPS、内存和发热。"),
        ("训练格式", "部署格式", "best.pt 需要经过 ONNX / TFLite 转换才能落地。"),
        ("模型输出", "用户提示", "模型给 mask 和 box，规则层再生成中文提示。"),
        ("离线验证", "真机运行", "离线指标之外，还要验证 CameraX、UI、TTS 和抓帧。"),
    ]
    for i, (a, b, desc) in enumerate(items):
        x = 0.85 + (i % 2) * 6.05
        y = 1.35 + (i // 2) * 2.15
        add_round(slide, x, y, 5.25, 1.55, C.white, C.line)
        add_text(slide, a, x + 0.25, y + 0.28, 1.35, 0.22, 14, C.blue, True)
        add_text(slide, "vs", x + 1.95, y + 0.28, 0.4, 0.22, 12, C.muted, True, PP_ALIGN.CENTER)
        add_text(slide, b, x + 2.75, y + 0.28, 1.55, 0.22, 14, C.orange, True)
        add_text(slide, desc, x + 0.25, y + 0.82, 4.72, 0.32, 11, C.text)
    add_text(slide, "项目价值：打通“训练 -> 导出 -> Android端运行 -> 用户提示”的完整软件闭环。", 1.1, 6.15, 11.0, 0.25, 14, C.navy, True, PP_ALIGN.CENTER)
    add_note("技术难点与工程取舍", "30秒", "这页讲技术价值：不是单一模型指标，而是训练、导出、部署、运行、提示的完整闭环。")


def slide_close(slide):
    add_header(slide, 18, "总结与展望", "已完成软件闭环，后续继续提升复杂场景鲁棒性")
    flow_node(slide, 0.85, 1.4, 5.3, 3.55, "阶段总结", "完成 Android 道路识别与辅助提示软件原型\n完成道路分割、目标检测、提示提醒、抓帧留证\n形成操作手册、源程序鉴别材料、软著申请材料", C.white, C.blue, 18)
    flow_node(slide, 7.05, 1.4, 5.3, 3.55, "后续展望", "补充更多农村道路与复杂天气数据\n提升遮挡、弱光、小目标场景鲁棒性\n继续优化提示规则\n探索后续硬件协同可能", C.white, C.mint, 18)
    add_round(slide, 1.45, 5.75, 10.45, 0.58, C.navy, C.navy)
    add_text(slide, "谢谢各位老师，恳请批评指正。", 1.6, 5.95, 10.1, 0.16, 14, C.white, True, PP_ALIGN.CENTER)
    add_note("总结与展望", "30秒", "结尾强调当前已经完成软件闭环，后续重点是数据、鲁棒性、提示规则和硬件协同探索。")


def backup_params(slide):
    add_header(slide, 19, "答辩备份：训练参数解释")
    params = [
        ("epoch", "训练轮数；分割主配置 100，检测主配置 80。"),
        ("batch", "每次送入模型的样本数，受显存和输入尺寸影响。"),
        ("learning rate", "参数更新步长；分割主配置 0.00015。"),
        ("imgsz", "YOLO 输入尺寸；检测训练主配置 704。"),
        ("AMP", "混合精度训练，减少显存并提升效率。"),
        ("threshold", "置信度/二值化阈值，用于过滤低质量输出。"),
    ]
    for i, (p, d) in enumerate(params):
        x = 0.85 + (i % 2) * 5.9
        y = 1.25 + (i // 2) * 1.55
        flow_node(slide, x, y, 5.15, 1.1, p, d, C.white, C.blue if i % 2 == 0 else C.mint, 13)
    add_note("备份：训练参数", "备用", "老师问训练参数时再翻。按参数名、含义、本项目设置值回答。")


def backup_curves(slide):
    add_header(slide, 20, "答辩备份：检测训练曲线与混淆矩阵")
    add_picture_fit(slide, IMG["det_results"], 0.55, 1.15, 4.0, 4.9, True)
    add_picture_fit(slide, IMG["det_pr"], 4.75, 1.15, 3.85, 4.9, True)
    add_picture_fit(slide, IMG["det_conf"], 8.82, 1.15, 3.8, 4.9, True)
    add_text(slide, "用途：老师追问检测指标时，可结合 loss、PR 曲线和混淆矩阵说明模型已完成训练验证，但仍有提升空间。", 0.85, 6.25, 11.8, 0.18, 11, C.muted, False, PP_ALIGN.CENTER)
    add_note("备份：检测曲线", "备用", "这页用于技术追问。不要主动展开太久，只说明这些图来自 YOLO 训练输出。")


def backup_formats(slide):
    add_header(slide, 21, "答辩备份：模型结构、框架、格式、运行时")
    rows = [
        ("模型结构", "U-Net / YOLOv8s", "决定网络怎么计算"),
        ("训练框架", "PyTorch / Ultralytics", "负责训练流程和参数更新"),
        ("文件格式", ".pt / ONNX / TFLite", "同一模型能力在不同阶段的表示"),
        ("推理运行时", "TFLite Interpreter / ONNX Runtime", "加载文件并执行前向推理"),
    ]
    for i, (a, b, c) in enumerate(rows):
        y = 1.25 + i * 1.15
        add_text(slide, a, 1.05, y + 0.18, 1.4, 0.22, 13, C.blue, True)
        flow_node(slide, 2.65, y, 3.15, 0.75, b, c, C.white, C.mint if i % 2 else C.blue, 11)
        if i < len(rows) - 1:
            arrow(slide, 4.05, y + 0.8, 0.22, 0.28, C.blue, "down")
    add_round(slide, 6.75, 1.5, 4.95, 3.6, RGBColor(0xEA, 0xF6, 0xFF), C.line)
    add_text(slide, "一句话背诵", 7.05, 1.85, 1.6, 0.22, 15, C.navy, True)
    add_text(slide, "U-Net 和 YOLOv8s 是模型结构；PyTorch 和 Ultralytics 是训练工具；ONNX 和 TFLite 是部署格式；Interpreter 是执行推理的运行时。", 7.05, 2.35, 4.35, 1.3, 14, C.text)
    add_note("备份：格式关系", "备用", "这页用于回答 ONNX、TFLite、pt 文件和模型结构之间的关系。")


def backup_tflite(slide):
    add_header(slide, 22, "答辩备份：为什么 Android 端优先选 TFLite")
    flow_node(slide, 0.95, 1.55, 3.1, 2.45, "TFLite优势", "Android生态成熟\n支持 GPU Delegate\n端侧集成成本较低", C.white, C.mint, 16)
    flow_node(slide, 5.1, 1.55, 3.1, 2.45, "ONNX定位", "中间表示\n便于转换和验证\n可作为备用方案", C.white, C.blue, 16)
    flow_node(slide, 9.25, 1.55, 3.1, 2.45, "本项目落地", "Android端主要加载 TFLite\nONNX用于中转/对照", C.white, C.orange, 16)
    add_text(slide, "答法：TFLite 并不是“更准”，而是更适合 Android 端部署；精度主要取决于模型训练、转换一致性和是否量化。", 1.2, 5.25, 10.9, 0.28, 13, C.navy, True, PP_ALIGN.CENTER)
    add_note("备份：TFLite选择", "备用", "老师问为什么不用 ONNX 或 pt 时，用这页说明 TFLite 是部署格式选择，不是模型结构选择。")


def build_notes() -> str:
    lines = [
        "# 阡陌智行结题答辩PPT v3 逐页讲稿",
        "",
        "说明：第1-18页为主讲内容，第19-22页为答辩备份页。主讲建议控制在 6-8 分钟。",
        "",
    ]
    for i, n in enumerate(NOTES, 1):
        lines.extend([f"## 第{i}页：{n.title}", "", f"建议时长：{n.seconds}", "", n.script, ""])
    return "\n".join(lines)


def build_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    blank = prs.slide_layouts[6]
    renderers = [
        slide_cover, slide_background, slide_scope, slide_system, slide_seg_flow,
        slide_seg_evidence, slide_detect_flow, slide_detect_evidence, slide_training,
        slide_model_choice, slide_export, slide_android, slide_rules, slide_runtime,
        slide_metrics, slide_outputs, slide_tradeoffs, slide_close,
        backup_params, backup_curves, backup_formats, backup_tflite,
    ]
    for render in renderers:
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = C.pale
        render(slide)
    return prs


def main() -> None:
    missing = [str(p) for p in IMG.values() if not p.exists()]
    if missing:
        print("Missing assets:")
        for p in missing:
            print(p)
    OUT.mkdir(parents=True, exist_ok=True)
    prs = build_deck()
    prs.save(str(PPTX))
    MD.write_text(build_notes(), encoding="utf-8")
    print(f"pptx: {PPTX}")
    print(f"notes: {MD}")


if __name__ == "__main__":
    main()
