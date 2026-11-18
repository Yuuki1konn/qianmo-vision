from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "doc"
ASSET_DIR = OUTPUT_DIR / "_assets"

PPT_PATH = OUTPUT_DIR / "阡陌智行结题答辩PPT_草稿.pptx"
MD_PATH = OUTPUT_DIR / "阡陌智行结题答辩PPT_逐页文案.md"

ASSETS = {
    "cover": ASSET_DIR / "ui_normal.jpg",
    "edge": ASSET_DIR / "ui_edge.jpg",
    "normal": ASSET_DIR / "ui_normal.jpg",
    "pedestrian": ASSET_DIR / "ui_pedestrian.jpg",
    "vehicle_landscape": ASSET_DIR / "ui_vehicle_landscape.png",
    "rotation_landscape": ASSET_DIR / "ui_rotation_landscape.png",
    "flow": ASSET_DIR / "主流程图.png",
}


class Theme:
    dark = RGBColor(0x44, 0x54, 0x6A)
    blue = RGBColor(0x5B, 0x9B, 0xD5)
    blue_strong = RGBColor(0x44, 0x72, 0xC4)
    light = RGBColor(0xF5, 0xFA, 0xFF)
    light_blue = RGBColor(0xE8, 0xF3, 0xFF)
    border = RGBColor(0xC7, 0xDB, 0xF5)
    text = RGBColor(0x1F, 0x2D, 0x3D)
    muted = RGBColor(0x5C, 0x6B, 0x7A)
    green = RGBColor(0x2F, 0xB7, 0x7A)
    orange = RGBColor(0xED, 0x7D, 0x31)
    white = RGBColor(0xFF, 0xFF, 0xFF)
    red = RGBColor(0xD1, 0x49, 0x5B)


FONT = "Microsoft YaHei"


@dataclass
class SlideSpec:
    number: int
    title: str
    bullets: list[str]
    images: list[str]
    layout_tip: str
    talk_time: str


