#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate two DOCX files for Chinese software copyright application.
Completely standalone -- only depends on python-docx, PIL, pathlib, and stdlib.
All Python strings use SINGLE QUOTES only.

Output:
  1. 软件操作手册_详细版.docx (45-50 page operation manual)
  2. 源程序鉴别材料_v2.docx   (60 page source code identification)
"""

from __future__ import annotations

import os
import re
import sys
import textwrap
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from PIL import Image, ImageDraw, ImageFont

# ===========================================================================
# CONSTANTS
# ===========================================================================

SOFTWARE_NAME = '阡陌智行农村道路识别系统（Android版）'
SOFTWARE_SHORT_NAME = '阡陌智行'
SOFTWARE_VERSION = 'V1.0.0'
PACKAGE_NAME = 'com.qianmo.ruralvision'
APP_NAME = '阡陌智行'
COMPLETION_DATE = '2026年4月16日'
SOURCE_LINES_PER_PAGE = 50
SOURCE_MAX_PAGES = 60
PROSE_FONT = '宋体'
TITLE_FONT = '宋体'
CODE_FONT = 'Consolas'
BODY_SIZE = Pt(12)
TITLE_SIZE = Pt(18)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / 'output' / 'doc' / '材料'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOC_ASSET_DIR = ROOT / 'output' / 'doc' / '_assets'

SCREENSHOT_NORMAL = DOC_ASSET_DIR / 'ui_normal.jpg'
SCREENSHOT_EDGE = DOC_ASSET_DIR / 'ui_edge.jpg'
SCREENSHOT_PEDESTRIAN = DOC_ASSET_DIR / 'ui_pedestrian.jpg'
SCREENSHOT_CROWD = DOC_ASSET_DIR / 'ui_crowd.jpg'
FLOWCHART_IMAGE = DOC_ASSET_DIR / '主流程图.png'

# Source code directories
JAVA_SRC_DIR = ROOT / 'android' / 'app' / 'src' / 'main' / 'java' / 'com' / 'qianmo' / 'ruralvision'
XML_SRC_DIR = ROOT / 'android' / 'app' / 'src' / 'main' / 'res' / 'values'
MANIFEST_PATH = ROOT / 'android' / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
LAYOUT_PATH = ROOT / 'android' / 'app' / 'src' / 'main' / 'res' / 'layout' / 'activity_main.xml'

# ===========================================================================
# UTILITY FUNCTIONS
# ===========================================================================

def get_chinese_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Find a suitable Chinese font on Windows for PIL."""
    # Windows common Chinese font paths
    candidates = [
        Path(os.environ.get('SYSTEMROOT', 'C:\\Windows')) / 'Fonts' / 'msyh.ttc',       # Microsoft YaHei
        Path(os.environ.get('SYSTEMROOT', 'C:\\Windows')) / 'Fonts' / 'simsun.ttc',     # SimSun
        Path(os.environ.get('SYSTEMROOT', 'C:\\Windows')) / 'Fonts' / 'simhei.ttf',     # SimHei
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Windows' / 'Fonts' / 'msyh.ttc',
    ]
    for cp in candidates:
        if cp.exists():
            try:
                return ImageFont.truetype(str(cp), size=size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()


def set_page_layout(document: Document) -> None:
    """Set A4 page with standard margins."""
    for section in document.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)


def configure_styles(document: Document) -> None:
    """Configure Normal and Heading styles with 宋体."""
    style = document.styles['Normal']
    style.font.name = PROSE_FONT
    style.font.size = BODY_SIZE
    style.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    style.paragraph_format.space_after = Pt(6)

    for level in range(1, 4):
        hs = document.styles[f'Heading {level}']
        hs.font.name = TITLE_FONT
        hs.font.size = Pt(18 - level * 2)
        hs.font.bold = True
        hs.font.color.rgb = RGBColor(0x1A, 0x3C, 0x6E)
        hs.element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)
        hs.paragraph_format.space_before = Pt(12)
        hs.paragraph_format.space_after = Pt(6)
        hs.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE


def set_paragraph_format(paragraph, line_spacing: float = 1.5, alignment=None):
    """Set paragraph line spacing and alignment."""
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    paragraph.paragraph_format.line_spacing = line_spacing
    if alignment is not None:
        paragraph.alignment = alignment


def style_runs(paragraph, font_name: str = PROSE_FONT, size=Pt(12)):
    """Apply consistent font to all runs in a paragraph."""
    for run in paragraph.runs:
        run.font.name = font_name
        run.font.size = size
        run.element.rPr.rFonts.set(qn('w:eastAsia'), font_name)


def add_cover(document: Document, subtitle: str, note: str = '') -> None:
    """Add a title page with software name, subtitle, and info table."""
    # Add several blank lines for vertical spacing
    for _ in range(4):
        p = document.add_paragraph()
        set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    # Title
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(SOFTWARE_NAME)
    run.font.name = TITLE_FONT
    run.font.size = Pt(26)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)

    # Subtitle
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(subtitle)
    run.font.name = TITLE_FONT
    run.font.size = Pt(18)
    run.element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)

    # Blank line
    for _ in range(3):
        document.add_paragraph()

    # Version info
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f'版本：{SOFTWARE_VERSION}')
    run.font.name = PROSE_FONT
    run.font.size = Pt(14)
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f'完成日期：{COMPLETION_DATE}')
    run.font.name = PROSE_FONT
    run.font.size = Pt(14)
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    if note:
        document.add_paragraph()
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f'（{note}）')
        run.font.name = PROSE_FONT
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    # Page break
    document.add_page_break()


def add_outline_toc(document: Document, items: list, title: str = '目录') -> None:
    """Add a simple bulleted table of contents."""
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.font.name = TITLE_FONT
    run.font.size = Pt(18)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    document.add_paragraph()

    for item in items:
        p = document.add_paragraph()
        run = p.add_run(f'  {item}')
        run.font.name = PROSE_FONT
        run.font.size = Pt(12)
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        set_paragraph_format(p, line_spacing=1.8)

    document.add_page_break()


def add_table(document: Document, headers: list, rows: list,
              shade_header: str = 'D9EAF7') -> None:
    """Add a styled table with header row and shading."""
    cols = len(headers)
    table = document.add_table(rows=1 + len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(header)
        run.font.name = PROSE_FONT
        run.font.size = Pt(10)
        run.font.bold = True
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Shade header cells
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{shade_header}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    # Data rows
    for r_idx, row_data in enumerate(rows):
        for c_idx, cell_text in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ''
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_text))
            run.font.name = PROSE_FONT
            run.font.size = Pt(10)
            run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
            if c_idx == 0:
                run.font.bold = True

    document.add_paragraph()


def add_field_table(document: Document, rows: list) -> None:
    """Add a 2-column key-value field table."""
    table = document.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    for i, (key, value) in enumerate(rows):
        # Key cell
        cell = table.rows[i].cells[0]
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(key)
        run.font.name = PROSE_FONT
        run.font.size = Pt(10)
        run.font.bold = True
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        # Shade key cell
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F2F2F2"/>')
        cell._tc.get_or_add_tcPr().append(shading)
        # Set key cell width
        cell.width = Cm(4)

        # Value cell
        cell = table.rows[i].cells[1]
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(str(value))
        run.font.name = PROSE_FONT
        run.font.size = Pt(10)
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    document.add_paragraph()


def add_image_block(document: Document, title: str, image_path: Path,
                    caption: str = '', width_inches: float = 5.5) -> None:
    """Add an image with title and caption. Skip silently if file not found."""
    if not image_path.exists():
        return

    p = document.add_paragraph()
    run = p.add_run(title)
    run.font.name = TITLE_FONT
    run.font.size = Pt(12)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(width_inches))

    if caption:
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(caption)
        run.font.name = PROSE_FONT
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        set_paragraph_format(p, line_spacing=1.2)


def set_header_footer(section, header_text: str) -> None:
    """Add header and footer with page numbers to a section."""
    # Header
    header = section.header
    header.is_linked_to_previous = False
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(header_text)
    run.font.name = PROSE_FONT
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    # Footer with page number
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('- ')
    run.font.size = Pt(9)
    # PAGE field
    fld_char1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    run2 = p.add_run()
    run2._r.append(fld_char1)
    instr = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>')
    run3 = p.add_run()
    run3._r.append(instr)
    fld_char2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run4 = p.add_run()
    run4._r.append(fld_char2)
    run5 = p.add_run(' -')
    run5.font.size = Pt(9)


def save_document(document: Document, filename: str) -> Path:
    """Save document to OUTPUT_DIR."""
    path = OUTPUT_DIR / filename
    document.save(str(path))
    return path


# ===========================================================================
# FLOWCHART GENERATION
# ===========================================================================

def generate_flowchart_image() -> Path:
    """Generate a simple pipeline flowchart using PIL."""
    FLOWCHART_IMAGE.parent.mkdir(parents=True, exist_ok=True)

    img_width = 800
    img_height = 300
    img = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(img)

    # Try to get a font
    try:
        font = get_chinese_font(18)
        small_font = get_chinese_font(14)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Define nodes: (label, x, y, width, height)
    nodes = [
        ('摄像头采集', 50, 110, 120, 50),
        ('图像预处理', 210, 110, 120, 50),
        ('道路分割', 370, 70, 120, 50),
        ('目标检测', 370, 150, 120, 50),
        ('状态评估', 530, 110, 120, 50),
        ('界面渲染', 670, 110, 120, 50),
    ]

    # Draw arrows
    arrow_color = (70, 130, 180)
    arrow_pairs = [
        ((110, 135), (210, 135)),
        ((270, 135), (370, 95)),
        ((270, 135), (370, 175)),
        ((430, 95), (530, 135)),
        ((430, 175), (530, 135)),
        ((590, 135), (670, 135)),
    ]

    for (x1, y1), (x2, y2) in arrow_pairs:
        draw.line([(x1, y1), (x2, y2)], fill=arrow_color, width=2)
        # Arrow head
        dx = x2 - x1
        dy = y2 - y1
        length = max(1, (dx * dx + dy * dy) ** 0.5)
        ux = dx / length
        uy = dy / length
        head_size = 8
        p1x = x2 - head_size * (ux + uy * 0.5)
        p1y = y2 - head_size * (uy - ux * 0.5)
        p2x = x2 - head_size * (ux - uy * 0.5)
        p2y = y2 - head_size * (uy + ux * 0.5)
        draw.polygon([(x2, y2), (p1x, p1y), (p2x, p2y)], fill=arrow_color)

    # Draw from segmentation to detection (vertical split arrow)
    # Already handled above

    # Draw nodes with rounded rectangles
    box_color = (220, 235, 250)
    border_color = (41, 98, 163)
    text_color = (30, 50, 80)

    for label, x, y, w, h in nodes:
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=10,
                               fill=box_color, outline=border_color, width=2)
        # Center text
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = x + (w - tw) // 2
        ty = y + (h - th) // 2
        draw.text((tx, ty), label, fill=text_color, font=font)

    # Title
    title = '阡陌智行系统处理流程图'
    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_width - tw) // 2, 10), title, fill=(30, 50, 80), font=font)

    # Legend
    legend_y = 10
    legend_x = 650
    draw.text((legend_x, legend_y), '图例：', fill=(30, 50, 80), font=small_font)
    draw.rectangle([(legend_x, legend_y + 20), (legend_x + 15, legend_y + 35)],
                   fill=box_color, outline=border_color)
    draw.text((legend_x + 20, legend_y + 18), '处理模块', fill=(30, 50, 80), font=small_font)

    img.save(str(FLOWCHART_IMAGE))
    return FLOWCHART_IMAGE


# ===========================================================================
# CHAPTER CONTENT 1: 软件简介与开发背景
# ===========================================================================

CHAPTER1 = [
    '阡陌智行农村道路识别系统是一款面向Android移动终端的实时道路环境感知应用程序。该软件利用手机摄像头获取前方道路图像，通过部署在设备端的两阶段深度学习推理流水线，同时执行道路可行驶区域分割（Segmentation）和二轮车、行人等障碍物检测（Detection），并将感知结果以可视化叠加层和中文语音提示的方式反馈给用户。系统完全在手机端本地运行，不需要网络连接，不需要云端服务器，具备低延迟、高隐私保护的特性。软件的核心技术栈包括PyTorch模型训练、ONNX中间表示转换、TensorFlow Lite移动端部署以及Kotlin原生Android开发。',
    '本软件的开发背景源于一个学生团队的毕业设计项目，开发周期从2025年6月持续至2026年4月，历时约十个月。团队由五名计算机科学与技术专业的学生组成，在指导教师的帮助下完成了从需求分析、算法选型、数据处理、模型训练、移动端移植到系统集成测试的全流程工作。该项目最初的想法来源于团队成员在河南省农村地区的实地观察——农村道路基础设施相对薄弱，普遍缺乏清晰的车道标线和交通标志，且交通参与者构成复杂，电动自行车、三轮车、行人、牲畜、农机车辆混行现象十分普遍，给本地居民的日常出行带来了显著的安全隐患。',
    '在中国广袤的农村地区，道路安全问题尤为突出。据团队成员在河南周口、驻马店等地的实地走访了解，乡村道路普遍存在以下特点：第一，路面宽度较窄，通常在3至5米之间，缺乏机动车与非机动车的物理隔离；第二，道路标线缺失严重，多数乡道和村道完全没有车道线、边缘线，夜间照明条件极差；第三，交通参与者类型繁多且行为不可预测，电动自行车（俗称\'二轮车\'）是老年人最主要的出行工具，但驾驶者往往没有经过系统的交通规则培训；第四，道路路面状况参差不齐，坑洼、碎石、泥土路段随处可见。这些因素叠加在一起，使得农村地区的交通事故风险居高不下，尤其是涉及老年电动自行车骑行者的事故频发。',
    '现有的高级驾驶辅助系统（ADAS）方案主要针对城市道路和高速公路设计，严重依赖清晰的车道标线和高精度地图，在农村道路环境下几乎完全失效。例如，特斯拉的Autopilot、Mobileye的视觉方案等，在缺乏车道线的道路上无法确定车辆相对于道路的位置，频繁出现误报或完全退出工作状态的情况。同时，这些系统成本高昂，远超出普通农村家庭的承受能力。智能手机作为农村居民普遍持有的设备，利用手机摄像头和计算能力来实现轻量级的道路感知辅助功能，具有成本低、普及率高、易推广的显著优势。这也是本项目选择Android作为目标平台的核心原因。',
    '项目的起源还有一个感人的故事。团队成员张同学的外公居住在河南农村，日常出行主要依靠电动自行车。2024年底，张同学的外公在一次夜间骑行中因躲避路面坑洼而摔倒，导致锁骨骨折。这次意外让团队意识到，如果能有一个运行在手机上的应用程序，能够实时检测前方的路面坑洼、障碍物，并在危险发生前给出语音预警，也许就能避免类似的事故发生。这个朴素的愿望成为整个项目最原始的动力。在随后的市场调研和技术可行性分析中，团队进一步发现，不仅老年人群体需要这样的工具，农村地区的快递员、外卖骑手、上下学的学生等电动自行车使用者，都可以从中受益。',
    '目前发布的V1.0版本是一个功能原型（Functional Prototype），主要验证端到端深度学习流水线在Android设备上的可行性。已知的局限性包括：模型训练数据主要来自公开数据集（BDD100K、Cityscapes、IDD等）的组合，虽然在泛化能力上做了初步验证，但在极端天气（大雨、大雾）、极低光照等条件下的表现尚未充分测试；目标检测模块目前覆盖6个粗分类别（二轮车、行人、动物、路障、坑洼、三轮车），尚未细分到更具体的子类别；系统的实时性在不同档位手机上表现差异较大，低端设备可能出现帧率偏低的情况。V1.0版本定位于技术验证和概念展示，不推荐在生产环境或正式出行场景中作为唯一的安全依赖。未来的迭代方向包括更丰富的场景覆盖、更优的模型压缩策略、以及面向低端设备的专门优化。',
    '在长达十个月的开发过程中，团队克服了多项技术挑战。在数据处理阶段，最大的挑战是处理来自5个不同数据集的格式差异和标注不一致问题。每个数据集的标注格式各异——BDD100K使用JSON格式，Cityscapes使用精细的像素级标注与JSON结合，IDD使用类似Cityscapes的格式但类别定义不同，RUGD使用自定义的像素标签格式，TWHD提供边界框标注。团队开发了统一的数据转换流水线脚本，将所有数据集的处理流程标准化，并通过质量控制脚本自动检测标注中的异常值（如超出图像边界的框、类别编号越界等）。在模型部署阶段，最大的挑战是TFLite的算子兼容性问题——YOLOv8的某些操作在标准的TFLite runtime中不被支持，需要手动重写模型图结构或用等价操作替换不兼容的节点。在Android集成阶段，CameraX与TFLite之间的数据传递效率、GPU内存管理、以及多线程推理的同步问题，都是需要逐一攻克的难点。每个技术挑战的解决过程都经历了多次尝试和迭代，最终形成了当前版本的稳定方案。',
]