SLIDES: list[SlideSpec] = [
    SlideSpec(
        number=1,
        title="封面",
        bullets=[
            "项目名称：“阡陌智行”——农村老年电动车出行助手",
            "副标题：大学生创新训练计划项目结题答辩",
            "当前软件成果：阡陌智行农村道路识别系统（Android版）",
            "项目负责人：卜裕鑫；项目成员：卞明轩、李昌隆、窦书航；指导教师：刘岩",
        ],
        images=["ui_normal.jpg"],
        layout_tip="左侧放项目标题与摘要，右侧放手机界面图，底部用蓝色信息条统一学校、成员和指导教师信息。",
        talk_time="20-30秒",
    ),
    SlideSpec(
        number=2,
        title="研究背景与问题提出",
        bullets=[
            "农村道路多为非结构化场景，常见土路、碎石路、坑洼路、窄路等复杂情况。",
            "缺少清晰车道线与统一标识，传统规则式识别方法稳定性不足。",
            "对二轮电动车用户而言，低成本、可实时运行的移动端辅助识别具有现实需求。",
            "因此项目聚焦于“移动端道路识别 + 风险提示”的可落地软件方案。",
        ],
        images=["ui_edge.jpg"],
        layout_tip="左侧用3张背景卡片讲问题，右侧放道路边缘或复杂场景界面图，突出“为什么做”。",
        talk_time="35-40秒",
    ),
    SlideSpec(
        number=3,
        title="研究目标与本阶段完成范围",
        bullets=[
            "项目目标：面向农村道路场景构建移动端道路识别与辅助提示系统。",
            "原始设想包含识别、语音提醒及后续硬件联动探索。",
            "当前已完成：道路分割、目标检测、状态提示、语音/提示音提醒、Android端部署、调试抓帧留证。",
            "本次结题以软件成果验收为主，未将紧急制动或整车控制写为已完成成果。",
        ],
        images=[],
        layout_tip="采用左右对照卡片：左边写原始设想，右边写当前已完成；底部单独强调“硬件联动未纳入已完成成果”。",
        talk_time="40秒",
    ),
    SlideSpec(
        number=4,
        title="系统总体方案",
        bullets=[
            "系统主链路为：采集 -> 预处理 -> 分割 -> 检测 -> 状态判定 -> 结果渲染 -> 抓帧留证。",
            "Android端使用 CameraX 完成相机采集与预览管理。",
            "分割与检测模型以 TFLite 形式部署到移动端，兼顾速度与可部署性。",
            "输出结果包括道路掩码、目标框、状态文字、语音/提示音与抓帧结果。",
        ],
        images=["主流程图.png"],
        layout_tip="右侧放主流程图，左侧用短句解释每个阶段的职责；底部用蓝色标签列出 Android、CameraX、TFLite 等关键词。",
        talk_time="35-40秒",
    ),
    SlideSpec(
        number=5,
        title="核心功能设计",
        bullets=[
            "道路可行驶区域分割：以半透明掩码直观显示可通行空间。",
            "风险目标检测：识别两轮车、三轮车、行人、动物、障碍物、坑洼等目标。",
            "状态提示与语音提醒：输出“前方道路正常”“前方有行人”等关键信息。",
            "横竖屏适配与调试抓帧：兼顾演示体验与结果留证。",
        ],
        images=["ui_pedestrian.jpg"],
        layout_tip="左侧做4张功能卡片，右侧放一张实机界面图，保持“图少字精”的技术说明页风格。",
        talk_time="35-40秒",
    ),
    SlideSpec(
        number=6,
        title="训练-导出-部署链路",
        bullets=[
            "训练阶段使用 PyTorch / Ultralytics 完成分割与检测模型训练。",
            "训练产物以 .pt 权重形式保存，例如 best.pt、last.pt。",
            "导出阶段先转为 ONNX，再进一步转换为 TFLite，并做一致性验证。",
            "Android 端最终加载的是部署模型，不再包含训练过程信息。",
        ],
        images=[],
        layout_tip="用 训练 / 导出 / 部署 三段链路讲清楚 best.pt、ONNX、TFLite 的关系，底部单独强调“模型结构不等于部署格式”。",
        talk_time="40-45秒",
    ),
    SlideSpec(
        number=7,
        title="模型选择依据",
        bullets=[
            "分割阶段对比 strict 与 relaxed，最终主显示选 relaxed。",
            "检测阶段对比 YOLOv8n 与 YOLOv8s，最终主模型选 YOLOv8s。",
            "输入尺寸对比 640 与 704，最终在检测训练阶段保留 704。",
            "选择原则不是只看单一指标，而是兼顾 Recall、可解释性和端侧落地。",
        ],
        images=[],
        layout_tip="把“为什么选这个”讲成对比与取舍，而不是只堆结论；建议分成 strict/relaxed、n/s、640/704 三块。",
        talk_time="45-50秒",
    ),
    SlideSpec(
        number=8,
        title="实机运行效果展示",
        bullets=[
            "正常道路场景：可行驶区域掩码连续、界面提示清晰。",
            "行人风险场景：目标框与底部“前方有行人”提示同步出现。",
            "车辆/横屏场景：界面可在横屏下保持信息完整显示。",
            "这一页重点展示“看得懂、能说明白、确实能运行”的真实效果。",
        ],
        images=["ui_normal.jpg", "ui_pedestrian.jpg", "ui_vehicle_landscape.png"],
        layout_tip="放 3 张成果图，文字只保留每张图的一句说明；这页要成为最直观的成果展示页。",
        talk_time="40-45秒",
    ),
    SlideSpec(
        number=9,
        title="结果验证与阶段成果",
        bullets=[
            "分割结果：mIoU 0.8411、Dice 0.9128、PA 0.9715。",
            "检测结果：Precision 0.5441、Recall 0.3689、mAP@0.5 0.3838、mAP@0.5:0.95 0.2168。",
            "多组真机截图中已出现约 16-22 FPS 的运行效果，具备移动端演示基础。",
            "阶段成果包括 Android软件原型、操作手册、源程序鉴别材料、软著申请材料。",
        ],
        images=[],
        layout_tip="左边做分割/检测两张指标卡，右边加“指标怎么看”和“阶段成果”两块，让你能顺手解释名词。",
        talk_time="35-40秒",
    ),
    SlideSpec(
        number=10,
        title="技术难点与工程取舍",
        bullets=[
            "训练效果与端侧实时性之间需要平衡，训练分辨率与部署分辨率并不完全相同。",
            "模型从 PyTorch 到 ONNX/TFLite 不是直接复制，而是要处理格式兼容与一致性验证。",
            "模型输出的是掩码和框，最终提示语还需要业务规则层做二次判定。",
            "项目重点不是单纯训出模型，而是打通“训练 -> 导出 -> 端侧软件”的完整闭环。",
        ],
        images=[],
        layout_tip="用 4 张卡片讲清楚真正的技术难点，底部再用一句话总结项目价值，比“创新口号页”更像答辩。",
        talk_time="30-35秒",
    ),
    SlideSpec(
        number=11,
        title="总结与展望",
        bullets=[
            "当前阶段已完成一套可运行的 Android 道路识别与辅助提示软件原型。",
            "项目已形成较完整的软件成果链路，能够支撑结题展示与软著申报材料整理。",
            "当前边界在于：硬件联动尚未实现，复杂场景鲁棒性仍有提升空间。",
            "后续将继续补充农村场景数据、优化提示规则，并探索后续硬件协同可能。",
        ],
        images=[],
        layout_tip="左侧写阶段总结，右侧写后续展望，底部保留“谢谢老师，恳请批评指正”的答辩收束语。",
        talk_time="30-35秒",
    ),
    SlideSpec(
        number=12,
        title="答辩备份：训练参数解释",
        bullets=[
            "epoch、batch、learning rate、imgsz、amp 等参数是老师最容易追问的内容。",
            "这页不主动讲，老师问到训练细节时再翻。",
        ],
        images=[],
        layout_tip="做成参数解释卡片页，突出“参数名 + 含义 + 本项目设置值”。",
        talk_time="追问备用",
    ),
    SlideSpec(
        number=13,
        title="答辩备份：训练模型与部署模型关系",
        bullets=[
            "U-Net / YOLOv8 是模型结构；.pt / .onnx / .tflite 是不同阶段的文件表示。",
            "这页用于回答“训练模型”和“导出模型”到底是不是一回事。",
        ],
        images=[],
        layout_tip="把 数据集 -> 训练框架 -> best.pt -> ONNX -> TFLite -> Android 明确画成一条链。",
        talk_time="追问备用",
    ),
    SlideSpec(
        number=14,
        title="答辩备份：为什么 Android 端优先选 TFLite",
        bullets=[
            "TFLite 更适合 Android 原生部署，集成成本更低。",
            "ONNX 仍保留作为中间格式、对照资产和备用方案。",
        ],
        images=[],
        layout_tip="做成 TFLite / ONNX 对比页，直接回答“为什么手机端不用训练时的原始模型文件”。",
        talk_time="追问备用",
    ),
]