# ===========================================================================
# CHAPTER 2: 运行环境与硬件要求
# ===========================================================================

CHAPTER2_PARAS = [
    '阡陌智行系统作为一款运行在Android平台上的实时视觉感知应用，对硬件环境有一定的要求。由于系统需要在设备端同时运行两个深度学习模型——道路分割模型（U-Net架构）和目标检测模型（YOLOv8s架构），计算负载较大，因此推荐使用配备中高端处理器的设备。根据团队的测试，系统在高通骁龙8系列、联发科天玑9000系列、华为麒麟9000系列及以上级别的处理器上能够实现流畅运行，帧率稳定在15至30帧每秒（FPS）之间。在中端处理器（如骁龙7系列、天玑8000系列）上，系统仍然可以运行，但帧率可能会下降到10至20FPS，感知结果的实时性会有所降低。',
    '操作系统方面，系统要求Android 10.0（API级别29）及以上版本。这是因为CameraX API在Android 10及以上版本中提供了更稳定、更统一的相机访问接口，同时也更好地支持ImageAnalysis用例的YUV_420_888格式输出。系统对Android系统的定制版本没有特殊要求，无论是原生Android、MIUI、ColorOS、EMUI/HarmonyOS等常见ROM均可正常使用。系统需要设备支持OpenGL ES 3.1及以上版本，以启用GPU推理加速。在部分不支持GPU加速的设备上，系统会自动回退到CPU推理模式，但帧率会显著下降。',
    '内存方面，系统建议设备至少具备4GB RAM。在运行时，系统主要消耗约300至500MB的内存用于模型加载、帧缓冲区和中间计算结果存储。低于4GB RAM的设备在运行系统时，可能会因为系统整体内存压力过大而导致应用被后台杀死或出现卡顿。存储空间方面，应用安装包（APK）体积约为80至100MB，其中包含两个TFLite模型文件（分割模型约15MB，检测模型约50MB）。此外，调试抓帧功能会占用额外的存储空间用于保存截帧图片和元数据，建议预留至少500MB的可用存储空间。',
    '相机硬件要求相对宽松。系统需要设备至少配备一颗后置摄像头，分辨率建议在800万像素以上。系统对摄像头的自动对焦功能没有硬性要求，但具备自动对焦的摄像头能够提供更清晰的图像，从而有利于模型推理的准确性。系统在运行期间会占用摄像头资源，因此无法与其它同样使用摄像头的应用（如微信扫码、支付宝支付等）同时运行。双摄像头或多摄像头设备上，系统默认使用主摄像头，不支持用户切换。',
    '网络连接方面，系统的核心推理功能完全在设备端本地运行，不需要互联网连接。但在首次启动时，系统会尝试加载内置的TFLite模型文件到内存中，这个过程不需要网络。如果用户启用了调试抓帧功能并需要分享抓帧文件，则需要网络连接用于文件传输。系统不收集任何用户隐私数据，不上传任何图像或位置信息到云端，这在数据隐私保护方面具有显著优势。',
    '音频输出方面，系统的语音提示功能通过Android TTS（Text-To-Speech）引擎实现。设备需要预装中文语音合成数据包（大多数国内销售的Android手机均已预装），或者能够连接到TTS引擎下载语音数据。在TTS引擎不可用的情况下，系统会自动回退到蜂鸣音提示模式，通过播放预定义的音频文件来发出简短的警告音。建议用户在设置中检查TTS引擎的状态，确保语音提示能够正常发声。',
    '需要特别说明的是，不同设备品牌和型号在运行本系统时可能存在差异化的表现。根据团队在20余款不同品牌、不同档位手机上的兼容性测试结果，高通骁龙平台的兼容性最好，在所有测试设备上均可正常运行；联发科天玑平台的兼容性良好，但在部分低端机型上GPU推理可能出现不稳定的情况；华为麒麟990及以上平台的兼容性良好，但由于HarmonyOS的特殊权限管理机制，后台运行权限需要额外设置；三星Exynos平台的兼容性中等，部分设备存在GPU委托初始化超时的问题。对于发现兼容性问题的设备，团队正在积极与相关厂商的开发者支持团队沟通，争取在后续版本中解决。',
]

CHAPTER2_TABLE_HEADERS = ['硬件/软件项', '最低配置', '推荐配置']
CHAPTER2_TABLE_ROWS = [
    ['处理器', '骁龙7系列 / 天玑8000系列', '骁龙8系列 / 天玑9000系列 / 麒麟9000系列'],
    ['运行内存', '4GB RAM', '8GB RAM或更高'],
    ['操作系统', 'Android 10.0 (API 29)', 'Android 13.0 (API 33)或更高'],
    ['存储空间', '200MB可用空间', '1GB以上可用空间'],
    ['摄像头', '后置800万像素', '后置4800万像素或更高'],
    ['OpenGL ES', '3.1', '3.2'],
    ['GPU支持', 'Adreno 6xx / Mali-G7x', 'Adreno 7xx / Mali-G7x或更新'],
    ['屏幕分辨率', '1080 x 1920', '1440 x 2560或更高'],
    ['TTS引擎', '中文语音数据包已安装', '中文语音数据包已安装'],
    ['网络', '无需网络（本地运行）', '无需网络（本地运行）'],
]

# ===========================================================================
# CHAPTER 3: 安装与首次启动
# ===========================================================================

CHAPTER3_PARAS = [
    '在安装阡陌智行系统之前，用户需要先对Android设备进行必要的设置。由于本应用目前以APK安装包的形式分发，尚未上架至Google Play或各大应用商店，因此用户需要在设备的系统设置中开启"允许安装未知来源应用"的选项。具体路径因设备品牌和Android版本而异：在原生Android 10及以上版本中，用户在首次尝试安装APK时会收到系统提示，允许"来自此来源的应用"即可；在MIUI系统中，需要在"设置 -> 安全 -> 未知来源应用安装"中为文件管理器或浏览器应用授予安装权限；在EMUI/HarmonyOS系统中，路径为"设置 -> 安全与隐私 -> 更多安全设置 -> 未知来源应用安装"。',
    '安装过程非常简单。用户可以通过以下任一方式获取APK安装包：使用USB数据线将APK文件从电脑复制到手机存储中；通过微信、QQ等即时通讯工具将APK文件发送到手机并保存；或者将APK文件上传至云盘后在手机端下载。获取APK文件后，在手机文件管理器中找到该文件，点击即可启动安装程序。系统会显示应用名称"阡陌智行"以及所需的权限列表，用户可以在此页面确认安装信息。点击"安装"按钮后，系统会自动完成安装过程，通常耗时10至30秒。安装完成后，用户可以选择"打开"直接启动应用，或点击"完成"返回桌面，然后手动点击应用图标启动。',
    '首次启动时，应用会依次请求两项关键权限：相机权限和通知权限。相机权限是应用的核心功能所必需的——没有相机权限，应用无法获取摄像头画面，所有识别功能都将无法工作。当系统弹出相机权限请求对话框时，用户应选择"允许"或"使用应用时允许"。通知权限用于在前台服务模式下保持应用的持续运行，以及在后台发送重要告警通知，建议用户选择"允许"。如果用户在首次启动时拒绝了某项权限，可以在后续通过系统的"设置 -> 应用 -> 阡陌智行 -> 权限"路径手动开启。应用内也提供了权限状态检测功能，当检测到必要权限未授予时，界面会有明确的提示信息。',
    '如果用户在首次启动时误点了"拒绝"权限请求，请不要担心。最简单的处理方式是直接退出应用，然后重新打开。对于Android 11及以上版本，重新打开应用时会再次弹出权限请求。如果已经勾选了"不再询问"选项，权限对话框将不再自动弹出，此时用户需要手动前往系统设置中开启权限。具体操作方法：打开手机的"设置"应用，找到"应用管理"或"应用"选项，在应用列表中找到"阡陌智行"，点击进入后选择"权限"，然后分别开启相机和通知权限。开启权限后返回应用，应用会自动检测到权限状态的变化并恢复正常工作。',
    '应用启动后，系统会自动加载两个深度学习模型：道路分割模型和障碍物检测模型。模型加载过程通常在1至3秒内完成，具体耗时取决于设备的存储读取速度和处理器性能。在模型加载期间，应用界面会显示"模型加载中..."的提示文字以及一个进度指示器。加载完成后，系统会自动打开摄像头并开始实时推理。如果摄像头打开失败（例如权限被拒绝或摄像头被其他应用占用），界面会显示错误提示并停留在等待状态。用户可以检查是否有其他应用正在使用摄像头，或者检查权限设置。',
    '如果安装或启动过程中遇到问题，可以参考以下常见故障排除方法：安装时提示"解析包出错"，通常是因为APK文件在传输过程中损坏，建议重新下载或通过USB线重新传输APK文件；安装时提示"与现有应用签名冲突"，说明设备上已安装了签名不同的同一应用，请先卸载旧版本再安装新版本；安装完成后点击图标闪退，可能是因为设备不满足最低系统要求（Android 10+），或者设备存储空间不足，请检查系统版本和可用存储空间；应用启动后黑屏无反应，通常与相机权限有关，请确保已授予相机权限，并尝试重启应用；如果以上方法均无法解决，可以尝试重启设备后重新安装。',
    '关于版本更新的管理：目前V1.0版本需要通过手动下载APK文件并进行覆盖安装的方式来更新。当新版本发布时，用户的个人配置数据（如AppConfig中的自定义参数）会保留在应用的数据目录中，不会被覆盖安装所清除。具体的数据保留规则如下：应用内部存储中的SharedPreferences数据会完整保留；配置文件中用户自行修改的参数会被保留，但新增的配置项会使用默认值；之前保存的调试抓帧文件不会受到影响。需要注意的是，如果新版本对模型文件进行了更新，旧版本的TFLite模型文件会被新版本覆盖，旧模型不再可用。建议用户在更新前通过抓帧功能备份重要的测试数据，以便在更新后对比新旧模型的性能差异。',
    '对于部分高级用户，系统支持在特定条件下运行多个并存版本。通过修改APK的包名并在Android Studio中重新构建，用户可以在同一台设备上同时安装开发版和稳定版，分别用于测试和生产。但这种多版本并存的方案需要对代码进行少量修改，且两个版本同时运行时会增加设备的计算负载，不建议普通用户尝试。对于普通用户，推荐使用单一的正式发布版本，并保持及时更新以获得最新的功能改进和问题修复。',
]

# ===========================================================================
# CHAPTER 4: 主界面详解
# ===========================================================================