def set_run_style(run, size: int, color: RGBColor, bold: bool = False) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def fill_shape(shape, color: RGBColor, transparency: float = 0.0) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.fill.transparency = transparency
    shape.line.color.rgb = color
    shape.line.transparency = 1.0


def style_box(shape, fill: RGBColor, line: RGBColor | None = None, width: float = 1.0) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line or fill
    shape.line.width = Pt(width)


def add_textbox(slide, left, top, width, height, text="", font_size=18, color=Theme.text, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.clear()
    frame.margin_left = Pt(8)
    frame.margin_right = Pt(8)
    frame.margin_top = Pt(4)
    frame.margin_bottom = Pt(4)
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    p = frame.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_run_style(run, font_size, color, bold)
    return box


def add_tag(slide, text: str, x: float, y: float, w: float, h: float, color: RGBColor = Theme.blue_strong) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    fill_shape(shape, color)
    tf = shape.text_frame
    tf.clear()
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    set_run_style(run, 12, Theme.white, True)


def add_slide_header(slide, number: int, title: str) -> None:
    top_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.16))
    fill_shape(top_line, Theme.blue)
    add_tag(slide, f"{number:02d}", 0.55, 0.35, 0.6, 0.35, Theme.dark)
    add_textbox(slide, Inches(1.25), Inches(0.28), Inches(8.8), Inches(0.55), title, font_size=24, color=Theme.dark, bold=True)
    sub = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.58), Inches(0.95), Inches(0.95), Inches(0.06))
    fill_shape(sub, Theme.blue_strong)


def add_footer(slide) -> None:
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.58), Inches(7.0), Inches(12.15), Inches(0.02))
    fill_shape(line, Theme.border)
    add_textbox(
        slide,
        Inches(0.6),
        Inches(7.03),
        Inches(8.5),
        Inches(0.22),
        "阡陌智行 | 大学生创新训练计划项目结题答辩",
        font_size=9,
        color=Theme.muted,
    )


def add_card(slide, x: float, y: float, w: float, h: float, title: str, body: Iterable[str], title_color: RGBColor = Theme.dark) -> None:
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    style_box(card, Theme.white, Theme.border, width=1.2)
    title_box = add_textbox(slide, Inches(x + 0.12), Inches(y + 0.08), Inches(w - 0.24), Inches(0.35), title, font_size=16, color=title_color, bold=True)
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + 0.12), Inches(y + 0.48), Inches(0.52), Inches(0.05))
    fill_shape(accent, Theme.blue)
    text_box = slide.shapes.add_textbox(Inches(x + 0.12), Inches(y + 0.58), Inches(w - 0.24), Inches(h - 0.7))
    tf = text_box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Pt(4)
    tf.margin_right = Pt(4)
    for idx, item in enumerate(body):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.bullet = True
        p.space_after = Pt(4)
        p.alignment = PP_ALIGN.LEFT
        if p.runs:
            run = p.runs[0]
        else:
            run = p.add_run()
            run.text = item
        set_run_style(run, 12, Theme.text, False)
    return title_box


def add_bullets(slide, x: float, y: float, w: float, h: float, bullets: Iterable[str], font_size: int = 15, color: RGBColor = Theme.text) -> None:
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Pt(6)
    tf.margin_right = Pt(6)
    for idx, item in enumerate(bullets):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = item
        p.bullet = True
        p.space_after = Pt(7)
        p.alignment = PP_ALIGN.LEFT
        if p.runs:
            run = p.runs[0]
        else:
            run = p.add_run()
            run.text = item
        set_run_style(run, font_size, color)


def add_image_fill(slide, path: Path, x: float, y: float, w: float, h: float, border: bool = False, rounded: bool = True) -> None:
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.background()
    if border:
        shape.line.color.rgb = Theme.border
        shape.line.width = Pt(1.25)
    else:
        shape.line.transparency = 1.0


def add_metric_card(slide, x: float, y: float, w: float, h: float, title: str, metrics: list[tuple[str, str]], fill: RGBColor) -> None:
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    style_box(card, fill, Theme.border, width=1.0)
    add_textbox(slide, Inches(x + 0.12), Inches(y + 0.12), Inches(w - 0.24), Inches(0.35), title, font_size=16, color=Theme.dark, bold=True)
    card_top = y + 0.62
    for idx, (name, value) in enumerate(metrics):
        col = idx % 2
        row = idx // 2
        mx = x + 0.15 + col * ((w - 0.3) / 2)
        my = card_top + row * 0.62
        add_textbox(slide, Inches(mx), Inches(my), Inches((w - 0.45) / 2), Inches(0.24), name, font_size=10, color=Theme.muted)
        add_textbox(slide, Inches(mx), Inches(my + 0.18), Inches((w - 0.45) / 2), Inches(0.36), value, font_size=18, color=Theme.blue_strong, bold=True)


def render_cover(slide) -> None:
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.18))
    fill_shape(bar, Theme.blue)
    side = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.85), Inches(0.6), Inches(3.95), Inches(5.9))
    style_box(side, Theme.white, Theme.border, width=1.3)
    add_tag(slide, "大学生创新训练计划项目结题答辩", 0.85, 0.78, 2.35, 0.42, Theme.blue_strong)
    add_textbox(slide, Inches(0.88), Inches(1.38), Inches(7.0), Inches(0.62), "“阡陌智行”", font_size=28, color=Theme.dark, bold=True)
    add_textbox(slide, Inches(0.88), Inches(1.93), Inches(7.2), Inches(0.8), "农村道路识别与辅助提示项目", font_size=24, color=Theme.dark, bold=True)
    add_textbox(
        slide,
        Inches(0.9),
        Inches(2.55),
        Inches(7.1),
        Inches(0.5),
        "当前软件成果：阡陌智行农村道路识别系统（Android版）",
        font_size=14,
        color=Theme.blue_strong,
    )
    add_textbox(
        slide,
        Inches(0.9),
        Inches(3.15),
        Inches(6.9),
        Inches(1.4),
        "面向农村非结构化道路场景，围绕道路分割、风险目标检测、状态提示与端侧部署形成可运行软件原型。",
        font_size=18,
        color=Theme.text,
    )
    add_textbox(
        slide,
        Inches(0.92),
        Inches(4.85),
        Inches(6.9),
        Inches(0.35),
        "关键词：农村道路识别 / Android端部署 / 实时提示 / 软著材料整理",
        font_size=12,
        color=Theme.muted,
        bold=True,
    )
    add_image_fill(slide, ASSETS["cover"], 9.08, 0.82, 3.5, 5.46, border=True)
    footer = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.65), Inches(6.28), Inches(12.0), Inches(0.74))
    footer.fill.solid()
    footer.fill.fore_color.rgb = Theme.blue_strong
    footer.fill.transparency = 0.02
    footer.line.transparency = 1.0
    add_textbox(slide, Inches(0.95), Inches(6.4), Inches(3.7), Inches(0.2), "郑州轻工业大学 计算机与人工智能学院", font_size=10, color=Theme.white)
    add_textbox(slide, Inches(0.95), Inches(6.63), Inches(3.5), Inches(0.2), "项目负责人：卜裕鑫", font_size=11, color=Theme.white, bold=True)
    add_textbox(slide, Inches(4.2), Inches(6.4), Inches(4.0), Inches(0.2), "项目成员：卞明轩、李昌隆、窦书航", font_size=10, color=Theme.white)
    add_textbox(slide, Inches(4.2), Inches(6.63), Inches(3.6), Inches(0.2), "指导教师：刘岩", font_size=11, color=Theme.white, bold=True)


def render_background_problem(slide) -> None:
    add_slide_header(slide, 2, "研究背景与问题提出")
    add_textbox(slide, Inches(0.72), Inches(1.12), Inches(5.5), Inches(0.34), "为什么这个问题值得做？", font_size=13, color=Theme.muted, bold=True)
    add_card(slide, 0.7, 1.55, 5.15, 1.18, "1. 场景复杂", ["土路、碎石路、坑洼路、窄路等情况频繁出现。"])
    add_card(slide, 0.7, 2.9, 5.15, 1.18, "2. 规则法受限", ["缺少清晰标线与统一路面特征，传统规则式方法适应性不足。"])
    add_card(slide, 0.7, 4.25, 5.15, 1.18, "3. 移动端有需求", ["二轮电动车场景需要低成本、实时运行、易演示的辅助识别方案。"])
    add_image_fill(slide, ASSETS["edge"], 6.25, 1.25, 6.3, 5.55, border=True)
    add_tag(slide, "农村非结构化道路", 9.5, 1.42, 2.0, 0.34, Theme.blue)
    add_footer(slide)


def render_scope(slide) -> None:
    add_slide_header(slide, 3, "研究目标与本阶段完成范围")
    add_card(slide, 0.72, 1.35, 5.85, 4.85, "项目原始设想", [
        "围绕农村二轮车出行辅助场景开展识别、提醒与系统集成研究。",
        "希望逐步探索道路识别、语音提示以及后续硬件联动的可能性。",
        "更偏“完整系统设想”，而不仅是单一模型验证。"])
    add_card(slide, 6.75, 1.35, 5.85, 4.85, "当前阶段已完成", [
        "道路可行驶区域分割",
        "风险目标检测",
        "状态文字提示",
        "语音/提示音提醒",
        "Android端部署与调试抓帧留证",
    ], title_color=Theme.blue_strong)
    callout = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(6.35), Inches(11.7), Inches(0.48))
    style_box(callout, Theme.light_blue, Theme.red, width=1.2)
    add_textbox(
        slide,
        Inches(0.98),
        Inches(6.42),
        Inches(11.3),
        Inches(0.2),
        "本次结题以软件成果验收为主，紧急制动 / 硬件联动不写为已完成成果。",
        font_size=12,
        color=Theme.red,
        bold=True,
        align=PP_ALIGN.CENTER,
    )
    add_footer(slide)