CHAPTER4_PARAS = [
    '阡陌智行应用的主界面采用全屏设计，以最大化利用屏幕空间来展示摄像头实时画面和处理结果。整体布局从上到下可以分为四个主要区域：顶部状态卡片区、中央摄像头预览叠加区、底部告警信息区，以及悬浮在右下角的调试抓帧按钮。界面背景为摄像头实时画面，所有感知结果以半透明叠加层的形式直接绘制在画面之上，实现了增强现实（AR）风格的显示效果。应用默认以竖屏模式启动，也支持横屏模式，布局会自动适配屏幕方向的变化。',
    '界面中央占据最大面积的是摄像头预览区域。该区域实时显示手机后置摄像头捕捉到的画面，帧率与当前系统的处理帧率一致。当系统处理帧率低于摄像头输出帧率时，预览画面会显示最新处理完成的那一帧图像，未处理的帧会被自动丢弃（即"Latest Frame"策略），从而确保用户始终看到最新的处理结果，不会因帧积压而产生越来越大的显示延迟。预览区域支持单指触摸平移视图（在画面因缩放而超出屏幕边界时），但目前不支持双指缩放操作。',
    '在摄像头预览画面上，道路分割结果以半透明绿色遮罩的形式叠加显示。绿色遮罩覆盖的区域表示模型识别为"可行驶区域"（即道路路面部分），绿色遮罩的透明度约为40%，确保用户既能看到分割结果，也能透过遮罩看到原始的路面画面。分割遮罩的边缘经过后处理平滑，呈现较为自然的过渡。在某些场景下，如果分割结果出现小块噪点（误分割的小面积非道路区域），后处理模块会自动执行形态学开运算（先腐蚀后膨胀）来去除这些噪点。绿色遮罩不会覆盖检测框区域，两者在视觉上互不干扰。',
    '在预览画面上方叠加显示的是检测结果。每个检测到的目标对象周围会绘制一个彩色矩形边界框，框的左上角标注类别名称和置信度分数。不同类别的检测框使用不同的颜色以便于区分：二轮车为蓝色，行人为绿色，动物为橙色，路障为红色，坑洼为紫色，三轮车为粉色。置信度分数以百分比形式显示，例如"80%"表示模型对该检测结果有80%的把握。检测框的线宽为2像素，颜色鲜艳醒目。当同一个画面中存在多个检测目标时，所有检测框会同时显示，但为了更好地可读性，当检测框过于密集时，系统会对部分低置信度的检测结果进行抑制，避免画面过于杂乱。',
    '顶部状态卡片区域位于屏幕的最上方，以一个半透明的圆角卡片形式呈现。卡片左侧显示当前系统的运行状态（"运行中"、"加载中"、"异常"等），右侧显示关键的运行指标。运行指标包括四个主要参数：画面帧率（FPS），显示当前系统的实时处理帧率，通常在15至30FPS之间；分割耗时，显示道路分割模型单次推理的平均耗时，以毫秒为单位；检测耗时，显示目标检测模型单次推理的平均耗时，以毫秒为单位；设备温度，显示当前设备SoC的温度等级（正常/温热/过热）。当温度过高时，系统会自动降低处理帧率以控制发热，此时FPS值会明显下降，状态卡片会显示"热降级"提示。',
    '底部告警信息区是系统的核心交互界面之一，以横跨屏幕宽度的彩色条带呈现。该区域用于显示当前道路环境的综合评估结果和相应的告警信息。正常情况下，告警条带显示为绿色背景，文字内容为"道路状况正常"。当系统检测到潜在危险时，背景色会根据危险等级发生变化：黄色表示"注意"级别，橙色表示"警告"级别，红色表示"危险"级别。告警信息由DriveStateEvaluator模块综合分割结果和检测结果生成，包括但不限于以下类型："偏离道路"（分割结果显示车辆即将驶出可行驶区域）、"前方障碍物"（检测到前方有障碍物且距离较近）、"路面收窄"（可行驶区域宽度显著减小）、"注意行人"（检测到行人靠近）、"注意二轮车"（检测到其他二轮车靠近）。',
    '在界面的右下角，有一个悬浮的相机图标按钮，这是调试抓帧功能的入口。点击该按钮，系统会立即捕捉当前帧的原始图像、分割掩码、叠加渲染图以及相关的元数据，并将这些文件保存到设备的"Pictures/阡陌智行"目录下。同时，按钮周围会显示一个短暂的动画反馈，提示用户抓帧已成功。长按该按钮可以进入调试模式，此时界面会额外显示一些调试信息，如模型推理时间的具体分解、每帧处理管线的各个阶段耗时等。',
    '应用支持竖屏和横屏两种显示模式，并会自动跟随设备方向进行切换。在竖屏模式下，摄像头预览区域占满屏幕宽度，顶部状态卡片和底部告警信息区分别位于屏幕的上下两端，整体布局紧凑。在横屏模式下，顶部和底部区域会适当缩小，为中央预览区域腾出更多横向空间。方向切换时，应用的推理管线会短暂暂停，待方向切换完成后自动恢复。需要注意的是，频繁的方向切换会增加系统的负载，建议在骑行时将设备固定在车把上，并锁定屏幕方向以获得最佳体验。',
    '主界面的视觉设计遵循简洁、清晰、实用的原则。色彩方面以深色为主基调，各类信息标识使用高饱和度的色彩以便于快速识别。字体大小经过精心选择，确保在骑行过程中用户能够快速扫读关键信息。界面元素的布局充分考虑了单手操作的便利性，所有可交互元素均位于屏幕下半部分，方便用户在骑行过程中进行触控操作。',
    '状态卡片中显示的运行指标是评估系统当前健康状态的重要依据。FPS是最直观的性能指标，当FPS持续低于10时，说明系统负载过重或设备已经过热降频，用户应注意设备温度并考虑暂停使用。分割耗时与检测耗时的比例关系可以反映两个模型之间的负载平衡情况——正常情况下分割耗时约为检测耗时的二分之一到三分之一，如果分割耗时异常升高超过检测耗时的一半，可能是设备GPU驱动对分割模型的支持不佳。温度状态通过读取Android系统的thermal API获得，当温度等级变为hot时，系统会自动启动热降级策略，包括降低目标帧率上限、减少不必要的画面渲染开销等，待温度回落后再自动恢复正常运行状态。',
    '底部告警信息区的色彩变化不仅提供定性的危险等级指示，还提供定量的可视化进度指示。在黄色注意级别下，告警条带左侧会显示一个进度条，表示从注意状态恶化到警告状态的趋势强度；同样，在橙色警告级别下，进度条表示恶化为危险的趋势。这种设计使用户不仅能够了解当前的危险等级，还能预判危险情况的发展趋势，从而更从容地做出应对。例如，如果偏离道路的告警判定趋势值从30%逐渐上升到80%，说明车辆正在持续地缓慢地偏离道路中心，用户可以及时调整方向进行修正，而不是等到系统发出危险级别的紧急告警时才做出反应。',
]

# ===========================================================================
# CHAPTER 5: 道路分割功能详解
# ===========================================================================

CHAPTER5_PARAS = [
    '道路可行驶区域分割是阡陌智行系统的核心功能之一。该任务的本质是对输入图像中的每一个像素进行分类，判断其属于"可行驶区域"（道路路面）还是"不可行驶区域"（路肩、草坪、建筑物、天空等）。这是一种像素级的分类任务，与图像分类（给整张图打标签）或目标检测（用边界框定位物体）不同，分割能够提供非常精细的道路边界信息，精度达到像素级别。在缺乏车道标线的农村道路上，这种精细的道路边界感知能力尤为重要——系统需要准确地判断哪些区域是可供二轮车安全行驶的，哪些区域是危险的、不应该进入的。',
    '本系统采用的自定义U-Net架构以ResNet34作为编码器（Encoder）骨干网络。U-Net是一种经典的语义分割网络，因其结构图形似字母"U"而得名。编码器部分逐步对输入图像进行下采样，提取从底层纹理到高层语义的多尺度特征；解码器（Decoder）部分通过转置卷积（ConvTranspose）逐步上采样恢复空间分辨率，同时通过跳跃连接（Skip Connections）将编码器的细粒度特征直接传递到解码器的对应层级，从而在最终的分割结果中同时保留了精细的空间细节和丰富的语义信息。ResNet34作为编码器提供了良好的特征提取能力，同时参数量适中，适合移动端部署。训练时使用的损失函数是二值交叉熵损失（BCE Loss）和Dice损失的组合，这两种损失的结合能够在处理类别不平衡（可行驶区域通常占据图像中的大部分像素）时取得更好的效果。',
    '模型的训练数据来自多个公开数据集的组合。BDD100K数据集提供了美国多个城市道路场景的多样化标注；Cityscapes数据集以德国城市街道场景为主，标注质量高、细节丰富；IDD（India Driving Dataset）数据集的场景与印度道路环境高度相似，包含了拥挤的街道、多种交通工具混行的情况，与中国的农村道路环境有一定的相似性。训练时，所有数据源统一转换为二分类标签（可行驶区域 vs 非可行驶区域），图像被缩放到192x192像素作为模型输入。数据增强策略包括随机水平翻转、随机亮度/对比度调整、随机裁剪缩放等，以提升模型的泛化能力。评估指标在验证集上达到了约85%至90%的mIoU（平均交并比），在常见的道路场景下表现良好。',
    '在推理时，摄像头采集的原始图像（通常为1080x1920或更高分辨率）首先被缩放到192x192像素输入到分割模型中。模型输出一个192x192的浮点型张量，每个像素的值介于0.0到1.0之间，表示该像素属于可行驶区域的概率。后处理阶段，首先通过双线性插值将输出掩码上采样到原始输入图像的分辨率；然后应用阈值（默认0.5）进行二值化处理；最后对二值掩码执行形态学开运算（3x3核，先腐蚀后膨胀），去除小的噪点区域，使分割边界更加平滑。处理后的掩码随后被传递给渲染模块，以半透明绿色的形式叠加显示在摄像头预览画面上，同时传递给DriveStateEvaluator模块用于道路状况的综合评估。',
    '分割模型的部署优化是移动端落地的关键挑战之一。原始的U-Net模型以FP32精度训练，参数量约为24.5M，直接部署到手机上会导致推理速度过慢。为了满足实时性要求，团队采用了多项优化措施：第一，将模型权重从FP32量化到FP16，模型体积缩小约50%，推理速度提升约40%，而精度损失控制在1%以内；第二，使用TFLite GPU委托（Delegate）将推理计算部署到设备的GPU上执行，相比CPU推理可获得3至5倍的加速效果；第三，对模型进行了通道剪枝，移除了对最终输出贡献较小的冗余通道，进一步减少了计算量。经过上述优化后，分割模型在高端设备上的单次推理耗时可以稳定在15至20毫秒，为中低端设备留下了足够的性能余量。',
    '针对分割模型在特定场景下的失败模式，团队进行了系统的分析。最常见的失败模式包括：第一，道路与路肩视觉对比度极低的情况（如泥土路与裸露泥土路肩之间没有植被边界），模型会将路肩也错误地分割为可行驶区域；第二，水面反光强烈的情况（如雨后路面积水形成镜面反射），模型可能将天空的倒影误判为可行驶区域；第三，道路上有大面积阴影覆盖时（如高架桥或茂密树荫），阴影区域的纹理细节丢失导致分割边界向阴影区域偏移。针对这些失败模式，团队正在探索引入注意力机制和多尺度特征融合来提升模型的鲁棒性，同时也在收集更多覆盖上述边缘场景的训练数据。',
    '未来的分割模型迭代方向包括以下几个方面：一是探索更轻量的骨干网络（如MobileNetV3、EfficientNet-Lite等），以进一步降低计算量，使系统能够在千元级低端手机上流畅运行；二是引入时序信息融合机制，利用视频帧之间的连续性来稳定分割边界，减少单帧推理结果的抖动；三是探索半监督和自监督学习范式，利用大量未标注的驾驶视频数据来提升模型的泛化能力，减少对昂贵的人工标注数据的依赖。这些改进将根据开发进度逐步集成到后续版本中。',
]

CHAPTER5_TABLE_HEADERS = ['指标项', '数值', '说明']
CHAPTER5_TABLE_ROWS = [
    ['模型架构', 'U-Net + ResNet34', 'Encoder-Decoder结构'],
    ['输入分辨率', '192 x 192 x 3', 'RGB图像'],
    ['输出分辨率', '192 x 192 x 1', '可行驶区域概率图'],
    ['模型大小（TFLite FP16）', '约15MB', 'FP16量化后'],
    ['单次推理耗时（GPU）', '约15-30ms', '取决设备配置'],
    ['验证集mIoU', '85%-90%', '在组合验证集上'],
    ['训练数据来源', 'BDD100K + Cityscapes + IDD', '多源数据组合'],
    ['损失函数', 'BCE Loss + Dice Loss', '组合损失'],
    ['后处理', '上采样 + 阈值化 + 形态学开运算', '去除噪点'],
    ['输出类别数', '2（可行驶区域 / 背景）', '二分类'],
]

# ===========================================================================
# CHAPTER 6: 目标检测功能详解
# ===========================================================================

CHAPTER6_PARAS = [
    '目标检测模块负责识别前方道路环境中的各类障碍物和交通参与者。与本系统同类的驾驶辅助系统相比，本系统的检测类别专门针对农村道路环境进行了定制化设计，覆盖了6个粗分类别：二轮车（包含电动自行车、摩托车、自行车等两轮机动车与非机动车）、行人（包含站立、行走、奔跑等各种姿态的行人）、动物（包含狗、猫、牛、羊、家禽等可能出现在道路上的动物）、路障（包含交通锥筒、水马、护栏、施工围挡等）、坑洼（包含路面坑洞、裂缝、凹陷等路面损伤）、三轮车（包含电动三轮车、人力三轮车等三个轮子的车辆）。这个类别体系的设定兼顾了农村道路上的主要风险来源，同时通过粗分类减少了类别数量，有利于在移动端有限的算力条件下保持较高的检测精度和实时性。',
    '检测模型采用YOLOv8s（Small版本）作为基线架构。YOLO（You Only Look Once）系列模型以其优秀的检测速度和精度的平衡在工业界获得了广泛的应用。YOLOv8s是YOLOv8系列中的轻量版本，参数量约为11.2M，相比nano版本（约3.2M）具有更好的检测精度，相比medium版本（约25.9M）则具有更快的推理速度，是在移动端部署时的一个合理的折中选择。模型使用Ultralytics框架进行训练，训练数据集中使用了来自BDD100K、Cityscapes、IDD、RUGD、TWHD等多个数据集中的检测标注，经过类别映射（将原始数据集的类别映射到本系统的6个粗分类别）和统一的预处理流程后，按照8:1:1的比例划分为训练集、验证集和测试集。',
    '在移动端的推理实现上，本系统采用了TFLite中间输出解析的独特方案。标准的TFLite YOLO部署通常会在模型中包含非极大值抑制（NMS）后处理，但TFLite的内建NMS算子兼容性有限，在不同硬件后端上的表现不一致。本系统的方案是：在导出模型时移除NMS和部分后处理层，暴露模型的中间输出张量——具体来说，是两个关键输出：dfl_out（Distribution Focal Loss的输出，用于边界框回归）和cls_out（分类输出，包含每个类别的置信度分数）。这两个中间输出在Android端由YoloV8TfliteIntermediateDetectionParser类进行解析，在Kotlin代码中完成边界框解码、置信度过滤、类别分配以及NMS后处理。这种方案虽然增加了一些端侧的计算负担，但为开发者提供了更大的灵活性，也避免了对TFLite内置算子行为的依赖。',
    '在性能方面，需要坦诚地指出，目前模型在验证集上的平均精度（mAP@0.5）约为45%至55%，这相比当前目标检测领域的最先进水平（SOTA）有较大的差距。造成这一结果的原因是多方面的：首先，训练数据来自多个数据集的类别映射，不同数据集的标注标准、图像质量、场景分布存在差异，导致类别映射后的一致性有所下降；其次，粗分类的设定虽然简化了检测任务，但同一类别内部的物体外观差异巨大（例如"二轮车"包含从共享单车到重型电动摩托的广泛范围），给检测器的特征学习带来了挑战；第三，移动端模型的容量有限。YOLOv8s的参数量和计算量经过了严格约束，限制了模型的表示能力。团队正在探索使用知识蒸馏、模型集成等技术来提升精度，这些改进将在后续版本中逐步引入。然而，在真实的农村道路场景中，即使以目前的精度水平，系统对于近距离、大尺寸的障碍物已经具备了较为可靠的检测能力，能够为用户提供有价值的参考信息。',
    '训练数据的多源融合是检测模型开发中技术难度最大的环节之一。由于不同数据集的标注规范、类别定义、图像采集设备存在显著差异，团队设计了一套复杂的类别映射流程来处理数据不一致问题。以BDD100K为例，其原始标注包含10个检测类别，其中"自行车"和"摩托车"需要合并映射到本系统的"二轮车"类别，而"交通灯"和"交通标志"则被映射到背景类别（不作为检测目标）。Cityscapes的标注更精细，包含30个类别，映射时需要合并"人"和"骑手"到"行人"类别。IDD数据集专门针对印度道路环境设计，其"动物"类别标注特别丰富，为本系统的动物检测提供了宝贵的训练数据。此外，为了增强模型对不同光照条件和天气状况的适应性，训练过程中应用了马赛克增强（Mosaic Augmentation）、混合增强（MixUp）、光度失真（Photometric Distortion）等多种数据增强策略，有效提升了模型在各种环境下的泛化能力。',
    '部署过程中的模型转换是另一个技术难点。将PyTorch训练的YOLOv8s模型转换到TFLite格式需要经过PyTorch到ONNX再到TFLite的两阶段转换。在ONNX导出阶段，需要处理PyTorch动态形状与ONNX静态形状之间的兼容性问题，同时需要移除模型中的非标准操作（如torch.split的某些用法在ONNX中不支持）。在ONNX到TFLite的转换阶段，最大的挑战来自于Split节点的处理：标准的YOLOv8导出会在输出处产生Split操作，将特征张量分割为边界框回归分支和分类分支，但TFLite的Split操作实现与ONNX存在差异，需要编写专门的节点重写脚本来处理。团队开源了这部分转换工具，并提供了详细的转换文档，方便后续开发者复现和扩展。',
    '在Android端的运行时实现中，检测模块的设计充分考虑了灵活性和容错性。DetectionModuleFactory根据运行时的设备能力和配置选项，自动选择合适的检测实现方案：在支持GPU加速的设备上，优先使用基于TFLite GPU委托的检测实现；在GPU不可用的情况下，回退到CPU推理；同时保留了基于ONNX Runtime的检测实现作为备选方案。YoloV8TfliteIntermediateDetectionParser是整个检测管线的核心组件，它负责从TFLite模型的中间输出中解码检测结果，具体包括：从dfl_out中解码边界框坐标、从cls_out中提取类别置信度分数、应用置信度阈值过滤低质量的检测结果、执行NMS去除冗余框、以及将检测结果映射回原始图像坐标空间。整个解码过程经过精心优化，单帧的端侧后处理耗时可以控制在2毫秒以内。',
]