def render_system(slide) -> None:
    add_slide_header(slide, 4, "系统总体方案")
    add_textbox(slide, Inches(0.72), Inches(1.18), Inches(4.8), Inches(0.42), "主链路：采集 -> 预处理 -> 推理 -> 判定 -> 渲染 -> 留证", font_size=14, color=Theme.muted, bold=True)
    steps = [
        "采集：CameraX 获取实时相机画面并管理预览。",
        "预处理：完成图像转换与模型输入准备。",
        "分割：输出可行驶区域掩码。",
        "检测：识别行人、车辆、动物、坑洼等目标。",
        "判定：综合掩码与目标位置生成底部提示。",
        "留证：支持抓取 frame、mask、overlay 和元数据。",
    ]
    for idx, text in enumerate(steps):
        cy = 1.75 + idx * 0.72
        circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.76), Inches(cy), Inches(0.36), Inches(0.36))
        fill_shape(circle, Theme.blue_strong)
        add_textbox(slide, Inches(0.84), Inches(cy + 0.02), Inches(0.2), Inches(0.2), str(idx + 1), font_size=11, color=Theme.white, bold=True, align=PP_ALIGN.CENTER)
        add_textbox(slide, Inches(1.18), Inches(cy - 0.02), Inches(4.15), Inches(0.45), text, font_size=13, color=Theme.text)
    add_image_fill(slide, ASSETS["flow"], 5.75, 1.3, 6.55, 4.95, border=True)
    tech = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.85), Inches(6.35), Inches(6.3), Inches(0.45))
    style_box(tech, Theme.light_blue, Theme.border)
    add_textbox(slide, Inches(6.0), Inches(6.43), Inches(6.0), Inches(0.18), "Android  •  CameraX  •  TensorFlow Lite  •  GPU/TFLite Runtime", font_size=12, color=Theme.blue_strong, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide)


def render_functions(slide) -> None:
    add_slide_header(slide, 5, "核心功能设计")
    add_card(slide, 0.72, 1.45, 3.35, 1.65, "道路分割", [
        "以半透明掩码显示可通行区域。",
        "直观区分道路与路侧环境。"])
    add_card(slide, 4.22, 1.45, 3.35, 1.65, "目标检测", [
        "识别两轮车、三轮车、行人、动物、障碍物、坑洼等目标。",
        "显示类别与置信度。"])
    add_card(slide, 0.72, 3.35, 3.35, 1.65, "状态提示", [
        "输出“前方道路正常”“前方有行人”等底部提示。",
        "兼顾文字与语音/提示音反馈。"])
    add_card(slide, 4.22, 3.35, 3.35, 1.65, "适配与留证", [
        "支持横竖屏显示。",
        "支持调试抓帧与元数据导出。"])
    add_image_fill(slide, ASSETS["pedestrian"], 8.05, 1.4, 4.0, 5.45, border=True)
    add_tag(slide, "实时识别 / 实时提示 / 可留证", 8.28, 1.6, 2.55, 0.34, Theme.blue_strong)
    add_footer(slide)


def render_pipeline(slide) -> None:
    add_slide_header(slide, 6, "训练-导出-部署链路")
    add_textbox(
        slide,
        Inches(0.72),
        Inches(1.08),
        Inches(7.8),
        Inches(0.28),
        "老师最容易问的其实是：训练模型、导出模型和手机端模型到底是什么关系？",
        font_size=12,
        color=Theme.muted,
    )
    add_card(slide, 0.72, 1.55, 3.55, 3.6, "训练阶段", [
        "分割：PyTorch 训练 U-Net。",
        "检测：Ultralytics 训练 YOLOv8。",
        "训练产物以 .pt 保存，例如 best.pt / last.pt。",
        "此阶段包含参数更新、epoch、优化器等训练信息。"])
    add_card(slide, 4.45, 1.55, 3.55, 3.6, "导出阶段", [
        "从 best.pt 导出为 ONNX。",
        "再由 ONNX 转为 TFLite。",
        "分割导出后做 ONNX 与 TFLite 一致性验证。",
        "这一阶段解决的是格式兼容与部署准备问题。"])
    add_card(slide, 8.18, 1.55, 4.1, 3.6, "部署阶段", [
        "Android 端通过 CameraX 采集画面。",
        "最终加载的是 TFLite / 推理引擎，不再训练。",
        "输出道路掩码、目标框、底部状态和语音提醒。",
        "关注的是 FPS、时延、稳定性和可演示性。"])
    for x in (4.0, 7.73):
        add_textbox(slide, Inches(x), Inches(3.0), Inches(0.4), Inches(0.2), ">", font_size=28, color=Theme.blue_strong, bold=True, align=PP_ALIGN.CENTER)
    tip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(5.5), Inches(11.55), Inches(0.88))
    style_box(tip, Theme.light_blue, Theme.border, width=1.0)
    add_textbox(slide, Inches(1.0), Inches(5.72), Inches(11.2), Inches(0.22), "模型结构 != 文件格式", font_size=16, color=Theme.dark, bold=True, align=PP_ALIGN.CENTER)
    add_textbox(
        slide,
        Inches(1.0),
        Inches(6.0),
        Inches(11.2),
        Inches(0.2),
        "U-Net / YOLOv8 是模型结构；.pt / .onnx / .tflite 是不同阶段的文件表示；TFLite Interpreter / ONNX Runtime 是推理引擎。",
        font_size=11,
        color=Theme.blue_strong,
        bold=True,
        align=PP_ALIGN.CENTER,
    )
    add_footer(slide)


def render_model_choices(slide) -> None:
    add_slide_header(slide, 7, "模型选择依据")
    add_textbox(slide, Inches(0.72), Inches(1.08), Inches(6.8), Inches(0.25), "这页不只说“用了什么”，而要说“为什么最后选它”。", font_size=12, color=Theme.muted)
    add_card(slide, 0.72, 1.45, 3.9, 2.2, "分割：strict vs relaxed", [
        "strict：BDD 仅使用 direct drivable，更保守。",
        "relaxed：BDD 使用 direct + alternative drivable，更符合道路直觉。",
        "最终主显示选 relaxed；strict 保留作安全边界参考。"])
    stat_a = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), Inches(3.05), Inches(3.4), Inches(0.38))
    style_box(stat_a, Theme.light_blue, Theme.border, width=0.8)
    add_textbox(slide, Inches(1.05), Inches(3.12), Inches(3.2), Inches(0.18), "strict mIoU 0.7862  vs  relaxed mIoU 0.8411", font_size=11, color=Theme.blue_strong, bold=True, align=PP_ALIGN.CENTER)
    add_card(slide, 4.75, 1.45, 3.75, 2.2, "检测：YOLOv8n vs YOLOv8s", [
        "YOLOv8s 在 Recall 与 mAP 上优于 YOLOv8n。",
        "更适合作为“安全优先”的主模型。",
        "最终检测选型保留到 YOLOv8s。"])
    stat_b = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.98), Inches(3.05), Inches(3.28), Inches(0.38))
    style_box(stat_b, Theme.light_blue, Theme.border, width=0.8)
    add_textbox(slide, Inches(5.08), Inches(3.12), Inches(3.08), Inches(0.18), "YOLOv8n AP50 0.2245  vs  YOLOv8s AP50 0.2578", font_size=10, color=Theme.blue_strong, bold=True, align=PP_ALIGN.CENTER)
    add_card(slide, 8.65, 1.45, 3.55, 2.2, "输入尺寸：640 vs 704", [
        "更高分辨率对远处和小目标更有帮助。",
        "704 在 Recall 和 mAP 上优于 640。",
        "因此检测训练阶段最终保留 704。"])
    stat_c = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.88), Inches(3.05), Inches(3.08), Inches(0.38))
    style_box(stat_c, Theme.light_blue, Theme.border, width=0.8)
    add_textbox(slide, Inches(8.98), Inches(3.12), Inches(2.88), Inches(0.18), "704 相比 640，Recall +0.0109，AP50 +0.0137", font_size=10, color=Theme.blue_strong, bold=True, align=PP_ALIGN.CENTER)
    summary = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(4.05), Inches(11.45), Inches(1.72))
    style_box(summary, Theme.white, Theme.border, width=1.0)
    add_textbox(slide, Inches(1.05), Inches(4.26), Inches(11.0), Inches(0.25), "最终保留的主路线", font_size=16, color=Theme.dark, bold=True, align=PP_ALIGN.CENTER)
    add_bullets(slide, 1.08, 4.65, 10.9, 0.9, [
        "分割：BDD100K + Cityscapes + IDD，主显示模型选择 relaxed。",
        "检测：先通过 n/s 与 640/704 做选型，再在 YOLOv8s 主线上补充 pothole 和 IDD_Detection 样本。",
        "核心原则不是只看单一指标，而是兼顾 Recall、可解释性和移动端落地。"],
        font_size=12,
    )
    add_footer(slide)


def render_results_visual(slide) -> None:
    add_slide_header(slide, 8, "实机运行效果展示")
    add_textbox(slide, Inches(0.72), Inches(1.1), Inches(7.0), Inches(0.25), "这一页重点展示真实运行效果：看得懂、能运行、可解释。", font_size=12, color=Theme.muted)
    cards = [
        (ASSETS["normal"], 0.72, 1.55, 2.65, 4.7, "正常道路场景", "绿色掩码连续覆盖可通行区域，底部提示“前方道路正常”。"),
        (ASSETS["pedestrian"], 3.62, 1.55, 2.65, 4.7, "行人风险场景", "检测多人目标，并触发“前方有行人”提示。"),
        (ASSETS["vehicle_landscape"], 6.52, 1.55, 5.1, 2.45, "车辆/横屏场景", "横屏状态下仍可显示检测框、提示语与功能按钮。"),
    ]
    for path, x, y, w, h, title, desc in cards:
        add_image_fill(slide, path, x, y, w, h, border=True)
        caption = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y + h + 0.08), Inches(w), Inches(0.6))
        style_box(caption, Theme.white, Theme.border, width=0.9)
        add_textbox(slide, Inches(x + 0.05), Inches(y + h + 0.12), Inches(w - 0.1), Inches(0.18), title, font_size=12, color=Theme.dark, bold=True, align=PP_ALIGN.CENTER)
        add_textbox(slide, Inches(x + 0.05), Inches(y + h + 0.29), Inches(w - 0.1), Inches(0.24), desc, font_size=9, color=Theme.muted, align=PP_ALIGN.CENTER)
    add_footer(slide)