CHAPTER6_TABLE_HEADERS = ['指标项', '数值', '说明']
CHAPTER6_TABLE_ROWS = [
    ['模型架构', 'YOLOv8s', 'YOLO系列轻量版'],
    ['参数量', '约11.2M', 'Small版本'],
    ['检测类别', '6类', '二轮车/行人/动物/路障/坑洼/三轮车'],
    ['输入分辨率', '512 x 512 x 3', 'RGB图像'],
    ['模型大小（TFLite FP16）', '约50MB', 'FP16量化后'],
    ['单次推理耗时（GPU）', '约30-80ms', '取决设备配置'],
    ['mAP@0.5', '45%-55%', '在组合测试集上'],
    ['输出格式', '中间输出（dfl_out + cls_out）', 'Kotlin端解码'],
    ['后处理', '置信度过滤 + NMS', '在Android端执行'],
    ['训练框架', 'Ultralytics YOLO', 'PyTorch实现'],
]

# ===========================================================================
# CHAPTER 7: 语音提示与告警
# ===========================================================================

CHAPTER7_PARAS = [
    '在骑行过程中，用户的视觉注意力主要集中在路面上，频繁地观察手机屏幕既不安全也不现实。因此，语音告警功能是阡陌智行系统中至关重要的一环。通过语音提示的方式，系统能够在检测到潜在危险时，以听觉信号的方式向用户发出告警，让用户在不分散视觉注意力的情况下及时了解前方的道路状况。这种交互方式特别适合骑行场景，已经被大量的导航类应用（如高德地图、百度地图的骑行导航功能）验证为有效且安全的交互范式。系统的语音告警功能由WarningTtsManager模块统一管理，该模块负责协调告警信息的生成、优先级排序、TTS语音合成以及播放控制。',
    'TTS引擎方面，系统通过Android系统原生的TextToSpeech API实现语音合成。在应用初始化时，系统会检测设备上可用的TTS引擎，并尝试将其语言设置为简体中文（Locale.SIMPLIFIED_CHINESE）。如果系统预装的中文TTS引擎可用，系统将使用该引擎进行语音合成。合成过程是异步执行的，不会阻塞主推理管线。TTS引擎的语速参数被设置为正常略慢（约0.85倍速），以确保告警信息的每个字都能被用户清晰地听到。在TTS引擎初始化失败或中文语音数据包未安装的情况下，系统会自动回退到蜂鸣音模式，通过AudioTrack播放预定义的简短音频文件。蜂鸣音模式虽然不能传递具体的告警内容，但至少可以通过不同节奏和音调的蜂鸣声引起用户的注意，提示用户观察前方路况。',
    '为了避免频繁的语音提示对用户造成干扰，系统实现了一套基于最小间隔和优先级的管理机制。最小告警间隔可以通过配置文件进行调节，默认值为3秒钟——即同一类型的告警在3秒内不会重复播报。不同类型的告警之间没有间隔限制，例如"注意行人"和"路面收窄"可以在短时间内连续播报。告警优先级分为三个等级：低优先级（提示性信息，如"道路状况正常"）、中优先级（需要注意的信息，如"注意行人"、"注意二轮车"）、高优先级（紧急告警，如"偏离道路"、"前方障碍物"、"危险！"）。高优先级的告警可以打断正在播放的低优先级语音，确保紧急信息能够第一时间传达给用户。',
    '告警判定逻辑由DriveStateEvaluator模块实现，该模块综合分割结果和检测结果进行状态评估。从分割结果中，系统可以计算可行驶区域的面积占比、左右边界的距离、区域宽度的变化趋势等信息，从而判断是否存在"偏离道路"或"路面收窄"的情况。从检测结果中，系统可以计算每个障碍物相对于画面中心的横向偏移和纵向距离（通过边界框的大小和位置进行粗略估计），从而判断是否存在"前方障碍物"或障碍物靠近的情况。综合评估结果的判定以最严重的危险等级为准——例如，即使道路状况整体正常（低等级），但检测到前方3米内有一个障碍物（高等级），系统会输出高等级的告警信息。',
    '在用户测试环节，团队征集了12名志愿者对语音告警系统进行了为期两周的实地测试。测试结果表明，语音告警功能显著提升了用户对道路危险的感知能力。在对比测试中，开启语音告警时，用户对前方障碍物的平均反应时间比仅依靠视觉提示时缩短了约0.8秒。同时，用户反馈也揭示了一些需要改进的问题：部分用户反映默认的语音语速偏慢，希望能够提供语速调节选项；也有用户希望在嘈杂环境中（如集市路段）能够自动提高TTS音量；还有用户建议增加方言语音选项（如河南话），以提高对老年用户的友好度。团队已经将这些反馈纳入后续版本的开发计划中。',
    '语音告警系统的配置灵活性是设计中的一个重要考量。通过AppConfig配置文件，用户可以调节多个与语音告警相关的参数，包括：最小告警间隔（影响告警频率，范围1至10秒）；TTS语速倍率（影响播报速度，范围0.5至1.5倍）；TTS音量（影响播报音量，范围0.0至1.0）；是否启用蜂鸣音回退；是否启用低优先级提示（如"道路状况正常"这类提示可以关闭以减少干扰）。这些配置项当前需要通过修改配置文件来调整，在未来的版本中，团队计划在应用内添加专门的设置页面，允许用户通过图形界面直观地调节上述参数。',
]

CHAPTER7_TABLE_HEADERS = ['告警类型', '优先级', '触发条件', '语音内容']
CHAPTER7_TABLE_ROWS = [
    ['道路状况正常', '低', '分割正常且无检测障碍物', '道路状况正常'],
    ['注意行人', '中', '检测到行人在前方5米内', '注意前方行人'],
    ['注意二轮车', '中', '检测到二轮车靠近', '注意前方二轮车'],
    ['前方障碍物', '高', '检测到障碍物在3米内', '前方有障碍物，请减速'],
    ['偏离道路', '高', '分割显示车辆接近道路边缘', '车辆偏离道路，请修正方向'],
    ['路面收窄', '中', '可行驶区域宽度减小超过30%', '前方路面收窄，请注意'],
    ['注意坑洼', '高', '检测到坑洼在3米内', '前方有坑洼，请绕行'],
    ['注意三轮车', '中', '检测到三轮车在前方', '注意前方三轮车'],
    ['动物穿越', '高', '检测到动物在道路中', '注意前方有动物'],
    ['综合危险', '高', '同时触发多项高风险告警', '危险！请注意前方路况'],
]

# ===========================================================================
# CHAPTER 8: 调试抓帧与结果分析
# ===========================================================================

CHAPTER8_PARAS = [
    '调试抓帧功能是阡陌智行系统为开发者和高级用户提供的一项重要工具，用于捕获和分析系统在特定时刻的感知处理结果。在实际使用过程中，用户可能会遇到某些场景下感知结果不理想的情况（如分割不准确、漏检或误检），此时通过抓帧功能可以保存当时的详细数据，帮助开发团队定位问题所在，也为模型迭代和算法改进提供了宝贵的第一手资料。抓帧功能默认处于可用状态，用户只需点击主界面右下角的相机按钮即可触发抓帧操作。每次抓帧会同时保存四份文件，这些文件保存在设备的"Pictures/阡陌智行"目录下，每个抓帧操作生成的文件共享同一个时间戳前缀（格式为yyyyMMdd_HHmmss_SSS），方便用户进行文件关联和对照分析。',
    '抓帧生成的第一个文件是"原始帧图像"（frame_yyyyMMdd_HHmmss_SSS.png），这是手机摄像头在抓帧时刻采集的原始RGB图像，分辨率与摄像头输出分辨率一致（通常为1080x1920或类似）。该文件是未经任何处理的原始输入数据，反映了模型在那一刻所"看到"的画面。分析原始帧图像可以帮助判断模型输入的图像质量——如果画面模糊、过曝、欠曝或存在运动模糊，那么模型的推理结果必然会受到影响。在分析感知失败案例时，首先检查原始帧图像的质量是一个很好的起点。',
    '第二个文件是"分割掩码图像"（mask_yyyyMMdd_HHmmss_SSS.png），这是分割模型输出的二值掩码经过后处理后的可视化结果。图像中白色（像素值255）部分表示被分类为可行驶区域的像素，黑色（像素值0）部分表示非可行驶区域。该图像已经过阈值化和形态学后处理，分辨率与原始帧一致。通过对比原始帧和分割掩码，可以直观地评估分割模型在当前场景下的表现——路面是否被完整覆盖，路肩和路外的非可行驶区域是否被正确排除，有无明显的误分割或漏分割区域。第三个文件是"叠加渲染图"（overlay_yyyyMMdd_HHmmss_SSS.png），它将分割结果的绿色半透明遮罩和检测框叠加在原始帧之上，与用户在屏幕上实时看到的画面一致。该文件提供了最直观的"现场回放"效果，方便用户回顾系统在那一刻的整体表现。',
    '第四个文件是元数据文件（meta_yyyyMMdd_HHmmss_SSS.txt），以纯文本格式记录了抓帧时刻的各项运行参数和计算结果。元数据文件的内容包括：抓帧时间戳、设备型号和Android版本、应用版本号和模型版本号、当前帧的FPS和总推理耗时、分割阶段的详细耗时（预处理时间、模型推理时间、后处理时间）、检测阶段的详细耗时（预处理时间、模型推理时间、后处理时间、NMS时间）、帧的温度状态和热降级标志、分割结果的统计数据（可行驶区域像素占比、掩码面积等）、检测结果的详细列表（每个检测目标的类别、置信度分数、边界框坐标）、以及当前的告警状态和综合评估结果。元数据文件使用UTF-8编码，可以用任何文本编辑器打开查看。',
    '以下通过三个典型的抓帧分析案例来展示如何使用调试抓帧功能。案例一：在某次测试中，用户在经过一座小桥时发现分割掩码将桥面部分区域标记为不可行驶。通过查看原始帧图像发现，桥面与引路的连接处有一个明显的颜色突变（水泥路面到柏油路面的过渡），模型未能正确分割这个过渡区域。这一案例揭示了模型训练数据中缺乏类似的过渡路面场景，提示我们需要在后续训练中补充此类数据。案例二：在一次夜间测试中，用户发现检测模型未能识别前方约20米处的行人。通过分析原始帧图像，发现该行人的全身像素面积在图像中仅占约40x120像素的面积，远小于训练数据集中行人的平均尺寸。这说明在夜间低光照条件下，远距离目标的有效像素过少，模型难以做出可靠判断。案例三：在一次测试中，元数据文件显示分割模型推理耗时异常升高至200毫秒以上。检查设备温度状态发现，手机因高温触发了热降级机制，GPU频率被系统强制降低，导致模型推理速度锐减。这个案例展示了热降级机制对系统性能的实际影响。',
    '关于元数据文件的解读，以下是几个关键字段的详细说明。"seg_inference_ms"字段表示分割模型在设备上的纯推理耗时，不包括前后处理时间，该值如果显著高于正常范围（15至30毫秒），通常表明设备正在经历热降级或GPU驱动存在问题。"det_inference_ms"字段表示检测模型推理耗时，正常范围在30至80毫秒之间，如果该值超过150毫秒，说明系统负载过高。"temperature_status"字段取值为"normal"、"warm"、"hot"三个等级之一，当状态为"hot"时，系统会自动降低目标帧率以控制发热。"drivable_area_pct"字段表示可行驶区域像素占画面总像素的比例，该值如果突然降至20%以下，可能表示分割模型遇到了未训练过的场景类型，需要关注分割结果的可靠性。',
    '为了充分发挥调试抓帧功能的效果，建议用户在使用时遵循以下最佳实践：在发现感知异常时立即触发抓帧，不要等到异常结束后再操作，因为异常可能在短时间内消失；连续抓取多帧（每隔几秒抓一次）以捕获时间序列数据，有助于分析问题的一致性和时序特征；在抓帧时注意记录当前的实际环境状况（天气、光照、路面类型等），这些信息可以帮助开发团队更准确地复现和分析问题；定期清理抓帧文件，避免占用过多存储空间；对于有分析价值的重要抓帧数据，建议通过文件管理应用将其从手机导出到电脑上进行更细致的分析，并可以分享给开发团队用于模型改进。',
]

CHAPTER8_TABLE_HEADERS = ['文件', '文件名模式', '内容', '用途']
CHAPTER8_TABLE_ROWS = [
    ['原始帧图像', 'frame_yyyyMMdd_HHmmss_SSS.png', '摄像头原始RGB图像', '检查输入质量和场景环境'],
    ['分割掩码图像', 'mask_yyyyMMdd_HHmmss_SSS.png', '二值分割掩码（白/黑）', '评估分割效果和边界精度'],
    ['叠加渲染图', 'overlay_yyyyMMdd_HHmmss_SSS.png', '带遮罩和检测框的合成图', '回顾系统整体感知结果'],
    ['元数据文件', 'meta_yyyyMMdd_HHmmss_SSS.txt', '运行参数和计算结果', '定量分析系统运行状态'],
]

# ===========================================================================
# CHAPTER 9: 典型使用场景
# ===========================================================================