def render_metrics(slide) -> None:
    add_slide_header(slide, 9, "结果验证与阶段成果")
    add_metric_card(
        slide,
        0.72,
        1.45,
        4.55,
        2.2,
        "分割结果",
        [("mIoU", "0.8411"), ("Dice", "0.9128"), ("PA", "0.9715")],
        Theme.light_blue,
    )
    add_metric_card(
        slide,
        0.72,
        3.95,
        4.55,
        2.35,
        "检测结果",
        [("Precision", "0.5441"), ("Recall", "0.3689"), ("mAP@0.5", "0.3838"), ("mAP@0.5:0.95", "0.2168")],
        Theme.light,
    )
    add_card(slide, 5.55, 1.45, 6.5, 1.95, "这些指标怎么看", [
        "mIoU / Dice：看分割区域和真实道路贴合得好不好。",
        "Precision / Recall：看检测框是否够准、够全。",
        "mAP@0.5 / mAP@0.5:0.95：看整体检测质量与定位稳定性。"], title_color=Theme.blue_strong)
    add_card(slide, 5.55, 3.7, 6.5, 2.15, "阶段成果", [
        "完成 Android 软件原型 V1.0.0。",
        "形成《操作手册》与《源程序鉴别材料》。",
        "整理完成软著申请相关材料。",
        "多组真机截图显示运行帧率约 16-22 FPS。"], title_color=Theme.blue_strong)
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.72), Inches(6.0), Inches(6.1), Inches(0.48))
    style_box(badge, Theme.blue_strong, Theme.blue_strong)
    add_textbox(slide, Inches(5.82), Inches(6.09), Inches(5.9), Inches(0.18), "当前成果已具备项目演示、验收和文档申报基础", font_size=12, color=Theme.white, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide)


def render_tradeoffs(slide) -> None:
    add_slide_header(slide, 10, "技术难点与工程取舍")
    add_card(slide, 0.72, 1.45, 2.8, 2.15, "训练效果 vs 端侧实时性", [
        "训练更关注学得好，部署更关注跑得动。",
        "因此训练分辨率和部署分辨率不完全相同。"])
    add_card(slide, 3.72, 1.45, 2.8, 2.15, "格式转换 vs 一致性", [
        "best.pt 不能直接上手机。",
        "需要导出 ONNX / TFLite，并做一致性验证。"])
    add_card(slide, 6.72, 1.45, 2.8, 2.15, "感知结果 vs 用户理解", [
        "模型只输出掩码和检测框。",
        "最终提示语需要业务规则层二次判定。"])
    add_card(slide, 9.72, 1.45, 2.8, 2.15, "检测频率 vs 稳定性", [
        "检测不是每帧都跑。",
        "当前通过节流和最新帧策略保证流畅性。"])
    value_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(4.05), Inches(11.8), Inches(1.75))
    style_box(value_box, Theme.light_blue, Theme.border, width=1.0)
    add_textbox(slide, Inches(1.02), Inches(4.28), Inches(11.4), Inches(0.26), "这套项目真正完成的不是“单个模型”，而是一个工程闭环", font_size=17, color=Theme.dark, bold=True, align=PP_ALIGN.CENTER)
    add_bullets(slide, 1.0, 4.72, 11.4, 0.82, [
        "从训练、导出、一致性验证，到 Android 端接入、界面展示和提示规则，形成了完整的软件闭环。",
        "这也是本项目在结题答辩里最值得强调的技术价值。"],
        font_size=13,
    )
    add_footer(slide)


def render_closing(slide) -> None:
    add_slide_header(slide, 11, "总结与展望")
    add_card(slide, 0.72, 1.45, 5.55, 4.55, "阶段总结", [
        "完成了一套可运行的 Android 道路识别与辅助提示软件原型。",
        "已形成操作手册、源程序鉴别材料和软著申请材料。",
        "当前成果能够支撑结题展示、软件申报和后续优化。"])
    add_card(slide, 6.55, 1.45, 5.85, 4.55, "后续展望", [
        "补充更多农村道路与复杂天气数据。",
        "增强遮挡、弱光、复杂目标场景下的鲁棒性。",
        "继续完善提醒规则，并探索后续硬件协同方向。"], title_color=Theme.blue_strong)
    thanks = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.35), Inches(6.25), Inches(10.6), Inches(0.48))
    style_box(thanks, Theme.blue_strong, Theme.blue_strong)
    add_textbox(slide, Inches(1.48), Inches(6.33), Inches(10.3), Inches(0.2), "谢谢各位老师，恳请批评指正。", font_size=14, color=Theme.white, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide)


def render_backup_params(slide) -> None:
    add_slide_header(slide, 12, "答辩备份：训练参数解释")
    add_textbox(slide, Inches(0.72), Inches(1.08), Inches(6.5), Inches(0.25), "这页不主动讲，老师问到训练细节时再翻。", font_size=12, color=Theme.muted)
    items = [
        ("Epoch", "训练轮数，分割主配置 100，检测主配置 80。"),
        ("Batch", "每次送入模型的样本数，受显存和输入尺寸限制。"),
        ("Learning Rate", "控制参数更新步长，分割主配置 0.00015。"),
        ("imgsz / image_size", "输入图像尺寸；分割训练 512，检测训练主配置 704。"),
        ("AMP", "混合精度训练，降低显存占用并提升训练效率。"),
        ("val_interval", "每隔几轮做一次验证；当前分割配置是每 2 轮一次。"),
        ("score threshold", "检测置信度阈值，当前 Android 配置为 0.35。"),
        ("IoU threshold", "NMS 阈值，当前 Android 配置为 0.45。"),
    ]
    for idx, (title, desc) in enumerate(items):
        col = idx % 2
        row = idx // 2
        x = 0.72 + col * 6.0
        y = 1.45 + row * 1.3
        add_card(slide, x, y, 5.45, 1.05, title, [desc], title_color=Theme.blue_strong)
    add_footer(slide)


def render_backup_relations(slide) -> None:
    add_slide_header(slide, 13, "答辩备份：训练模型与部署模型关系")
    add_textbox(slide, Inches(0.72), Inches(1.08), Inches(7.2), Inches(0.26), "这页用来回答：训练模型和导出模型到底是不是一回事？", font_size=12, color=Theme.muted)
    stages = [
        ("数据与训练", "公开数据 + 自采样本\nPyTorch / Ultralytics"),
        ("训练产物", "best.pt / last.pt\n保存的是训练权重"),
        ("中间导出", "ONNX\n跨框架中间表示"),
        ("部署成品", "TFLite\nAndroid 端最终部署格式"),
    ]
    xs = [0.82, 3.55, 6.28, 9.01]
    for (title, desc), x in zip(stages, xs):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(2.05), Inches(2.15), Inches(2.0))
        style_box(card, Theme.white, Theme.border, width=1.0)
        add_textbox(slide, Inches(x + 0.1), Inches(2.28), Inches(1.95), Inches(0.24), title, font_size=15, color=Theme.dark, bold=True, align=PP_ALIGN.CENTER)
        add_textbox(slide, Inches(x + 0.08), Inches(2.78), Inches(1.98), Inches(0.8), desc, font_size=12, color=Theme.text, align=PP_ALIGN.CENTER)
    for x in (2.98, 5.71, 8.44):
        add_textbox(slide, Inches(x), Inches(2.82), Inches(0.28), Inches(0.2), ">", font_size=28, color=Theme.blue_strong, bold=True, align=PP_ALIGN.CENTER)
    explain = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(4.55), Inches(11.45), Inches(1.5))
    style_box(explain, Theme.light_blue, Theme.border, width=1.0)
    add_bullets(slide, 1.05, 4.8, 11.0, 0.8, [
        "U-Net / YOLOv8 是模型结构，不是文件格式。",
        ".pt 更偏训练侧，可能还带 epoch、优化器等信息；.onnx / .tflite 更偏推理部署。",
        "部署时真正跑在手机上的不是“训练框架”，而是对应的推理引擎。"],
        font_size=13,
    )
    add_footer(slide)


def render_backup_tflite(slide) -> None:
    add_slide_header(slide, 14, "答辩备份：为什么 Android 端优先选 TFLite")
    add_card(slide, 0.72, 1.45, 3.75, 2.5, "TFLite 的原因", [
        "Android 端生态更成熟，解释器和 Delegate 更直接。",
        "更适合 CameraX + 端侧推理这类场景。",
        "集成成本和工程复杂度更低。"], title_color=Theme.blue_strong)
    add_card(slide, 4.8, 1.45, 3.75, 2.5, "ONNX 的角色", [
        "作为跨平台中间格式，便于导出、调试和一致性对照。",
        "也可作为备用运行方案，但不是当前 Android 主后端。"])
    add_card(slide, 8.88, 1.45, 3.35, 2.5, "本项目当前落地", [
        "分割：主部署为 TFLite FP16，保留 dynamic range 备用。",
        "检测：Android 端当前资产已使用 detection.tflite。"])
    note = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(4.35), Inches(11.45), Inches(1.42))
    style_box(note, Theme.light_blue, Theme.border, width=1.0)
    add_bullets(slide, 1.02, 4.62, 11.0, 0.7, [
        "训练时用的 PyTorch / Ultralytics 框架并不会直接搬到手机上。",
        "Android 端更关注的是：能否稳定推理、是否支持 GPU、是否容易和现有工程集成。"],
        font_size=13,
    )
    add_footer(slide)


def build_markdown() -> str:
    lines = [
        "# 阡陌智行结题答辩PPT逐页文案",
        "",
        "生成文件：`阡陌智行结题答辩PPT_草稿.pptx`",
        "",
        "说明：前 11 页为主讲内容，默认控制在 5-7 分钟内讲完；第 12-14 页为答辩追问备用页。",
        "",
    ]
    for spec in SLIDES:
        lines.extend([
            f"## 第{spec.number}页：{spec.title}",
            "",
            f"**建议讲述时长**：{spec.talk_time}",
            "",
            "**页面要点**",
            "",
        ])
        lines.extend([f"- {item}" for item in spec.bullets])
        lines.extend([
            "",
            "**建议配图**",
            "",
        ])
        if spec.images:
            lines.extend([f"- `{name}`" for name in spec.images])
        else:
            lines.append("- 本页以蓝白信息卡和结构图形为主，不强依赖图片。")
        lines.extend([
            "",
            "**版式提示**",
            "",
            f"- {spec.layout_tip}",
            "",
        ])
    return "\n".join(lines)


def build_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank = prs.slide_layouts[6]
    renderers = [
        render_cover,
        render_background_problem,
        render_scope,
        render_system,
        render_functions,
        render_pipeline,
        render_model_choices,
        render_results_visual,
        render_metrics,
        render_tradeoffs,
        render_closing,
        render_backup_params,
        render_backup_relations,
        render_backup_tflite,
    ]
    for render in renderers:
        slide = prs.slides.add_slide(blank)
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = Theme.light
        render(slide)
    return prs


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(build_markdown(), encoding="utf-8")
    prs = build_presentation()
    prs.save(str(PPT_PATH))
    print(f"markdown: {MD_PATH}")
    print(f"pptx: {PPT_PATH}")


if __name__ == "__main__":
    main()