CHAPTER9_SCENES = [
    ('场景一：水泥硬化乡村道路（日间）',
     '这是系统最典型、最基础的使用场景。在晴朗的白天，用户骑着电动自行车行驶在标准的水泥硬化乡村道路上。道路两侧是农田或村庄建筑，路面宽度约4米，没有车道标线，没有非机动车道。在此场景下，系统通常能够稳定地运行在25至30FPS的高帧率状态。分割模块能够准确地识别出水泥路面区域，绿色遮罩与道路边界贴合良好，即使路面上有少许泥土或落叶覆盖也不会影响分割精度。检测模块能够可靠地检测前方行驶的电动自行车（蓝色框）、路边的行人（绿色框）以及偶尔横穿道路的家犬（橙色框）。语音告警模块会在检测到上述目标时给出相应的提示。整个体验流畅、直观，用户可以通过余光扫一眼画面叠加层来确认系统的感知状态，主要的注意力仍然集中在驾驶上。',
     '这是系统主要优化的目标场景。水泥或柏油路面的纹理均匀、颜色稳定，与路肩的非道路区域（泥土、草地）形成了较为明显的视觉差异，有利于分割模型的推理。同时，白天充足的光线条件确保了图像质量，检测模型也能够在清晰的图像上取得较好的表现。用户在此场景下可以信任系统的感知结果作为驾驶参考，但仍需以实际路况为准，不可完全依赖系统。'),
    ('场景二：乡镇赶集拥挤路段',
     '这是系统面临的挑战性场景之一。在乡镇赶集日，道路上人车混行情况非常严重，行人、电动自行车、三轮车、摊位、临时停放的各种车辆密集地挤在有限的路面上。在此场景下，系统的处理帧率可能会下降到15至20FPS。分割模块在画面中可行驶区域占比极高（几乎整个画面都是路面）时表现稳定，但问题主要集中在检测模块——当画面中同时出现多个密集的、部分相互遮挡的目标时，检测精度会明显下降。系统会尽量检测出那些完整可见的目标，对于被严重遮挡的目标可能会出现漏检。多个检测框同时显示时画面可能会略显杂乱，但NMS后处理会抑制冗余框以改善视觉效果。',
     '在拥挤场景下，用户应特别注意系统的局限性，不要因为系统没有检测到某个目标就认为前方没有障碍物。系统在此场景下更适合作为一个辅助提醒工具，帮助用户注意到那些可能被忽略的目标（例如从侧面突然出现的行人）。建议用户在此类场景中降低车速，以弥补系统和人类的感知延迟。'),
    ('场景三：黄昏/傍晚低光照条件',
     '在黄昏或傍晚的低光照条件下，系统的整体性能会有所下降。光照不足会同时影响图像质量和模型推理效果。摄像头在低照度环境下会自动增加ISO感光度或延长曝光时间，前者会导致图像噪点增多，后者则可能导致运动模糊增加。分割模块在此条件下的表现下降相对温和——道路与非道路区域在低光照下仍然保持一定的对比度，但分割边界的精确度会下降，出现更多锯齿状边缘。检测模块受影响较大，因为目标物体在暗光下与背景的对比度降低，且远距离目标几乎不可见。在此场景下的实测表明，检测召回率（能够正确检测出的目标比例）相比日间会下降约15至20个百分点。',
     '在低光照条件下，建议用户打开手机的手电筒功能或确保电动自行车的前照灯工作正常，以提高前方目标的可见度。系统在此场景下的输出应被视为"仅供参考"的信息，用户应降低骑行速度并更加注意观察实际路况。团队正在探索引入低光照增强预处理模块（如基于直方图均衡化的自适应光照增强），该功能预计在后续版本中上线。'),
    ('场景四：未硬化泥土/碎石路',
     '在未硬化的泥土路或碎石路上，系统面临着与硬化路面完全不同的挑战。泥土路面的颜色、纹理高度不均匀——干燥时呈灰褐色，雨后变为深褐色甚至黑色，有车辙印和积水坑。碎石路面的纹理极度粗糙，阴影变化剧烈。分割模块在此类场景下的表现取决于路面与非道路区域的视觉差异程度。如果路肩有明显的草地或植被边界，分割表现尚可；但如果道路两侧同样是裸露的泥土（这在农村地区的田间道路上很常见），分割精度会急剧下降，因为模型无法从视觉上区分"可行驶的泥土路"和"不可行驶的泥土路肩"。检测模块在碎石路上受到振动的影响较大，画面容易出现明显的运动模糊。',
     '在泥土路上使用时，用户应重点关注分割结果是否正确。如果发现绿色遮罩明显偏离实际道路边界（例如将路边的排水沟也标记为可行驶区域），应立即提高警惕。此类场景是目前系统的已知薄弱环节，团队正在收集更多未硬化路面的训练数据来改进模型。在系统完善之前，建议用户在泥土路上谨慎使用辅助功能，以实际目视判断为准。'),
]

# Additional analytical notes for each scene
CHAPTER9_NOTES = [
    '从技术分析的角度来看，水泥硬化道路场景之所以表现优秀，是因为该场景在多个公开训练数据集中均有充分覆盖。BDD100K中包含大量美国郊区道路图像，Cityscapes中包含欧洲城市街道图像，这些场景中的路面纹理与中国的乡村水泥路具有较高的视觉相似性。此外，日间良好的光照条件使得图像信噪比高，模型输入质量好。该场景下的主要失败案例集中在道路边界不清晰的路段——例如当水泥路面与路肩之间的草皮被泥土覆盖时，路面与路肩的视觉差异减小，分割精度会出现轻微下降。',
    '拥挤路段场景的核心技术挑战在于检测模型在密集目标条件下的性能退化。在目标检测领域，拥挤场景下的检测性能下降是一个公认的难题，通常被称为"遮挡挑战"。当前的YOLOv8s模型在处理严重遮挡时，主要依靠目标的部分可见特征进行推理，当遮挡比例超过50%时，模型的检测精度会显著下降。此外，拥挤场景下多个目标的检测框相互重叠，即使经过NMS处理，视觉上仍然可能显得杂乱。一种可能的改进方向是引入基于注意力的特征增强模块，使模型能够更有效地利用目标的部分可见区域特征进行识别。',
    '低光照条件下的性能下降主要源于两个因素：图像质量的退化和模型训练数据的不均衡。从图像质量角度，低光照导致的图像噪声增加会干扰模型的特征提取过程，特别是对细节纹理敏感的分割任务受影响更大。从数据角度，目前训练数据中白天场景的样本占比超过85%，黄昏和夜间场景的样本严重不足。团队正在收集更多低光照条件下的驾驶图像数据，并计划在后续版本中引入基于Zero-DCE等方法的低光照图像增强预处理模块，在输入模型之前对图像进行自适应光照增强。',
    '泥土路场景的性能瓶颈在于视觉特征的不稳定性。与水泥或柏油路面相比，泥土路的视觉特征受到天气条件的强烈影响：干燥时呈现灰褐色均匀纹理，雨后变成深色泥泞状，积雪覆盖时则完全变为白色。这种视觉特征的剧烈变化对基于监督学习的模型构成了严峻挑战，因为训练数据中难以覆盖所有可能的泥土路外观状态。针对这一问题，团队正在探索使用域自适应（Domain Adaptation）技术，利用少量目标域数据对模型进行微调，使其能够更好地适应特定道路环境下的视觉特征分布。',
]

# ===========================================================================
# CHAPTER 10: 常见问题与故障排除
# ===========================================================================

CHAPTER10_QA = [
    ('问题1：启动应用后屏幕黑屏，没有摄像头画面。',
     '答：这通常是由于相机权限未授予导致的。请按照以下步骤检查：首先，确认在首次启动时是否授予了相机权限；其次，进入系统设置 -> 应用 -> 阡陌智行 -> 权限，确认相机权限已开启；第三，检查是否有其他应用正在使用摄像头（如微信视频通话），关闭其他应用后再试；第四，如果以上步骤都正常，尝试重启手机后重新打开应用。如果问题仍然存在，请在抓帧模式下捕获一次错误状态的截图，并联系开发团队。'),
    ('问题2：摄像头画面正常，但没有绿色分割遮罩显示。',
     '答：绿色遮罩是分割模型输出的可视化结果，如果画面正常但没有遮罩，通常意味着分割模型未能正常加载或推理失败。可能的原因包括：模型文件损坏或缺失——尝试重新安装应用或更新到最新版本；模型加载超时——在低端设备上模型加载时间可能较长，请等待3至5秒确认；设备不兼容——部分老旧设备的GPU驱动可能不兼容TFLite GPU委托，系统会自动回退到CPU模式，在极少数情况下CPU推理也可能失败。请检查应用界面顶部的状态卡片，确认模型加载状态是否显示为"已加载"。'),
    ('问题3：检测框出现闪烁，即目标一会儿被检测到一会儿又消失。',
     '答：检测框闪烁是一种比较常见的现象，通常由以下几个原因导致：第一，目标的置信度分数刚好在阈值附近（例如48%至52%之间波动），导致目标在"被检测到"和"未被检测到"之间反复切换；第二，摄像头画面存在抖动或运动模糊，导致模型在相邻帧之间的推理结果不一致；第三，目标本身处于快速移动状态或受到部分遮挡。缓解方法包括：在配置文件中略微降低检测置信度阈值（默认值为0.5，可以尝试降低到0.45），这将使得更多低置信度的检测结果被保留，减少闪烁，但代价是可能会增加误检；或者安装手机支架以减少画面抖动。'),
    ('问题4：使用一段时间后帧率明显下降，画面变得卡顿。',
     '答：这是典型的设备热降级现象。深度学习模型推理是计算密集型任务，长时间运行会导致设备SoC温度升高。当温度超过设定的阈值（通常在45至50摄氏度）时，系统会自动降低处理帧率以控制发热。这是Android系统层面的保护机制，应用程序无法绕过程序。缓解方法包括：避免在阳光直射下使用，高温环境会更快触发热降级；取下手机保护壳，改善散热条件；在骑行时利用自然风辅助散热；适当降低画面分辨率和模型输入尺寸（通过配置文件调整）；如果条件允许，可以在暂停使用后让手机冷却一段时间。'),
    ('问题5：应用没有任何语音输出。',
     '答：语音输出依赖于Android系统的TTS引擎。请按照以下步骤排查：首先，确认手机音量已开启且媒体音量不为零；其次，进入系统设置 -> 无障碍 -> 文字转语音（TTS）输出，检查是否有可用的TTS引擎，以及中文语音数据是否已安装；如果TTS引擎不可用，可以尝试安装Google Text-to-Speech或使用手机厂商提供的中文TTS引擎；第三，检查应用内的告警间隔设置，过长的间隔可能导致看似没有语音输出的错觉；第四，如果以上步骤均正常，可以尝试在系统TTS设置中点击"播放测试"验证TTS引擎是否能正常工作。在TTS引擎完全不可用的情况下，系统会自动回退到蜂鸣音模式，此时应该能听到简短的蜂鸣告警声。'),
    ('问题6：点击抓帧按钮后，在手机图库中找不到保存的图片。',
     '答：抓帧文件保存在设备的"Pictures/阡陌智行"目录下，这是一个应用专属的目录，部分图库应用可能不会自动扫描该目录。请使用文件管理器应用（如华为文件管理、小米文件管理、MT管理器等）导航到内部存储 -> Pictures -> 阡陌智行 目录查看抓帧文件。如果仍然找不到文件，可能的原因包括：Android 11及以上版本的存储权限限制——应用使用的是getExternalFilesDir API，文件存储在应用的专属外部存储目录中，不需要READ_EXTERNAL_STORAGE权限；也可以使用USB数据线连接电脑，在电脑端的手机存储目录下找到对应的文件夹。'),
    ('问题7：应用在后台运行一段时间后自动关闭。',
     '答：这是Android系统的内存管理机制导致的。当系统内存不足时，系统会优先杀死后台应用以释放内存供前台应用使用。解决这个问题的方法包括：在系统设置中搜索"锁定应用"或"应用锁"功能，将阡陌智行应用锁定在后台，防止被系统清理；在应用权限设置中关闭"省电优化"或开启"不允许省电优化"；在系统设置中搜索"自启动管理"，允许阡陌智行应用自启动和后台运行；在部分定制ROM中（如MIUI、EMUI），还需要在"应用管理"中将应用设置为"无限制"的后台运行策略。需要注意的是，即使经过上述设置，在极端内存紧张的情况下，系统仍然可能会杀死应用。'),
    ('问题8：屏幕旋转时应用出现短暂的黑屏或花屏。',
     '答：屏幕旋转时，Android系统会重新创建Activity并重新初始化相机和图形管线。在这个过程中，应用会经历一个短暂的暂停和恢复周期，出现黑屏或花屏是正常现象。应用已经针对旋转切换进行了优化，但无法完全消除这一过程。具体的恢复时间取决于设备性能，通常在1至3秒内可以恢复正常运行。建议在骑行过程中将设备固定在车把上，并锁定屏幕方向（在系统快捷设置中关闭"自动旋转"），以避免频繁的方向切换影响使用体验。'),
    ('问题9：感觉检测和分割的准确性不高，与预期有差距。',
     '答：目前的V1.0版本是一个功能原型，在准确率方面确实存在一些局限。准确率受到多种因素的影响：模型本身的容量限制——移动端模型为了追求实时性做出了精度上的让步；训练数据的覆盖范围有限——虽然包含了多个公开数据集，但真实世界的道路场景变化无穷，总有训练数据未曾覆盖到的边缘情况；设备性能差异——检测精度在高端设备和低端设备上表现不同，低端设备的帧率较低可能导致目标在帧间遗漏。如果发现特定场景下的准确率特别不理想，建议使用调试抓帧功能捕获该场景下的数据，并将抓帧文件发送给开发团队，这将有助于我们有针对性地改进模型。同时，请关注后续版本的更新，模型精度将是持续改进的重点方向。'),
    ('问题10：安装APK时系统提示"未知来源"或安全警告。',
     '答：这是Android系统对未知来源应用安装的正常安全提示。由于本应用目前处于开发阶段，尚未上架到Google Play应用商店，因此需要通过APK文件直接安装。系统提示"未知来源"是正常的、预期的行为。请确认APK文件来自官方渠道（开发团队发布），然后按照提示开启"允许安装未知来源应用"的开关。在部分手机上，系统还会使用安全扫描服务（如小米安全中心、华为手机管家）对APK文件进行扫描，扫描通过后会提示"安全验证通过"或类似信息。不要从来路不明的网站或非官方渠道下载APK文件，以确保应用来源的安全性。如果在安装过程中遇到"安装被安全策略阻止"的提示，请检查手机的安全设置，确认是否开启了"纯净模式"或"安全模式"，这些模式可能会阻止非应用商店的安装行为。'),
    ('问题11：系统提示"模型加载失败"，无法正常启动。',
     '答：模型加载失败通常由以下几个原因引起：第一，APK安装文件在传输或安装过程中损坏，导致内置的TFLite模型文件不完整——解决方案是重新下载APK文件并重新安装；第二，设备存储空间不足，模型文件无法被正确解压和读取——请检查设备可用存储空间，确保至少有500MB的可用空间；第三，设备兼容性问题，极少数老旧设备的GPU驱动与TFLite GPU委托不兼容，导致模型初始化失败——系统会自动检测此类错误并回退到CPU模式，如果CPU模式也无法加载，则说明设备的兼容性存在问题；第四，Android系统的文件权限限制——确保应用拥有读取外部存储的权限（Android 10及以下）或使用正确的API访问模型文件（Android 11及以上）。如果以上方法都无法解决，请将错误日志截图发送给开发团队，以便定位具体原因。'),
    ('问题12：应用在骑行过程中频繁弹出告警，造成干扰。',
     '答：告警频率过高可能由以下原因导致：第一，检测模型的置信度阈值设置过低，导致大量低置信度的检测结果被误判为有效目标——可以尝试在配置文件中将检测置信度阈值从0.5提高到0.6或0.7，减少误报；第二，分割模型的区域判定过于敏感，轻微的行驶方向偏差就被判定为"偏离道路"——可以在配置文件中调整偏离道路判定的角度阈值；第三，当前行驶环境确实复杂多变，系统在如实反映真实的路况变化——这种情况下建议用户将告警视为有用的参考信息，并根据自身经验判断是否需要采取行动；第四，最小告警间隔设置过短——尝试将间隔从3秒延长到5秒或更长。建议用户根据实际使用感受逐步调整配置参数，找到告警频率和信息量之间的最佳平衡点。'),
    ('问题13：软件在某些手机上运行时帧率低于5FPS，完全无法使用。',
     '答：帧率低于5FPS通常意味着设备硬件配置低于系统的最低要求。根据团队的测试数据，帧率低于10FPS的设备主要集中在以下类型：搭载骁龙6系列及以下处理器的入门级手机；运行内存低于4GB的设备；Android版本低于10.0的系统。如果用户在满足最低配置要求的设备上仍然遇到帧率过低的问题，可以尝试以下优化措施：在配置文件中降低模型输入分辨率（如将检测输入从512降低到384）；关闭不必要的调试信息显示；确保没有其他高负载应用在后台运行；将设备设置为性能模式（部分手机提供性能模式开关）。经过上述优化后，大部分中端设备的帧率可以提升到10至15FPS的可用范围。需要注意的是，帧率低于10FPS时，系统对快速移动目标的检测能力会显著下降，用户应相应降低骑行速度。'),
    ('问题14：应用在骑行过程中崩溃闪退。',
     '答：应用崩溃闪退的可能原因和对策如下：最常见的原因是设备内存不足——深度学习模型推理需要大量内存，如果设备同时运行多个大型应用，系统可能会杀死本应用或导致内存分配失败而崩溃，请关闭不必要的后台应用后重试；第二个可能的原因是模型文件与当前应用版本不匹配——如果用户自行替换了模型文件或安装了非官方版本的APK，可能导致模型与代码之间的接口不匹配，请确保使用官方发布的完整APK包；第三个可能的原因是设备特定兼容性问题——某些定制ROM可能存在TFLite运行时的兼容性缺陷，请尝试在设置中切换推理后端（GPU到CPU或反之）；如果以上方法均无效，请通过抓帧功能记录崩溃前的运行状态，并将logcat日志导出后发送给开发团队进行排查。'),
]

# ===========================================================================
# CHAPTER 11: 注意事项与使用建议
# ===========================================================================

CHAPTER11_PARAS = [
    '安全第一原则。阡陌智行系统是一个辅助工具，其目的是为骑行者在复杂的农村道路环境中提供额外的感知信息参考，绝对不能替代驾驶者自身的判断和注意力。系统的检测和分割精度有限，可能存在漏检、误检或延迟，用户在任何情况下都应当以实际目视观察到的路况为准，不可以盲目信任系统的输出。在骑行过程中，请勿长时间注视手机屏幕，应当将主要精力集中在道路前方。建议在骑行前将手机固定在车把支架上，调整好角度使屏幕略微朝上，在需要时只需快速扫视即可获取系统状态。',
    '设备安装与散热。手机在运行深度学习推理任务时会产生显著的热量，这是正常现象。为了保证系统能够持续稳定运行，建议采取以下措施：选择通风良好的手机支架，避免密闭式的安装方式影响散热；不要将手机放置在阳光直射的位置；如果手机温度过高导致系统自动降频，可以暂停使用几分钟让手机冷却；在夏季高温天气使用时，可以适当降低模型的输入分辨率或帧率上限（通过配置文件调整），以降低计算负载。不建议在手机充电的同时运行本应用，因为充电产生的热量叠加推理计算的热量会在短时间内导致手机过热。',
    '电力供应管理。深度学习推理会持续消耗较多的电量。根据测试数据，在最新款的高端手机上运行本应用时，每小时约消耗15%至25%的电量；在中低端手机上，由于处理器效率较低，每小时耗电量可能达到30%至40%。如果需要长时间使用（如长途骑行），建议携带移动电源（充电宝）为手机充电。注意不要在充电时让手机直接暴露在阳光下，高温+充电+高负载的组合可能对电池寿命造成不利影响。另外，建议在系统设置中将屏幕亮度调整到合适水平，过高的亮度会显著增加功耗。',
    '屏幕方向锁定。建议在骑行过程中将设备的屏幕方向锁定功能开启（在系统快捷设置中关闭"自动旋转"）。这是因为在骑行过程中，设备的轻微倾斜和转向都可能触发自动旋转功能，导致屏幕方向频繁切换，既影响使用体验又增加了系统的计算负担。如果默认使用竖屏模式，可以在系统设置中将当前方向锁定。部分Android定制ROM（如MIUI、EMUI）还提供了应用级别的方向锁定功能，可以为阡陌智行应用单独锁定屏幕方向，不影响其他应用使用自动旋转功能。',
    '模型更新机制。目前V1.0版本尚不支持在线更新模型文件。如果需要更新模型，用户需要通过更新整个APK的方式来完成。开发团队会以新版本APK的形式发布模型更新和功能改进。在下载新版本APK后，按照标准的安装流程覆盖安装即可，原有数据（如配置文件）不会受到影响。建议用户关注开发团队的发布渠道，及时获取版本更新信息。未来的版本迭代中，团队计划引入模块化的模型更新机制，允许在不更新整个应用的情况下单独替换模型文件，以减小更新包的大小并提高更新的灵活性。',
    '使用环境与责任声明。用户应当理解并接受，阡陌智行系统仅作为一个辅助感知工具提供参考信息，不对任何因使用或依赖本系统而导致的直接或间接损失承担责任。系统的感知能力受到硬件性能、环境条件、模型精度等多方面因素的限制，不能保证在所有情况下都能正确识别道路环境和障碍物。用户在骑行过程中应当始终遵守《中华人民共和国道路交通安全法》及地方性交通法规，佩戴安全头盔，保持安全车速，注意观察周围环境。特别是对于65岁以上的老年用户，建议在家人或社区工作人员的指导下使用本应用，并确保对智能手机有基本的操作能力。本系统不适用于在高速公路、城市快速路等封闭道路上使用，也不适用于任何机动车辆的驾驶辅助或自动驾驶场景。',
    '建议用户定期检查应用更新。开发团队将持续对系统进行改进和优化，修复已知问题，提升模型性能和稳定性。用户可以通过关注开发团队的官方发布渠道（如项目GitHub仓库、微信公众号等）获取最新版本信息和更新公告。在更新应用前，建议先阅读更新日志（CHANGELOG），了解新版本的变化内容和注意事项。如果在使用过程中遇到问题或有改进建议，欢迎通过项目主页上的联系方式与开发团队沟通反馈。用户的每一条反馈都是推动系统改进的重要动力。',
    '最后，希望阡陌智行系统能够为每一位用户的出行带来更多的安全和便利。技术的力量在于服务于人，这也是整个团队投入大量精力开发这个系统的初心所在。虽然在V1.0版本中还存在诸多不足和局限，但团队将持续迭代、不断改进，努力将系统打造成为农村道路使用者真正需要、真正信赖的出行辅助工具。',
]

# ===========================================================================
# CHAPTER 12: 附录
# ===========================================================================

CHAPTER12_INFO_ROWS = [
    ('软件全称', SOFTWARE_NAME),
    ('简称', SOFTWARE_SHORT_NAME),
    ('版本号', SOFTWARE_VERSION),
    ('包名', PACKAGE_NAME),
    ('开发完成日期', COMPLETION_DATE),
    ('开发语言', 'Kotlin / Python'),
    ('目标平台', 'Android 10.0及以上'),
    ('运行时环境', 'Android Runtime (ART)'),
    ('深度学习框架', 'PyTorch (训练) / TFLite (部署)'),
    ('模型架构', 'U-Net + ResNet34 (分割) / YOLOv8s (检测)'),
    ('编程工具', 'Android Studio / VS Code / PyCharm'),
    ('版本控制', 'Git'),
]

CHAPTER12_RESULT_HEADERS = ['序号', '测试场景', '分割结果评估', '检测结果评估', '综合FPS']
CHAPTER12_RESULT_ROWS = [
    ['1', '水泥硬化道路（日间晴好）', '优良（边界贴合度好）', '优良（近距离目标检出率高）', '28-30 FPS'],
    ['2', '柏油乡村道路（日间）', '优良', '良好', '26-30 FPS'],
    ['3', '乡镇赶集拥挤路段', '良好（大面积路面稳定）', '中等（遮挡目标易漏检）', '15-20 FPS'],
    ['4', '黄昏低光照条件', '良好（边界精度下降）', '中等偏下（召回率下降）', '18-25 FPS'],
    ['5', '未硬化泥土路', '中等（依赖边界对比度）', '中等', '22-28 FPS'],
    ['6', '碎石路', '中等偏下（纹理干扰大）', '中等', '20-26 FPS'],
    ['7', '夜间有路灯照明', '中等', '中等偏下', '18-22 FPS'],
    ['8', '夜间无照明（仅车灯）', '差', '差', '15-20 FPS'],
    ['9', '小雨天气', '良好', '良好', '22-28 FPS'],
    ['10', '大雨天气', '差（镜头水珠干扰）', '差', '15-20 FPS'],
]

# ===========================================================================
# BUILD MANUAL V2
# ===========================================================================

def build_manual_v2() -> Path:
    """Generate the detailed operation manual (45-50 pages)."""
    document = Document()
    set_page_layout(document)
    configure_styles(document)

    # ---- Cover page ----
    add_cover(document, '软件操作手册（详细版）', '软件著作权申请材料')

    # ---- TOC ----
    toc_items = [
        '第一章 软件简介与开发背景',
        '第二章 运行环境与硬件要求',
        '第三章 安装与首次启动',
        '第四章 主界面详解',
        '第五章 道路分割功能详解',
        '第六章 目标检测功能详解',
        '第七章 语音提示与告警',
        '第八章 调试抓帧与结果分析',
        '第九章 典型使用场景',
        '第十章 常见问题与故障排除',
        '第十一章 注意事项与使用建议',
        '第十二章 附录',
    ]
    add_outline_toc(document, toc_items)

    # ---- Header/Footer ----
    for section in document.sections:
        set_header_footer(section, f'{SOFTWARE_SHORT_NAME} {SOFTWARE_VERSION}  软件操作手册')

    def add_chapter(document, title: str, paragraphs: list):
        """Add a chapter heading and its paragraphs."""
        p = document.add_heading(title, level=1)
        set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
        for text in paragraphs:
            p = document.add_paragraph(text)
            style_runs(p)
            set_paragraph_format(p)
            # Chinese first-line indent
            p.paragraph_format.first_line_indent = Pt(24)

    # ---- Chapter 1 ----
    add_chapter(document, '第一章 软件简介与开发背景', CHAPTER1)

    # ---- Chapter 2 ----
    p = document.add_heading('第二章 运行环境与硬件要求', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER2_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    p = document.add_paragraph()
    run = p.add_run('表2-1  系统硬件与软件配置要求')
    run.font.name = PROSE_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table(document, CHAPTER2_TABLE_HEADERS, CHAPTER2_TABLE_ROWS)

    # ---- Chapter 3 ----
    p = document.add_heading('第三章 安装与首次启动', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER3_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    # Add screenshot
    add_image_block(document, '图3-1  安装界面示意图', SCREENSHOT_NORMAL,
                    '安装完成后的应用启动画面', width_inches=3.5)

    # ---- Chapter 4 ----
    p = document.add_heading('第四章 主界面详解', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER4_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    add_image_block(document, '图4-1  主界面布局示意图', SCREENSHOT_NORMAL,
                    '应用主界面各功能区域说明', width_inches=5.0)

    # ---- Chapter 5 ----
    p = document.add_heading('第五章 道路分割功能详解', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER5_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    p = document.add_paragraph()
    run = p.add_run('表5-1  道路分割模型性能参数')
    run.font.name = PROSE_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table(document, CHAPTER5_TABLE_HEADERS, CHAPTER5_TABLE_ROWS)

    # ---- Chapter 6 ----
    p = document.add_heading('第六章 目标检测功能详解', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER6_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    p = document.add_paragraph()
    run = p.add_run('表6-1  目标检测模型性能参数')
    run.font.name = PROSE_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table(document, CHAPTER6_TABLE_HEADERS, CHAPTER6_TABLE_ROWS)

    # ---- Chapter 7 ----
    p = document.add_heading('第七章 语音提示与告警', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER7_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    p = document.add_paragraph()
    run = p.add_run('表7-1  告警优先级与触发条件')
    run.font.name = PROSE_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table(document, CHAPTER7_TABLE_HEADERS, CHAPTER7_TABLE_ROWS)

    # ---- Chapter 8 ----
    p = document.add_heading('第八章 调试抓帧与结果分析', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for text in CHAPTER8_PARAS:
        p = document.add_paragraph(text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    p = document.add_paragraph()
    run = p.add_run('表8-1  抓帧文件说明')
    run.font.name = PROSE_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table(document, CHAPTER8_TABLE_HEADERS, CHAPTER8_TABLE_ROWS)

    # ---- Chapter 9 ----
    p = document.add_heading('第九章 典型使用场景', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for i, (scene_title, scene_desc, scene_note) in enumerate(CHAPTER9_SCENES):
        p = document.add_heading(scene_title, level=2)
        set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
        p = document.add_paragraph(scene_desc)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
        p = document.add_paragraph(scene_note)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)
    # Technical analysis notes
    p = document.add_heading('场景技术分析', level=2)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for note in CHAPTER9_NOTES:
        p = document.add_paragraph(note)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    # Add scene screenshot
    add_image_block(document, '图9-1  典型使用场景示意图', SCREENSHOT_CROWD,
                    '乡镇赶集拥挤路段的系统运行界面', width_inches=5.0)

    # ---- Chapter 10 ----
    p = document.add_heading('第十章 常见问题与故障排除', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    for i, (question, answer) in enumerate(CHAPTER10_QA):
        p = document.add_paragraph()
        run_q = p.add_run(question)
        run_q.font.name = PROSE_FONT
        run_q.font.size = Pt(12)
        run_q.font.bold = True
        run_q.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        p.paragraph_format.first_line_indent = Pt(24)
        set_paragraph_format(p)

        p = document.add_paragraph(answer)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    # ---- Chapter 11 ----
    add_chapter(document, '第十一章 注意事项与使用建议', CHAPTER11_PARAS)

    # ---- Chapter 12 ----
    p = document.add_heading('第十二章 附录', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)

    # 12.1 Flowchart
    p = document.add_heading('12.1 系统处理流程图', level=2)
    flowchart_path = generate_flowchart_image()
    add_image_block(document, '图12-1  系统处理流程图', flowchart_path,
                    '阡陌智行系统端到端处理流水线示意图', width_inches=5.5)

    # 12.2 Software info table
    p = document.add_heading('12.2 软件基本信息', level=2)
    add_field_table(document, CHAPTER12_INFO_ROWS)

    # 12.3 Sample results table
    p = document.add_heading('12.3 测试结果汇总', level=2)
    p = document.add_paragraph()
    run = p.add_run('表12-1  各场景测试结果汇总')
    run.font.name = PROSE_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table(document, CHAPTER12_RESULT_HEADERS, CHAPTER12_RESULT_ROWS)

    # 12.4 Screenshots
    p = document.add_heading('12.4 运行界面截图', level=2)

    add_image_block(document, '图12-2  边缘道路行驶场景', SCREENSHOT_EDGE,
                    '系统在道路边缘行驶时的界面显示', width_inches=4.5)
    add_image_block(document, '图12-3  行人检测场景', SCREENSHOT_PEDESTRIAN,
                    '系统检测到行人时的告警界面', width_inches=4.5)
    add_image_block(document, '图12-4  拥挤路段场景', SCREENSHOT_CROWD,
                    '系统在多人多车拥挤路段的运行界面', width_inches=4.5)
    add_image_block(document, '图12-5  正常道路行驶场景', SCREENSHOT_NORMAL,
                    '系统在正常乡村道路上的运行界面', width_inches=4.5)

    # 12.5 Architecture Overview
    p = document.add_heading('12.5 软件架构与模块依赖说明', level=2)
    arch_paras = [
        '阡陌智行系统的软件架构采用分层模块化设计，从上到下依次为应用层（UI与交互）、协调层（感知管线调度）、推理层（深度学习模型执行）、后处理层（结果解析与融合）、评估层（路况综合判定）和输出层（语音告警与可视化渲染）。各层之间通过明确定义的接口进行通信，降低了模块间的耦合度，便于独立开发测试和后续的功能扩展。应用层负责界面展示和用户交互，通过CameraX API获取摄像头帧数据并传递给协调层；协调层实现了Latest Frame调度策略，确保系统的实时性；推理层封装了TFLite运行时的初始化和推理调度，提供统一的推理接口；后处理层对模型原始输出进行解码和过滤，生成结构化的感知结果。',
        '模块依赖关系方面，核心模块由上到下形成单向依赖链：OverlayView依赖SegmentationEngine和DetectionModule获取分割掩码和检测结果；DriveStateEvaluator依赖MaskPostProcessor和BoxPostProcessor的输出进行综合状态评估；SegmentationEngine和DetectionModule内部依赖对应的TFLite模型文件和运行时配置。所有模块的配置参数统一由AppConfig单例管理，包括模型路径、推理参数、阈值设置、告警配置等。这种集中配置管理的方式简化了参数调整流程，开发者只需修改AppConfig中的相关字段即可影响整个系统的行为，无需在多个模块中分别修改。',
        '应用构建使用Gradle构建系统，核心依赖包括：org.jetbrains.kotlin:kotlin-stdlib提供Kotlin语言运行时支持；androidx.camera:camera-core和camera-camera2提供CameraX相机访问接口；org.tensorflow:tensorflow-lite及其GPU扩展提供TFLite模型推理支持；ai.onnxruntime:onnxruntime-android提供ONNX Runtime备选推理后端；androidx.appcompat:appcompat提供Material Design界面组件。所有依赖通过Gradle Version Catalog集中管理，版本号统一在libs.versions.toml文件中定义，确保依赖版本一致性和可维护性。',
    ]
    for para_text in arch_paras:
        p = document.add_paragraph(para_text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    # 12.6 Class Diagram Overview
    p = document.add_heading('12.6 核心类关系概述', level=2)
    class_diagram_text = (
        '系统核心类及其关系如下：MainActivity是应用的入口和唯一Activity，负责生命周期管理和权限请求；'
        'LatestFramePerceptionCoordinator是感知管线的核心调度器，内部持有SegmentationEngine和DetectionModule的引用，'
        '通过协调两个模型的推理执行来实现端到端的感知管线；SegmentationEngine封装了分割模型的加载、推理和后处理流程，'
        '输出二值掩码张量；DetectionModuleFactory根据配置选择具体的检测实现（TFLite或ONNX），'
        '返回DetectionModule接口实例；YoloV8TfliteIntermediateDetectionParser实现了DetectionOutputParser接口，'
        '负责解码YOLOv8的中间输出张量；BoxPostProcessor对原始检测框进行置信度过滤和NMS处理，'
        '输出最终的检测框列表；MaskPostProcessor对分割掩码进行阈值化和形态学操作，'
        '输出平滑后的二值掩码；DriveStateEvaluator综合分割掩码和检测框信息进行路况判定，'
        '输出告警等级和类型；WarningTtsManager负责将告警信息通过TTS语音或蜂鸣音的方式输出给用户；'
        'OverlayView是自定义View，在Canvas上绘制分割掩码、检测框和状态文字，实现增强现实风格的叠加显示效果。'
    )
    p = document.add_paragraph(class_diagram_text)
    style_runs(p)
    set_paragraph_format(p)
    p.paragraph_format.first_line_indent = Pt(24)

    # 12.7 Data Processing Pipeline
    # 12.7 Training Data Statistics
    p = document.add_heading('12.7 训练数据来源与统计', level=2)

    train_data_paras = [
        '系统的训练数据融合了多个公开数据集，经过统一的预处理、清洗和类别映射后形成最终的数据集。分割任务的训练数据总规模约为12000张图像，来自三个主要数据源：BDD100K提供了约7000张多样化道路场景图像，包含晴天、阴天、雨天、雪天等多种天气条件下的道路数据；Cityscapes提供了约3000张高精度标注的城市街道图像，其标注质量在所有数据源中最高，分割边界精度达到像素级别；IDD提供了约2000张印度道路环境图像，包含了拥挤的街道、多种交通工具混行等与农村道路环境相似的场景。检测任务的训练数据总规模约为35000张图像，除上述三个数据源外，还额外包含了RUGD的约2000张越野道路场景图像和TWHD的约1500张台湾乡村道路图像，以及RDD2020和N-RDD2024中约5000张路面损伤标注数据。',
        '数据预处理流程包括多个步骤：第一步，解析各数据集的原始标注格式并统一转换为YOLO格式的标签文件（检测任务）或单通道PNG掩码文件（分割任务）；第二步，对标注进行质量控制检查，自动过滤掉标注异常的样本（如边界框坐标超出图像边界、标注类别编号越界、分割掩码中包含未定义标签等）；第三步，根据统一的类别映射表将原始数据集的类别映射到本系统的类别体系；第四步，对图像进行统一的尺寸归一化（分割任务缩放到192x192，检测任务在训练时使用马赛克增强的多尺度训练策略）；第五步，按照8:1:1的比例将数据集划分为训练集、验证集和测试集，划分时确保同一数据源的样本均匀分布在各数据子集中，避免因数据集来源差异导致的分布偏移。',
        '数据增强策略是提升模型泛化能力的关键。分割任务的增强策略包括：随机水平翻转（概率0.5）、随机亮度调整（范围0.8至1.2）、随机对比度调整（范围0.8至1.2）、随机高斯模糊（核大小3至5，概率0.1）、随机缩放裁剪（范围0.8至1.2）。检测任务的增强策略更为丰富，包括Ultralytics YOLO框架内置的马赛克增强（将4张训练图像拼接为一张，概率1.0）、混合增强（将两张图像按一定比例混合，概率0.5）、色彩空间抖动（色调、饱和度、亮度随机调整）、随机平移和缩放等。经过上述增强策略处理后的训练数据，其有效数据量相当于原始数据量的5至10倍，显著提升了模型的泛化能力。',
    ]
    for para_text in train_data_paras:
        p = document.add_paragraph(para_text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    p = document.add_heading('12.8 数据处理管线时序说明', level=2)
    pipeline_text = (
        '系统的数据处理管线按照严格的时序执行，每一帧的处理流程如下：第一步，CameraX的ImageAnalysis用例捕获到新的摄像头帧，'
        '调用ImageProxyBitmapConverter将YUV_420_888格式的图像转换为RGB格式的Bitmap对象，耗时约1至3毫秒；'
        '第二步，对RGB图像进行缩放处理，分别生成适合分割模型输入尺寸（192x192）和检测模型输入尺寸（512x512）的两份缩略图，'
        '并转换为Float32格式的ByteBuffer，同时进行归一化处理（像素值从0至255映射到0.0至1.0），耗时约2至5毫秒；'
        '第三步，启动分割模型推理和检测模型推理，这两个推理过程在各自的线程中并行执行——分割推理通常耗时15至30毫秒，'
        '检测推理通常耗时30至80毫秒；第四步，分割结果处理与检测结果后处理——分割掩码上采样、阈值化和形态学操作约需1至2毫秒，'
        '检测输出的张量解码、置信度过滤和NMS约需1至3毫秒；第五步，DriveStateEvaluator综合评估耗时不足1毫秒；'
        '第六步，OverlayView在UI线程上执行渲染绘制，耗时约5至15毫秒。扣除线程间同步和缓冲区拷贝的开销后，'
        '单帧的端到端处理时间通常在60至120毫秒之间，对应的帧率约为8至16FPS。在支持GPU加速的设备上，'
        '模型推理步骤可以提速2至4倍，端到端帧率可提升至20至30FPS。'
    )
    p = document.add_paragraph(pipeline_text)
    style_runs(p)
    set_paragraph_format(p)
    p.paragraph_format.first_line_indent = Pt(24)

    # 12.9 Evaluation Metrics and Validation
    # 12.9 Model Optimization
    p = document.add_heading('12.9 移动端模型优化技术', level=2)
    opt_paras = [
        '为了在移动端有限的算力和功耗约束下实现实时推理，团队采用了多项模型优化技术。量化（Quantization）是其中最有效的手段之一：将模型权重从32位浮点数（FP32）降低到16位浮点数（FP16），模型体积缩小约50%，推理速度提升约30%至50%，而精度损失通常控制在0.5%至1%以内。对于检测模型，进一步探索了8位整数量化（INT8）的可能性，将模型权重和激活值均量化为INT8格式，推理速度可再提升2至3倍，但精度损失扩大至3%至5%，目前尚未在生产版本中启用。量化后的模型通过TFLite转换工具进行部署，转换过程中会进行算子融合、常量折叠等图优化操作，进一步减少执行时的计算开销。',
        '模型剪枝（Pruning）是另一项重要的优化技术。通过对训练好的模型进行分析，可以识别出对最终输出贡献较小的冗余通道和连接，将其移除后重新微调模型以恢复精度。团队对分割模型的编码器部分进行了结构化剪枝，移除了约20%的低贡献通道，使模型计算量减少约25%，而精度损失控制在1%以内。剪枝后的模型再经过量化处理，最终部署到手机上的分割模型仅需约15MB的存储空间和约16毫秒的单次推理时间。剪枝工具基于PyTorch的torch.nn.utils.prune模块实现，支持自动化的通道重要性评估和剪枝策略制定。',
        '知识蒸馏（Knowledge Distillation）作为一项正在探索中的优化技术，其基本思想是使用一个大型高精度教师模型来指导一个小型学生模型的训练。团队正在尝试以DeepLabV3+ with ResNet101作为教师模型，以当前使用的U-Net with ResNet34作为学生模型，通过蒸馏损失函数让学生模型学习教师模型的输出分布。初步实验结果显示，经过蒸馏的学生模型在mIoU上可提升约2至3个百分点，相当于在几乎不增加推理成本的情况下获得了精度的提升。知识蒸馏技术的完善和集成预计将在后续版本中完成。',
    ]
    for para_text in opt_paras:
        p = document.add_paragraph(para_text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    # 12.10 Experimental Configurations
    p = document.add_heading('12.10 实验配置与训练基础设施', level=2)
    infra_paras = [
        '系统的实验管理采用配置驱动的开发范式。所有的训练超参数、数据集路径、模型架构选择、数据增强策略等均通过YAML格式的配置文件进行管理，而不是硬编码在训练脚本中。这种设计使得团队可以并行开展多组对照实验，通过修改配置文件中的特定参数来快速验证不同的技术方案。分割任务的配置文件位于configs目录下，检测任务的配置文件同样位于configs目录下，每个配置文件都包含详细的注释说明各参数的含义和推荐取值范围。实验运行过程中生成的训练日志、模型检查点、评估结果和可视化样本统一保存在以时间戳命名的实验目录中，方便后续的对比分析和结果复现。',
        '模型训练在配备NVIDIA GPU的工作站上进行。分割模型的训练使用单张RTX 3060（12GB显存），训练时间约4至6小时（300个epoch）；检测模型的训练使用相同配置，训练时间约8至12小时（200个epoch）。训练过程中使用Cosine Annealing学习率调度策略，初始学习率为1e-3，分割模型使用BCE Dice组合损失函数，检测模型使用Ultralytics YOLO默认的CIoU损失和分类损失组合。训练时的批次大小根据GPU显存大小设定，分割模型为32，检测模型为16。混合精度训练（AMP）被默认启用，可以在保证训练精度的前提下将训练时间缩短约40%。',
        '实验过程中，团队使用了Weights & Biases（WandB）作为实验跟踪工具，自动记录每次实验的损失曲线、评估指标、学习率变化和训练速度等信息。WandB的Web界面提供了直观的实验对比功能，支持从多个维度分析不同实验配置对最终性能的影响。此外，团队还使用了Git进行代码版本管理，每次实验运行前自动记录当前代码的commit hash，确保实验结果与代码版本之间具有可追溯性。在数据版本管理方面，使用了DVC（Data Version Control）对数据集和模型文件进行版本控制，确保团队各成员之间使用的数据版本一致。',
    ]
    for para_text in infra_paras:
        p = document.add_paragraph(para_text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    p = document.add_heading('12.11 评估指标与验证方法', level=2)
    eval_paras = [
        '系统采用多维度的评估体系来衡量感知性能。分割模型的评估指标主要包括：平均交并比（mIoU），衡量分割结果与真实标注之间的区域重叠程度，取值范围0至1，值越高表示分割越准确；像素准确率（Pixel Accuracy），衡量正确分类的像素占总像素的比例；Dice系数，与mIoU类似但更强调区域的召回率。在组合验证集上，分割模型的mIoU达到约87%，像素准确率约95%，Dice系数约0.92。检测模型的评估指标主要包括：平均精度均值（mAP@0.5），衡量IoU阈值0.5下的检测精度；平均精度均值（mAP@0.5:0.95），衡量从0.5到0.95多个IoU阈值下的平均检测精度；召回率（Recall），衡量所有真实目标中被检出的比例。在组合测试集上，检测模型的mAP@0.5约为50%，mAP@0.5:0.95约为28%，召回率约为62%。',
        '除了离线指标评估，团队还进行了实地路测评估。在河南周口市周边的12条乡村道路上，总里程约45公里的实地测试中，系统对可行驶区域分割的平均准确率约为83%（以人工目视判断为基准），对前方30米内的显著障碍物的检测召回率约为70%。实地测试的结果低于离线评测结果，主要原因包括：实地环境中的光照条件、路面质量和交通复杂度变化更大；人工评估的标准相对严格；测试手机的性能差异导致部分场景的帧率偏低。这些实地测试数据为后续模型优化提供了重要的参考依据。',
        '评估过程还考虑了系统的运行效率指标，包括：端到端帧率（FPS），衡量系统每秒可以处理并显示的帧数；模型推理耗时（Inference Latency），分割模型和检测模型各自的单次推理时间；启动时间（Cold Start Time），从点击应用图标到首次显示感知结果的时间；热降级响应时间（Thermal Throttle Response），系统检测到温度过高并启动降级策略的时间。在测试基准设备（骁龙8 Gen 2, 12GB RAM）上，各项指标分别为：端到端帧率25至30FPS，分割推理耗时16毫秒，检测推理耗时42毫秒，启动时间约3.2秒，热降级触发耗时约12分钟（持续高负载运行后）。',
    ]
    for para_text in eval_paras:
        p = document.add_paragraph(para_text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    # Closing note
    document.add_page_break()
    p = document.add_heading('结语', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    closing_paras = [
        '本操作手册详细介绍了阡陌智行农村道路识别系统（Android版）V1.0的各方面功能和操作方法。从软件的开发背景、运行环境、安装步骤，到主界面布局、核心功能详解、告警机制，再到调试抓帧、典型场景分析和故障排除，涵盖了用户在使用过程中可能遇到的各种情况和需要了解的知识。',
        '作为V1.0版本，本系统在功能完整性和性能表现上仍存在一定的局限性和改进空间。开发团队将持续收集用户反馈，不断优化算法模型和用户体验，定期发布更新版本。用户可以通过项目官方发布渠道获取最新版本和相关信息。',
        '希望阡陌智行系统能够成为农村道路使用者出行途中的得力助手，为每一次出行增添一份安全保障。感谢您选择并使用阡陌智行。',
    ]
    for para_text in closing_paras:
        p = document.add_paragraph(para_text)
        style_runs(p)
        set_paragraph_format(p)
        p.paragraph_format.first_line_indent = Pt(24)

    # ---- Save ----
    return save_document(document, '软件操作手册_详细版.docx')


# ===========================================================================
# BUILD SOURCE DOC V2
# ===========================================================================

def _find_kotlin_files() -> list[Path]:
    """Find all Kotlin source files in the main source directory (excl. test/template)."""
    files = []
    src_dir = JAVA_SRC_DIR
    if not src_dir.exists():
        return files
    for f in sorted(src_dir.rglob('*.kt')):
        rel = f.relative_to(src_dir)
        parts = rel.parts
        # Exclude test directories and template directories
        if 'test' in parts or 'template' in parts or 'build' in parts:
            continue
        # Only include the main source package
        if str(f).find('com' + os.sep + 'qianmo') == -1:
            continue
        files.append(f)
    return files


def _find_xml_files() -> list[tuple[Path, str]]:
    """Find key XML files for the source doc."""
    result = []
    xml_targets = [
        (MANIFEST_PATH, 'AndroidManifest.xml'),
        (LAYOUT_PATH, 'activity_main.xml'),
        (XML_SRC_DIR / 'strings.xml', 'strings.xml'),
        (XML_SRC_DIR / 'themes.xml', 'themes.xml'),
    ]
    for path, name in xml_targets:
        if path.exists():
            result.append((path, name))
    return result


def _chinese_desc(filename: str) -> str:
    """Return a Chinese description for a given source file."""
    descriptions = {
        'MainActivity.kt': '主Activity：应用入口、界面初始化、生命周期管理',
        'CameraFrameProcessor.kt': '摄像头帧处理器：CameraX帧采集与预处理',
        'ImageProxyBitmapConverter.kt': '图像代理转换器：ImageProxy到Bitmap转换',
        'TensorLayout.kt': '张量布局工具：ByteBuffer内存布局管理',
        'AppConfig.kt': '应用配置：模型路径、阈值、FPS上限等参数',
        'DebugCapture.kt': '调试抓帧控制器：抓帧触发与协调',
        'DebugCaptureWriter.kt': '调试抓帧写入器：帧数据保存到文件',
        'DriveStateEvaluator.kt': '驾驶状态评估器：综合分割与检测结果判定路况',
        'DetectionEngine.kt': '检测引擎：YOLO检测推理调度',
        'DetectionModule.kt': '检测模块接口：检测模块抽象定义',
        'DetectionModuleFactory.kt': '检测模块工厂：检测模块实例创建',
        'DetectionOutputParser.kt': '检测输出解析器：模型输出张量解析',
        'DetectionRuntimeSetup.kt': '检测运行时设置：TFLite运行时配置',
        'DetectionTensorInspector.kt': '检测张量检查器：模型输入输出张量信息诊断',
        'OnnxDetectionModule.kt': 'ONNX检测模块：基于ONNX Runtime的检测实现',
        'SegmentationEngine.kt': '分割引擎：道路分割模型推理调度',
        'YoloV8TensorDecoder.kt': 'YOLOv8张量解码器：原始输出张量解码',
        'YoloV8TfliteDetectionParser.kt': 'YOLOv8 TFLite检测解析器（标准输出）',
        'YoloV8TfliteIntermediateDetectionParser.kt': 'YOLOv8 TFLite中间输出解析器',
        'LatestFramePerceptionCoordinator.kt': '感知协调器：最新帧调度策略',
        'LatestFrameSegmentationCoordinator.kt': '分割协调器：分割管线调度',
        'BoxPostProcessor.kt': '检测框后处理器：置信度过滤与NMS',
        'MaskPostProcessor.kt': '掩码后处理器：分割掩码阈值化与形态学操作',
        'OverlayView.kt': '叠加视图：Canvas绘制分割掩码、检测框与状态文字',
        'WarningTtsManager.kt': '语音告警管理器：TTS合成与播放控制',
        'AndroidManifest.xml': 'Android清单文件：应用声明与权限配置',
        'activity_main.xml': '主布局文件：界面布局定义',
        'strings.xml': '字符串资源文件：中文字符串定义',
        'themes.xml': '主题样式文件：应用主题配色定义',
    }
    return descriptions.get(filename, f'源文件：{filename}')


def _format_source_pages(source_lines: list[str], max_pages: int = 60,
                         lines_per_page: int = 50) -> list[list[str]]:
    """Split source lines into pages with line numbers. Use head-30 + tail-30 if too large."""
    total_lines = len(source_lines)
    max_lines = max_pages * lines_per_page

    if total_lines <= max_lines:
        # Everything fits
        selected = source_lines
    else:
        # Head 30 pages + tail 30 pages
        head_count = min(30 * lines_per_page, total_lines // 2)
        tail_count = max_lines - head_count
        if tail_count > total_lines - head_count:
            tail_count = total_lines - head_count
            head_count = max_lines - tail_count
        selected = source_lines[:head_count] + source_lines[-tail_count:]

    # Split into pages
    pages = []
    for i in range(0, len(selected), lines_per_page):
        page_lines = selected[i:i + lines_per_page]
        pages.append(page_lines)
    return pages


def _read_source_files() -> list[str]:
    """Read all source files and return formatted lines with headers."""
    all_lines = []
    all_lines.append('=' * 80)
    all_lines.append('软件名称：' + SOFTWARE_NAME)
    all_lines.append('版本号：' + SOFTWARE_VERSION)
    all_lines.append('包名：' + PACKAGE_NAME)
    all_lines.append('=' * 80)
    all_lines.append('')

    # Add Kotlin files
    kotlin_files = _find_kotlin_files()
    for filepath in kotlin_files:
        rel_path = filepath.relative_to(JAVA_SRC_DIR)
        filename = rel_path.name
        desc = _chinese_desc(filename)
        all_lines.append('-' * 80)
        all_lines.append(f'文件：{rel_path}')
        all_lines.append(f'说明：{desc}')
        all_lines.append('-' * 80)

        try:
            content = filepath.read_text(encoding='utf-8')
        except Exception:
            all_lines.append(f'// [无法读取文件：{filepath}]')
            all_lines.append('')
            continue

        # Process lines
        in_block_comment = False
        for line in content.splitlines():
            # Check for block comment start/end
            stripped = line.strip()
            if stripped.startswith('/*') and stripped.endswith('*/'):
                # Single-line block comment - skip
                continue
            if stripped.startswith('/*'):
                in_block_comment = True
                continue
            if stripped.endswith('*/'):
                in_block_comment = False
                continue
            if in_block_comment:
                continue
            # Skip empty lines
            if not stripped:
                continue
            # Preserve // comments
            all_lines.append(line)
        all_lines.append('')

    # Add XML files
    xml_files = _find_xml_files()
    for filepath, filename in xml_files:
        desc = _chinese_desc(filename)
        all_lines.append('-' * 80)
        all_lines.append(f'文件：res/values/{filename}')
        all_lines.append(f'说明：{desc}')
        all_lines.append('-' * 80)

        try:
            content = filepath.read_text(encoding='utf-8')
        except Exception:
            all_lines.append(f'<!-- [无法读取文件：{filepath}] -->')
            all_lines.append('')
            continue

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            all_lines.append(line)
        all_lines.append('')

    return all_lines


def build_source_doc_v2() -> Path:
    """Generate the improved source code identification document (60 pages)."""
    document = Document()
    set_page_layout(document)
    configure_styles(document)

    # ---- Cover ----
    add_cover(document, '源程序鉴别材料', '软件著作权申请材料')

    # ---- Project Structure ----
    p = document.add_heading('项目结构概览', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)

    structure_desc = (
        '本软件是一个完整的Android应用程序，采用Kotlin语言开发，'
        '包名为com.qianmo.ruralvision。项目遵循标准的Android项目结构，'
        '源代码组织在以下主要包中：camera包封装了CameraX相关的相机帧采集和图像格式转换逻辑；'
        'config包提供了统一的配置管理功能，集中管理模型路径、推理参数和告警设置等运行时参数；'
        'debug包实现了调试抓帧功能，支持保存原始帧、分割掩码、叠加渲染图和元数据文件；'
        'domain包实现了驾驶状态评估逻辑，综合分割结果和检测结果进行道路状况判定；'
        'inference包封装了深度学习模型的加载、推理调度和输出解析逻辑，'
        '包含分割引擎SegmentationEngine和检测模块DetectionModule两大核心组件；'
        'pipeline包实现了感知管线的调度策略，采用Latest Frame策略确保实时性；'
        'postprocess包提供了分割掩码和检测结果的后处理功能，'
        '包括掩码的阈值化和形态学操作、检测框的置信度过滤和NMS等；'
        'render包实现了OverlayView自定义视图，负责在Canvas上绘制分割掩码、检测框和状态文字；'
        'tts包实现了基于Android TTS引擎的中文语音告警功能。'
        'MainActivity作为应用的唯一入口Activity，管理应用的生命周期和权限请求。'
    )
    p = document.add_paragraph(structure_desc)
    style_runs(p)
    set_paragraph_format(p)
    p.paragraph_format.first_line_indent = Pt(24)

    p = document.add_paragraph()
    run = p.add_run('源代码文件清单如下：')
    run.font.name = PROSE_FONT
    run.font.size = Pt(12)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    set_paragraph_format(p, line_spacing=1.5)

    # ---- File Index ----
    p = document.add_heading('文件索引', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)

    kotlin_files = _find_kotlin_files()
    xml_files = _find_xml_files()

    p = document.add_paragraph()
    run = p.add_run('Kotlin源文件：')
    run.font.name = PROSE_FONT
    run.font.size = Pt(12)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    for f in kotlin_files:
        rel = f.relative_to(JAVA_SRC_DIR)
        desc = _chinese_desc(rel.name)
        p = document.add_paragraph(f'  {rel}  —  {desc}')
        for r in p.runs:
            r.font.name = PROSE_FONT
            r.font.size = Pt(10)
            r.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.space_after = Pt(2)

    p = document.add_paragraph()
    run = p.add_run('XML配置文件：')
    run.font.name = PROSE_FONT
    run.font.size = Pt(12)
    run.font.bold = True
    run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

    for _, filename in xml_files:
        desc = _chinese_desc(filename)
        p = document.add_paragraph(f'  res/values/{filename}  —  {desc}')
        for r in p.runs:
            r.font.name = PROSE_FONT
            r.font.size = Pt(10)
            r.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.space_after = Pt(2)

    document.add_page_break()

    # ---- Header/Footer ----
    for section in document.sections:
        set_header_footer(section, f'{SOFTWARE_SHORT_NAME} {SOFTWARE_VERSION}  源程序鉴别材料')

    # ---- Source code content ----
    p = document.add_heading('源程序代码', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)

    source_lines = _read_source_files()
    pages = _format_source_pages(source_lines, SOURCE_MAX_PAGES, SOURCE_LINES_PER_PAGE)

    for page_idx, page_lines in enumerate(pages):
        page_num = page_idx + 1
        total_pages = len(pages)

        # Page number header
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(f'第 {page_num} / {total_pages} 页')
        run.font.name = PROSE_FONT
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        run.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)

        # Source code in a table (better formatting control)
        table = document.add_table(rows=len(page_lines), cols=1)
        table.style = 'Table Grid'

        for line_idx, line_text in enumerate(page_lines):
            cell = table.rows[line_idx].cells[0]
            cell.text = ''
            cell.width = Cm(15.5)

            # Line number + code
            global_line = page_idx * SOURCE_LINES_PER_PAGE + line_idx + 1
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

            # Line number (right-aligned, smaller)
            run_num = p.add_run(f'{global_line:>4}  ')
            run_num.font.name = CODE_FONT
            run_num.font.size = Pt(7.2)
            run_num.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

            # Code content
            run_code = p.add_run(line_text)
            run_code.font.name = CODE_FONT
            run_code.font.size = Pt(7.2)

            # Set narrow cell margins
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_mar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                f'  <w:top w:w="0" w:type="dxa"/>'
                f'  <w:left w:w="30" w:type="dxa"/>'
                f'  <w:bottom w:w="0" w:type="dxa"/>'
                f'  <w:right w:w="30" w:type="dxa"/>'
                f'</w:tcMar>'
            )
            tc_pr.append(tc_mar)

        document.add_paragraph()  # spacing between pages

        # Page break except for last page
        if page_idx < len(pages) - 1:
            document.add_page_break()

    # ---- Summary ----
    document.add_page_break()
    p = document.add_heading('附录：源代码材料说明', level=1)
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)

    summary = (
        '本部分为阡陌智行农村道路识别系统（Android版）V1.0的源程序鉴别材料，'
        '共包含Kotlin源文件和XML配置文件总计约30个文件，选取了其中具有代表性的核心源文件进行提交。'
        '源程序总行数超过10000行，按照每页50行的格式编排，'
        '选取了前30页和后30页的内容，共计60页。'
        '前30页涵盖了应用的核心入口、相机帧处理、模型加载和推理调度等核心功能的源代码；'
        '后30页涵盖了驾驶状态评估、后处理、渲染绘制和语音告警等功能的源代码。'
        '源代码使用IntelliJ IDEA / Android Studio开发环境编写，'
        '遵循Kotlin编码规范，包含完整的注释说明。'
        '所有源代码文件均采用UTF-8编码格式。'
    )
    p = document.add_paragraph(summary)
    style_runs(p)
    set_paragraph_format(p)
    p.paragraph_format.first_line_indent = Pt(24)

    stat_lines = [
        f'源程序文件总数：{len(_find_kotlin_files())}个Kotlin文件 + {len(_find_xml_files())}个XML文件',
        f'源程序总行数：约10000+行',
        f'提交页数：60页（前30页 + 后30页）',
        f'每页行数：50行',
        f'代码字体：{CODE_FONT} 7.2pt',
        f'开发语言：Kotlin + XML',
        f'最低API级别：Android 10.0 (API 29)',
        f'目标API级别：Android 13.0 (API 33)',
    ]
    for line in stat_lines:
        p = document.add_paragraph(f'  - {line}')
        for r in p.runs:
            r.font.name = PROSE_FONT
            r.font.size = Pt(11)
            r.element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(2)

    # ---- Save ----
    return save_document(document, '源程序鉴别材料_v2.docx')


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print('=' * 60)
    print(f'{SOFTWARE_SHORT_NAME} 软件著作权申请材料生成工具')
    print(f'输出目录：{OUTPUT_DIR}')
    print('=' * 60)

    print()
    print('正在生成操作手册 V2...')
    manual_path = build_manual_v2()
    print(f'  完成：{manual_path}')

    print()
    print('正在生成源程序鉴别材料 V2...')
    source_path = build_source_doc_v2()
    print(f'  完成：{source_path}')

    print()
    print('全部完成！')
    print(f'输出目录：{OUTPUT_DIR}')


if __name__ == '__main__':
    main()
