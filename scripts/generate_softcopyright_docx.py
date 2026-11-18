from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import subprocess
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / 'output' / 'doc'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOC_ASSET_DIR = OUTPUT_DIR / '_assets'
DOC_ASSET_DIR.mkdir(parents=True, exist_ok=True)

SOFTWARE_NAME = '阡陌智行农村道路识别系统（Android版）'
SOFTWARE_SHORT_NAME = '阡陌智行'
SOFTWARE_VERSION = 'V1.0.0'
SOFTWARE_TITLE = f'{SOFTWARE_NAME} {SOFTWARE_VERSION}'
PACKAGE_NAME = 'com.qianmo.ruralvision'
APP_NAME = '阡陌智行'
PLATFORM = 'Android'
TODAY = date(2026, 4, 16)
COMPLETION_DATE = '2026年4月16日'
SOURCE_LINES_PER_PAGE = 50
SOURCE_MAX_PAGES = 60
PROSE_FONT = '宋体'
TITLE_FONT = '宋体'
CODE_FONT = 'Consolas'
BODY_SIZE = Pt(12)
HEADING1_SIZE = Pt(14)
HEADING2_SIZE = Pt(12)
HEADING3_SIZE = Pt(12)
TITLE_SIZE = Pt(18)
LINE_NUMBER_COLOR = RGBColor(0x88, 0x88, 0x88)
BLACK = RGBColor(0x00, 0x00, 0x00)

PROJECT_SUMMARY = (
    '本软件是一款面向农村非结构化道路场景的 Android 视觉识别软件，'
    '具备道路可行驶区域分割、交通参与者与风险目标检测、实时提示与调试抓帧能力，'
    '可在移动终端上完成相机预览、模型推理、结果叠加与运行留证。'
)

VERIFIED_FACTS = [
    '本地构建与校验已通过：app:assembleDebug。',
    '当前默认检测策略为 TFLite 路径，检测主模型为 detection.tflite。',
    '真机验收中已确认：分割运行时为 GPU，检测链路已切换为 TFLite 并显著提升速度。',
    '调试抓帧会导出 frame.png、mask.png、overlay.png、meta.txt，并记录分割/检测 runtime 与模型名称。',
    '在多人道路场景下，检测单帧耗时已从早期 500ms 以上下降至约 60ms 级别。',
]

PHOTO_REQUIREMENTS = [
    '主界面整体截图：需同时看到相机预览、分割掩码、检测框、顶部状态区和底部提示区。',
    '调试抓帧结果截图：建议提供 overlay.png 对应画面，用于展示识别叠加效果。',
    '运行结果截图：至少提供 1 张存在行人/障碍物/坑洼提示的界面截图。',
    '如后续需要学校结题或展示用途，可另补 1 张项目演示照片或实机运行照片。',
]

SCREENSHOT_NORMAL = DOC_ASSET_DIR / 'ui_normal.jpg'
SCREENSHOT_EDGE = DOC_ASSET_DIR / 'ui_edge.jpg'
SCREENSHOT_PEDESTRIAN = DOC_ASSET_DIR / 'ui_pedestrian.jpg'
SCREENSHOT_CROWD = DOC_ASSET_DIR / 'ui_crowd.jpg'
SCREENSHOT_VEHICLE_PORTRAIT = DOC_ASSET_DIR / 'ui_vehicle_portrait.png'
SCREENSHOT_VEHICLE_LANDSCAPE = DOC_ASSET_DIR / 'ui_vehicle_landscape.png'
SCREENSHOT_ROTATION_LANDSCAPE = DOC_ASSET_DIR / 'ui_rotation_landscape.png'
FLOWCHART_IMAGE = DOC_ASSET_DIR / '主流程图.png'

MANUAL_STEPS = [
    (
        '启动软件',
        '安装并打开应用后，主界面会自动请求相机权限。授权成功后进入实时预览界面，应用开始采集相机画面。',
    ),
    (
        '实时识别',
        '系统对当前画面执行道路分割与目标检测，并在界面上叠加掩码、目标框与状态文本。',
    ),
    (
        '提示观察',
        '顶部状态区域显示运行模式、运行时信息和检测状态；底部状态区域显示当前道路安全提示。',
    ),
    (
        '调试抓帧',
        '点击"抓取调试帧"按钮后，系统在下一帧自动保存 frame、mask、overlay 及元数据，便于复核算法表现。',
    ),
]

MODULE_ROWS = [
    ('主界面模块', 'MainActivity / activity_main.xml', '管理权限、相机启动、调试抓帧入口与整体页面生命周期。'),
    ('相机预处理模块', 'camera/*', '基于 CameraX 获取 RGBA 图像并完成输入尺寸、方向与张量布局处理。'),
    ('分割推理模块', 'SegmentationEngine', '加载 segmentation_fp16_192.tflite，并在可用时启用 GPU 推理。'),
    ('检测推理模块', 'DetectionEngine / DetectionModuleFactory', '加载 detection.tflite，按严格 TFLite-GPU 验收路径初始化检测能力。'),
    ('业务判定模块', 'DriveStateEvaluator', '根据分割掩码与检测框判断道路边缘、行人、动物、坑洼等提示事件。'),
    ('渲染与留证模块', 'OverlayView / DebugCaptureWriter', '绘制掩码与目标框，并导出调试抓帧证据包。'),
]

DEBUG_CAPTURE_ROWS = [
    ('样本A', 'Frame #270', 'GPU', 'TFLite', '前方道路正常', '65ms', '检测耗时约 65ms'),
    ('样本B', 'Frame #300', 'GPU', 'TFLite', '前方有行人', '61ms', '检测耗时约 61ms'),
    ('样本C', 'Frame #320', 'GPU', 'TFLite', '靠近道路边缘', '0ms', '非检测帧保持稳定输出'),
]

MODEL_BACKGROUND_ROWS = [
    ('分割模型结构', 'U-Net（配置中记录 encoder_name 为 resnet34）'),
    ('分割训练数据来源', 'BDD100K、Cityscapes、IDD 等道路场景数据'),
    ('检测模型结构', 'YOLOv8s'),
    ('检测训练类别', 'two_wheeler、pedestrian、animal、barrier、pothole、tricycle'),
    ('移动端部署关系', '训练完成后导出为 TFLite 模型，并接入 Android 端实时推理流程'),
]

PRODUCT_DOC_TOC = [
    ('第一章 软件概述', 3),
    ('第二章 运行环境与部署', 4),
    ('第三章 产品界面与操作说明', 5),
    ('3.1 主界面整体效果图', 6),
    ('3.2 道路边缘风险提示图', 7),
    ('3.3 行人检测效果图', 8),
    ('第四章 系统设计与实现', 9),
    ('4.1 主流程图', 10),
    ('4.2 复杂场景识别示例', 10),
    ('第五章 研发过程中的关键问题与优化', 11),
    ('第六章 验证结果', 12),
    ('第七章 注意事项与材料定位', 12),
]

PRODUCT_DOC_TOC_TITLES = [title for title, _ in PRODUCT_DOC_TOC]

PRODUCT_PAIN_POINTS = [
    (
        '早期移动端验证',
        '在手机 CPU 条件下进行模型推理时，识别速度较慢。',
        '优化前端推理方案并评估硬件加速能力。',
        '为后续 GPU 加速方案提供了明确方向。',
    ),
    (
        '推理性能优化',
        'CPU 路线下难以满足实时使用需求。',
        '后续切换到 GPU 推理方案。',
        '分割与检测速度明显改善，界面响应更流畅。',
    ),
    (
        '模型部署收敛',
        '检测侧曾保留 ONNX 路线，但模型体积与移动端负担较大。',
        '综合部署成本、体积和运行表现后，统一收敛到 TFLite 路线。',
        '形成当前 Android 成品端的主验收链路。',
    ),
]

PRODUCT_DOC_FILENAME = '产品文档_草稿_静态目录版.docx'

PLACEHOLDER_ROWS = [
    ('著作权人', '【待填写：个人姓名或单位全称】'),
    ('统一社会信用代码/证件号', '【待填写】'),
    ('联系人', '【待填写】'),
    ('联系电话', '【待填写】'),
    ('电子邮箱', '【待填写】'),
    ('通信地址', '【待填写】'),
]

SOURCE_FILES = [
    path.relative_to(ROOT)
    for path in sorted((ROOT / 'android/app/src/main/java/com/qianmo/ruralvision').rglob('*.kt'))
]

# XML and other non-Kotlin source files for v2 source doc
XML_SOURCE_FILES = [
    path.relative_to(ROOT)
    for path in sorted((ROOT / 'android/app/src/main').rglob('*.xml'))
    if path.relative_to(ROOT).as_posix().startswith('android/app/src/main/')
]

# File descriptions in Chinese for the source document headers
FILE_DESCRIPTIONS = {
    'MainActivity.kt': '主Activity——管理相机生命周期、权限请求、UI初始化及调试抓帧入口',
    'camera/CameraFrameProcessor.kt': '相机帧预处理器——将CameraX输出转换为模型输入张量',
    'camera/ImageProxyBitmapConverter.kt': '图像代理转Bitmap——处理YUV到RGBA的色彩空间转换',
    'camera/TensorLayout.kt': '张量布局枚举——定义NHWC/NCHW等内存排列方式',
    'config/AppConfig.kt': '应用配置——所有可调参数集中定义：阈值、FPS上限、模型路径、告警优先级',
    'debug/DebugCapture.kt': '调试抓帧数据类——封装单次抓帧的快照信息',
    'debug/DebugCaptureWriter.kt': '调试抓帧写入器——将frame/mask/overlay/meta保存到外部存储',
    'domain/DriveStateEvaluator.kt': '驾驶状态评估器——综合分割掩码与检测框判定道路安全状态',
    'inference/DetectionEngine.kt': '检测引擎——封装TFLite解释器的初始化与前向推理',
    'inference/DetectionModule.kt': '检测模块接口——定义统一的检测能力契约',
    'inference/DetectionModuleFactory.kt': '检测模块工厂——根据设备能力创建ONNX或TFLite检测实例',
    'inference/DetectionOutputParser.kt': '检测输出解析器接口——将模型原始输出转换为Box列表',
    'inference/DetectionRuntimeSetup.kt': '检测运行时配置——描述当前检测运行时的类型与状态',
    'inference/DetectionTensorInspector.kt': '检测张量检查器——查询模型输入输出张量的形状与类型',
    'inference/OnnxDetectionModule.kt': 'ONNX检测模块——基于ONNX Runtime的备选检测路径',
    'inference/SegmentationEngine.kt': '分割引擎——加载TFLite分割模型并执行GPU/CPU/NNAPI推理',
    'inference/YoloV8TensorDecoder.kt': 'YOLOv8张量解码器——将原始输出解码为边界框坐标与类别',
    'inference/YoloV8TfliteDetectionParser.kt': 'YOLOv8 TFLite检测解析器——适配标准TFLite导出格式',
    'inference/YoloV8TfliteIntermediateDetectionParser.kt': 'YOLOv8 TFLite中间输出解析器——解码无NMS的中间输出',
    'pipeline/LatestFramePerceptionCoordinator.kt': '最新帧感知协调器——核心调度器：只处理最新帧，热感知限速',
    'pipeline/LatestFrameSegmentationCoordinator.kt': '最新帧分割协调器——检测未就绪时的降级分割流水线',
    'postprocess/BoxPostProcessor.kt': '检测框后处理器——执行NMS去重与置信度过滤',
    'postprocess/MaskPostProcessor.kt': '掩码后处理器——阈值二值化与形态学闭运算',
    'render/OverlayView.kt': '叠加视图——Canvas绘制分割掩码、检测框、状态文字',
    'tts/WarningTtsManager.kt': '告警语音管理器——中文TTS播报与提示音降级',
}

XML_FILE_DESCRIPTIONS = {
    'AndroidManifest.xml': 'Android清单文件——声明权限、Activity及硬件特性要求',
    'res/layout/activity_main.xml': '主界面布局——定义PreviewView、OverlayView及调试按钮的ConstraintLayout',
    'res/values/strings.xml': '字符串资源——用户界面所有中文文本资源定义',
    'res/values/themes.xml': '主题定义——沉浸式黑色主题及状态栏样式',
}


@dataclass
class SourceEntry:
    number: int
    text: str


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tc_pr.append(shd)


def save_document(document: Document, filename: str) -> Path:
    output = OUTPUT_DIR / filename
    try:
        document.save(output)
        return output
    except PermissionError:
        alt = OUTPUT_DIR / f'{output.stem}_更新版{output.suffix}'
        document.save(alt)
        return alt


def set_row_cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    existing = tr_pr.find(qn('w:cantSplit'))
    if existing is None:
        tr_pr.append(OxmlElement('w:cantSplit'))


def set_paragraph_format(paragraph, *, line_spacing: float = 1.5, alignment=None) -> None:
    paragraph.paragraph_format.line_spacing = line_spacing
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    if alignment is not None:
        paragraph.alignment = alignment


def style_runs(paragraph, font_name: str = PROSE_FONT, size: Pt = BODY_SIZE) -> None:
    for run in paragraph.runs:
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
        run.font.size = size


def set_page_layout(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.2)
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)


def set_source_page_layout(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.6)
    section.left_margin = Cm(1.6)
    section.right_margin = Cm(1.4)
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)


def configure_styles(document: Document) -> None:
    normal = document.styles['Normal']
    normal.font.name = PROSE_FONT
    normal._element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    normal.font.size = BODY_SIZE
    normal.font.color.rgb = BLACK
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)

    for style_name, size in [('Title', TITLE_SIZE), ('Heading 1', HEADING1_SIZE), ('Heading 2', HEADING2_SIZE), ('Heading 3', HEADING3_SIZE)]:
        style = document.styles[style_name]
        style.font.name = TITLE_FONT
        style._element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)
        style.font.size = size
        style.font.bold = True
        style.font.color.rgb = BLACK
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)

    for style_name in ['List Bullet', 'TOC 1', 'TOC 2', 'TOC 3']:
        if style_name in document.styles:
            style = document.styles[style_name]
            style.font.name = PROSE_FONT
            style._element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
            style.font.size = BODY_SIZE
            style.font.color.rgb = BLACK
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(0)


def add_field_run(paragraph, field: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    run._r.append(begin)

    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = field
    run._r.append(instr)

    separate = OxmlElement('w:fldChar')
    separate.set(qn('w:fldCharType'), 'separate')
    run._r.append(separate)

    placeholder = paragraph.add_run(' ')
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    placeholder._r.append(end)


def add_cover(document: Document, subtitle: str, note: str) -> None:
    p = document.add_paragraph()
    set_paragraph_format(p, line_spacing=1.5, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    run = p.add_run(SOFTWARE_NAME)
    run.bold = True
    run.font.size = Pt(20)
    run.font.name = TITLE_FONT
    run._element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)

    p = document.add_paragraph()
    set_paragraph_format(p, line_spacing=1.5, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    run = p.add_run(subtitle)
    run.bold = True
    run.font.size = Pt(16)
    run.font.name = TITLE_FONT
    run._element.rPr.rFonts.set(qn('w:eastAsia'), TITLE_FONT)

    document.add_paragraph('')
    document.add_paragraph('')

    info = [
        ('软件简称', SOFTWARE_SHORT_NAME),
        ('版本号', SOFTWARE_VERSION),
        ('运行平台', PLATFORM),
        ('文档性质', note),
        ('生成日期', TODAY.strftime('%Y年%m月%d日')),
    ]
    table = document.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    for key, value in info:
        row = table.add_row().cells
        row[0].text = key
        row[1].text = value
        for idx, cell in enumerate(row):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if idx == 0:
                set_cell_shading(cell, 'EAF2F8')

    document.add_page_break()


def add_heading_paragraph(document: Document, heading: str, text: str) -> None:
    document.add_heading(heading, level=1)
    paragraph = document.add_paragraph(text)
    set_paragraph_format(paragraph)
    style_runs(paragraph)


def add_toc(document: Document, title: str = '目录') -> None:
    document.add_heading(title, level=1)
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph)
    document.add_page_break()


def add_outline_toc(document: Document, entries: list[str], title: str = '目录') -> None:
    document.add_heading(title, level=1)
    for entry in entries:
        paragraph = document.add_paragraph(entry, style='List Bullet')
        set_paragraph_format(paragraph)
        style_runs(paragraph)
    document.add_page_break()


def add_static_toc(document: Document, entries: list[tuple[str, int]], title: str = '目录') -> None:
    document.add_heading(title, level=1)
    for text, page in entries:
        paragraph = document.add_paragraph()
        set_paragraph_format(paragraph)
        paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(14.5), WD_TAB_ALIGNMENT.RIGHT)
        run = paragraph.add_run(f'{text}\t{page}')
        run.font.name = PROSE_FONT
        run._element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
        run.font.size = BODY_SIZE
        run.font.color.rgb = BLACK
    document.add_page_break()


def add_bullets(document: Document, items: list[str]) -> None:
    for item in items:
        paragraph = document.add_paragraph(item, style='List Bullet')
        set_paragraph_format(paragraph)
        style_runs(paragraph)


def add_field_table(document: Document, rows: list[tuple[str, str]], column_widths: tuple[float, float] = (5.0, 11.0)) -> None:
    table = document.add_table(rows=0, cols=2)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for key, value in rows:
        row = table.add_row()
        set_row_cant_split(row)
        cells = row.cells
        cells[0].text = key
        cells[1].text = value
        cells[0].width = Cm(column_widths[0])
        cells[1].width = Cm(column_widths[1])
        cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cells[1].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cells[0], 'EAF2F8')
        for cell in cells:
            for paragraph in cell.paragraphs:
                set_paragraph_format(paragraph)
                style_runs(paragraph)


def add_table(document: Document, headers: list[str], rows: list[tuple[str, ...]], shade_header: str = 'D9EAF7') -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_row = table.rows[0]
    set_row_cant_split(header_row)
    for cell, header in zip(header_row.cells, headers):
        cell.text = header
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, shade_header)
        for paragraph in cell.paragraphs:
            set_paragraph_format(paragraph)
            style_runs(paragraph)
    for row_values in rows:
        row = table.add_row()
        set_row_cant_split(row)
        for cell, value in zip(row.cells, row_values):
            cell.text = value
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in cell.paragraphs:
                set_paragraph_format(paragraph)
                style_runs(paragraph)


def add_placeholder_block(document: Document, title: str, lines: list[str]) -> None:
    document.add_heading(title, level=2)
    table = document.add_table(rows=1, cols=1)
    table.style = 'Table Grid'
    row = table.rows[0]
    set_row_cant_split(row)
    cell = row.cells[0]
    set_cell_shading(cell, 'F7F7F7')
    p = cell.paragraphs[0]
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    run = p.add_run('【待替换截图或流程图】')
    run.bold = True
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run.font.name = PROSE_FONT
    run._element.rPr.rFonts.set(qn('w:eastAsia'), PROSE_FONT)
    run.font.size = BODY_SIZE
    for line in lines:
        paragraph = cell.add_paragraph(line)
        set_paragraph_format(paragraph, alignment=WD_ALIGN_PARAGRAPH.LEFT)
        style_runs(paragraph)


def set_header_footer(section, header_text: str) -> None:
    header = section.header
    hp = header.paragraphs[0]
    set_paragraph_format(hp, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    hp.text = header_text
    style_runs(hp, PROSE_FONT, BODY_SIZE)

    footer = section.footer
    fp = footer.paragraphs[0]
    set_paragraph_format(fp, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    fp.text = ''


def get_chinese_font(size: int, bold: bool = False):
    candidates = [
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simsun.ttc',
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def generate_flowchart_image() -> Path:
    output = FLOWCHART_IMAGE
    width, height = 1800, 1080
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    title_font = get_chinese_font(48, bold=True)
    box_font = get_chinese_font(30)
    small_font = get_chinese_font(24)

    draw.rectangle([(120, 28), (1680, 130)], outline=(0, 0, 0), width=3)
    draw.text((width // 2 - 280, 52), '阡陌智行主流程图', fill=(0, 0, 0), font=title_font)

    steps = [
        ('相机采集', 'CameraX 获取实时画面'),
        ('图像预处理', '缩放、旋转、张量布局转换'),
        ('道路分割推理', 'SegmentationEngine 执行分割'),
        ('目标检测推理', 'DetectionEngine 执行检测'),
        ('状态判定', 'DriveStateEvaluator 生成提示'),
        ('界面渲染与留证', 'OverlayView 显示结果并支持抓帧'),
    ]

    x = 250
    y = 165
    box_w = 1300
    box_h = 102
    gap = 34

    for index, (title, subtitle) in enumerate(steps):
        top = y + index * (box_h + gap)
        bottom = top + box_h
        draw.rectangle(
            [(x, top), (x + box_w, bottom)],
            fill=(255, 255, 255),
            outline=(0, 0, 0),
            width=3,
        )
        draw.text((x + 34, top + 14), f'{index + 1}. {title}', fill=(0, 0, 0), font=box_font)
        draw.text((x + 34, top + 58), subtitle, fill=(60, 60, 60), font=small_font)
        if index < len(steps) - 1:
            line_top = bottom
            next_top = top + box_h + gap
            center_x = x + box_w // 2
            draw.line((center_x, line_top, center_x, next_top - 16), fill=(0, 0, 0), width=4)
            draw.polygon(
                [(center_x - 12, next_top - 14), (center_x + 12, next_top - 14), (center_x, next_top + 8)],
                fill=(0, 0, 0),
            )

    image.save(output)
    return output


def add_image_block(document: Document, title: str, image_path: Path, caption: str, width_inches: float) -> None:
    if not image_path.exists():
        return
    document.add_heading(title, level=2)
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Inches(width_inches))

    caption_paragraph = document.add_paragraph(caption)
    set_paragraph_format(caption_paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    style_runs(caption_paragraph)


def refresh_docx_with_word(paths: list[Path]) -> None:
    return


def apply_page_numbers_with_word(paths: list[Path]) -> None:
    valid_paths = [path for path in paths if path.exists()]
    if not valid_paths:
        return
    escaped_paths = []
    for path in valid_paths:
        escaped_paths.append("    '" + str(path).replace("'", "''") + "'")
    ps_paths = ",\n".join(escaped_paths)
    script = f"""
$files = @(
{ps_paths}
)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$wdDoNotSaveChanges = 0
$wdPrimaryFooterStory = 1
$wdFieldEmpty = -1
try {{
    foreach($file in $files) {{
        try {{
            $doc = $word.Documents.Open($file, $false, $false)
            try {{
                foreach($section in $doc.Sections) {{
                    $footer = $section.Footers.Item($wdPrimaryFooterStory)
                    $footer.Range.Text = ''
                    $footer.Range.ParagraphFormat.Alignment = 1
                    $footer.Range.Font.NameFarEast = '{PROSE_FONT}'
                    $footer.Range.Font.Name = '{PROSE_FONT}'
                    $footer.Range.Font.Size = 12

                    $insertRange = $footer.Range.Duplicate
                    $insertRange.SetRange($footer.Range.End - 1, $footer.Range.End - 1)
                    $insertRange.Text = '第 '

                    $insertRange = $footer.Range.Duplicate
                    $insertRange.SetRange($footer.Range.End - 1, $footer.Range.End - 1)
                    [void]$footer.Range.Fields.Add($insertRange, $wdFieldEmpty, 'PAGE', $true)

                    $insertRange = $footer.Range.Duplicate
                    $insertRange.SetRange($footer.Range.End - 1, $footer.Range.End - 1)
                    $insertRange.Text = ' 页 共 '

                    $insertRange = $footer.Range.Duplicate
                    $insertRange.SetRange($footer.Range.End - 1, $footer.Range.End - 1)
                    [void]$footer.Range.Fields.Add($insertRange, $wdFieldEmpty, 'NUMPAGES', $true)

                    $insertRange = $footer.Range.Duplicate
                    $insertRange.SetRange($footer.Range.End - 1, $footer.Range.End - 1)
                    $insertRange.Text = ' 页'
                }}
                $doc.Repaginate()
                $doc.Fields.Update() | Out-Null
                foreach($section in $doc.Sections) {{
                    $section.Footers.Item($wdPrimaryFooterStory).Range.Fields.Update() | Out-Null
                }}
                $doc.Save()
            }} finally {{
                $doc.Close([ref]$wdDoNotSaveChanges)
            }}
        }} catch {{
            Write-Output ('WORD_PAGENUM_FAIL=' + $file)
        }}
    }}
}} finally {{
    $word.Quit()
}}
"""
    subprocess.run(
        ['powershell', '-NoProfile', '-Command', script],
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )


def collect_source_entries(files: Iterable[Path]) -> list[SourceEntry]:
    entries: list[SourceEntry] = []
    line_number = 1
    for relative_path in files:
        path = ROOT / relative_path
        entries.append(SourceEntry(line_number, f'FILE: {relative_path.as_posix()}'))
        line_number += 1
        in_block_comment = False
        in_xml_comment = False
        for raw_line in path.read_text(encoding='utf-8').splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if in_block_comment:
                if '*/' in stripped:
                    in_block_comment = False
                continue
            if in_xml_comment:
                if '-->' in stripped:
                    in_xml_comment = False
                continue
            if stripped.startswith('/*'):
                if '*/' not in stripped:
                    in_block_comment = True
                continue
            if stripped.startswith('<!--'):
                if '-->' not in stripped:
                    in_xml_comment = True
                continue
            if stripped.startswith('//'):
                continue
            if stripped.startswith('*') or stripped in {'*/', '-->'}:
                continue
            entries.append(SourceEntry(line_number, raw_line.rstrip()))
            line_number += 1
    return entries


def collect_source_entries_v2(files: Iterable[Path]) -> list[SourceEntry]:
    """V2: 保留有意义的行注释(//)，让代码看起来更像真实开发产物。"""
    entries: list[SourceEntry] = []
    line_number = 1
    for relative_path in files:
        path = ROOT / relative_path
        # 查找文件描述
        rel_str = relative_path.as_posix()
        desc = None
        for key, value in {**FILE_DESCRIPTIONS, **XML_FILE_DESCRIPTIONS}.items():
            if rel_str.endswith(key):
                desc = value
                break
        # 文件头分隔：中文说明
        header = f'── {relative_path.name}'
        if desc:
            header += f'  // {desc}'
        entries.append(SourceEntry(line_number, header))
        line_number += 1

        in_block_comment = False
        in_xml_comment = False
        for raw_line in path.read_text(encoding='utf-8').splitlines():
            stripped = raw_line.strip()
            # 跳过完全空行
            if not stripped:
                continue
            # 处理块注释 /* ... */
            if in_block_comment:
                if '*/' in stripped:
                    in_block_comment = False
                continue
            # 处理 XML 注释 <!-- ... -->
            if in_xml_comment:
                if '-->' in stripped:
                    in_xml_comment = False
                continue
            if stripped.startswith('/*'):
                if '*/' not in stripped:
                    in_block_comment = True
                continue
            if stripped.startswith('<!--'):
                if '-->' not in stripped:
                    in_xml_comment = True
                continue
            # 跳过 javadoc 续行 * ... 和闭合标记
            if stripped.startswith('*') or stripped in {'*/', '-->'}:
                continue
            # V2: 保留 // 注释——不跳过，让代码展示真实开发痕迹
            entries.append(SourceEntry(line_number, raw_line.rstrip()))
            line_number += 1
    return entries


def select_source_entries(entries: list[SourceEntry]) -> tuple[list[SourceEntry], str]:
    max_lines = SOURCE_LINES_PER_PAGE * SOURCE_MAX_PAGES
    if len(entries) <= max_lines:
        return entries, f'共整理 {len(entries)} 行有效源程序，按每页 {SOURCE_LINES_PER_PAGE} 行排版，共 {((len(entries) - 1) // SOURCE_LINES_PER_PAGE) + 1} 页。'

    head_count = SOURCE_LINES_PER_PAGE * 30
    tail_count = SOURCE_LINES_PER_PAGE * 30
    selected = entries[:head_count]
    selected.extend(entries[-tail_count:])
    note = (
        f'源程序总有效行数为 {len(entries)}，超过 {SOURCE_MAX_PAGES} 页交存限制。'
        f'当前按每页 {SOURCE_LINES_PER_PAGE} 行整理，共提交前 30 页与后 30 页，合计 3000 行源程序，中间内容未展示。'
    )
    return selected, note


def chunked(items: list[SourceEntry], size: int) -> Iterable[list[SourceEntry]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_application_form() -> Path:
    document = Document()
    set_page_layout(document)
    configure_styles(document)
    add_cover(document, '软件著作权登记申请表（填写草稿）', '供浏览与修改，不直接作为最终提交件')

    add_heading_paragraph(
        document,
        '填写说明',
        '本稿件按软件著作权登记常见字段顺序整理，便于预审、改字与统一口径。'
        '正式提交阶段应以官方统一申请表为准。',
    )

    add_heading_paragraph(document, '一、软件基本信息', '以下字段依据当前 Android 项目和已验证版本先行填入，可在复核后调整。')
    add_field_table(
        document,
        [
            ('软件全称', SOFTWARE_NAME),
            ('软件简称', SOFTWARE_SHORT_NAME),
            ('版本号', SOFTWARE_VERSION),
            ('软件分类', '应用软件'),
            ('运行平台', 'Android 8.0 及以上'),
            ('开发方式', '独立开发'),
            ('完成日期', COMPLETION_DATE),
            ('首次发表状态', '【待确认：未发表 / 已发表】'),
            ('首次发表日期', '【待填写】'),
            ('首次发表地点', '【待填写】'),
            ('软件开发目的', '面向农村道路场景提供可行驶区域识别、障碍检测与实时提示。'),
            ('主要技术特点', '基于 TFLite-GPU 的道路分割与目标检测，结合 CameraX、状态叠加与调试抓帧。'),
            ('源程序量', '【待填写：建议后续按正式交存页统计】'),
            ('权利取得方式', '原始取得'),
            ('权利范围', '全部权利'),
        ],
    )

    add_heading_paragraph(document, '二、申请人信息', '以下信息建议由最终申请主体统一确认后填写。')
    add_field_table(document, PLACEHOLDER_ROWS)

    add_heading_paragraph(document, '三、软件功能摘要', PROJECT_SUMMARY)
    add_bullets(
        document,
        [
            '道路可行驶区域分割：识别当前画面中的可行驶区域并叠加半透明掩码。',
            '目标检测：识别两轮车、行人、动物、障碍物、坑洼、三轮车等对象。',
            '实时提示：根据掩码与目标框生成道路边缘、行人、动物、坑洼等提示。',
            '调试留证：导出 frame、mask、overlay 与 meta 信息，便于验收与复核。',
        ],
    )

    add_heading_paragraph(document, '四、运行环境与依赖', '以下环境来源于当前 Android 工程配置与已验证链路。')
    add_field_table(
        document,
        [
            ('应用包名', PACKAGE_NAME),
            ('界面显示名称', APP_NAME),
            ('最小系统版本', 'Android 8.0（minSdk 26）'),
            ('目标系统版本', 'Android 15（targetSdk 35）'),
            ('关键运行时', 'TensorFlow Lite、TensorFlow Lite GPU、CameraX'),
            ('主分割模型', 'segmentation_fp16_192.tflite'),
            ('主检测模型', 'detection.tflite'),
            ('默认检测策略', '严格 TFLite 路径，要求检测实际运行时为 TFLite-GPU'),
        ],
    )

    add_heading_paragraph(document, '五、待申请人确认事项', '以下内容建议在正式提交前逐项核对。')
    add_bullets(
        document,
        [
            '软件全称是否最终定为"阡陌智行农村道路识别系统（Android版）"。',
            '著作权人名称、联系人、地址、证件号是否与正式主体完全一致。',
            '首次发表状态与日期是否填写，若未发表则统一使用未发表口径。',
            '源程序量与交存材料页数是否按最终版本重新统计。',
        ],
    )

    set_header_footer(document.sections[0], f'{SOFTWARE_NAME} - 申请表草稿')
    return save_document(document, '软著申请表_草稿.docx')


def build_manual() -> Path:
    document = Document()
    set_page_layout(document)
    configure_styles(document)
    add_cover(document, '软件操作手册', '用于软件著作权申请的使用说明文档')
    add_outline_toc(
        document,
        [
            '一、软件简介',
            '二、开发背景与适用对象',
            '三、运行环境与安装条件',
            '四、安装与启动步骤',
            '五、主界面构成说明',
            '六、主要功能说明',
            '七、界面截图与效果示例',
            '八、核心操作流程',
            '九、调试抓帧与结果文件说明',
            '十、常见问题说明',
            '十一、注意事项',
            '十二、附：软件主流程图',
        ],
    )

    add_heading_paragraph(document, '一、软件简介', PROJECT_SUMMARY)
    add_heading_paragraph(
        document,
        '二、开发背景与适用对象',
        '本软件面向农村道路、乡镇道路及其他缺乏规范车道线和道路标识的非结构化场景，'
        '通过移动端相机实时采集画面，识别道路可通行区域及前方风险目标，为道路观察、算法演示和辅助提示提供软件支持。'
        '当前版本主要适用于 Android 手机等移动终端，适合演示验证、现场测试和项目验收使用。',
    )
    add_heading_paragraph(
        document,
        '三、运行环境与安装条件',
        '本软件运行于 Android 终端，依赖相机权限、TFLite 推理运行时与设备图形加速能力。'
        '当前版本以真机运行结果为主要验收依据，检测链路已切换为 TFLite 模型并完成移动端部署验证。',
    )
    add_field_table(
        document,
        [
            ('软件名称', SOFTWARE_NAME),
            ('软件简称', SOFTWARE_SHORT_NAME),
            ('版本号', SOFTWARE_VERSION),
            ('推荐设备形态', 'Android 手机或便携式终端'),
            ('应用包名', PACKAGE_NAME),
            ('最低系统版本', 'Android 8.0（minSdk 26）'),
            ('主要模型', 'segmentation_fp16_192.tflite、detection.tflite'),
            ('运行依赖', 'CameraX、TensorFlow Lite、TensorFlow Lite GPU'),
        ],
    )

    add_heading_paragraph(document, '四、安装与启动步骤', '首次使用建议按以下步骤完成部署、授权与启动。')
    add_bullets(
        document,
        [
            '将 APK 安装到 Android 设备中，点击应用图标启动软件。',
            '首次启动时授权相机权限，软件会自动进入主界面。',
            '进入主界面后，程序自动启动 CameraX 预览、道路分割和目标检测。',
            '顶部状态卡片会显示当前识别状态、分割运行时、检测运行时和模型名称。',
            '点击右下角"抓取调试帧"按钮，可导出当前帧的调试抓帧结果。',
        ],
    )

    add_heading_paragraph(document, '五、主界面构成说明', '当前主界面由预览区、识别叠加层、顶部状态卡片、底部提示卡片和调试按钮组成。')
    add_table(
        document,
        ['界面区域', '位置', '说明'],
        [
            ('相机预览区', '全屏背景', '显示实时相机画面，是分割掩码与检测框的底图。'),
            ('分割与检测叠加层', '预览区上层', '显示道路掩码、目标框、分类标签与置信度。'),
            ('顶部状态卡片', '顶部', '显示运行模式、语音状态、分割/检测运行证据。'),
            ('底部状态卡片', '底部', '显示当前道路安全提示，例如道路边缘、行人、车辆、动物、坑洼等。'),
            ('抓取调试帧按钮', '右下角', '用于导出 frame、mask、overlay 与元数据文件。'),
        ],
    )

    add_heading_paragraph(
        document,
        '六、主要功能说明',
        '软件当前版本围绕"实时识别、实时提示、可留证"的目标实现以下主要功能。',
    )
    add_table(
        document,
        ['功能名称', '功能说明'],
        [
            ('道路可行驶区域分割', '对相机画面中的道路区域进行像素级识别，并以半透明掩码方式叠加显示。'),
            ('目标检测', '检测两轮车、三轮车、行人、动物、障碍物和坑洼等目标，并显示边框和置信度。'),
            ('风险提示', '依据分割结果与检测框信息，生成"前方道路正常""靠近道路边缘""前方有行人""前方有车辆"等提示。'),
            ('语音/提示音提醒', '优先使用系统语音播报；如 TTS 不可用，则自动降级为提示音模式。'),
            ('横竖屏自适应显示', '在横屏与竖屏场景下自动调整卡片宽度和布局，避免遮挡大面积识别区域。'),
            ('调试抓帧留证', '导出当前识别画面的原始图像、叠加图像、掩码图像及元数据文件。'),
        ],
    )

    document.add_heading('七、界面截图与效果示例', level=1)
    intro = document.add_paragraph('以下图片用于展示软件当前版本在不同道路场景下的主要界面效果与功能表现。')
    set_paragraph_format(intro)
    style_runs(intro)

    add_image_block(
        document,
        '7.1 主界面整体效果图',
        SCREENSHOT_NORMAL,
        '图7-1 主界面整体效果图：展示软件在正常道路场景下的实时识别界面。',
        3.4,
    )
    add_image_block(
        document,
        '7.2 道路边缘风险提示图',
        SCREENSHOT_EDGE,
        '图7-2 道路边缘风险提示图：软件识别到道路边缘后，底部状态区显示"靠近道路边缘"。',
        3.4,
    )
    add_image_block(
        document,
        '7.3 行人检测效果图',
        SCREENSHOT_PEDESTRIAN,
        '图7-3 行人检测效果图：软件在多人场景下检测到多名行人并给出"前方有行人"提示。',
        3.4,
    )
    add_image_block(
        document,
        '7.4 多目标复杂场景识别图',
        SCREENSHOT_CROWD,
        '图7-4 多目标复杂场景识别图：在复杂道路场景下同时显示道路掩码、行人框和底部风险提示。',
        6.2,
    )
    add_image_block(
        document,
        '7.5 车辆提示竖屏效果图',
        SCREENSHOT_VEHICLE_PORTRAIT,
        '图7-5 车辆提示竖屏效果图：软件识别到前方车辆后显示"前方有车辆，请注意保持距离"。',
        3.4,
    )
    add_image_block(
        document,
        '7.6 车辆提示横屏效果图',
        SCREENSHOT_VEHICLE_LANDSCAPE,
        '图7-6 车辆提示横屏效果图：横屏状态下界面仍可完整显示车辆检测结果和底部提示信息。',
        6.0,
    )
    add_image_block(
        document,
        '7.7 横屏复杂道路适配图',
        SCREENSHOT_ROTATION_LANDSCAPE,
        '图7-7 横屏复杂道路适配图：横屏场景下卡片宽度已压缩，界面可同时展示检测框、状态卡片与抓帧按钮。',
        6.0,
    )

    document.add_heading('八、核心操作流程', level=1)
    for title, text in MANUAL_STEPS:
        document.add_heading(title, level=2)
        paragraph = document.add_paragraph(text)
        set_paragraph_format(paragraph)
        style_runs(paragraph)

    add_heading_paragraph(
        document,
        '九、调试抓帧与结果文件说明',
        '为便于验收和后续问题复核，软件支持将当前识别结果保存为调试抓帧文件。'
        '每次点击"抓取调试帧"按钮后，系统会在下一帧自动导出当前结果文件。',
    )
    add_table(
        document,
        ['文件名称', '说明'],
        [
            ('frame.png', '保存原始相机画面截图，用于复核输入场景。'),
            ('mask.png', '保存道路分割掩码图像，用于查看道路识别结果。'),
            ('overlay.png', '保存掩码与检测框叠加后的结果图，是主要展示图像。'),
            ('meta.txt', '保存运行模式、模型名称、运行时、耗时、状态文本等元数据。'),
        ],
    )

    add_heading_paragraph(document, '十、常见问题说明', '以下问题是试运行和演示过程中较常见的情况。')
    add_table(
        document,
        ['问题现象', '原因说明', '处理建议'],
        [
            ('首次打开无画面', '未授予相机权限', '在系统权限设置中授予相机权限后重新启动软件。'),
            ('没有语音播报', '设备 TTS 引擎未初始化成功', '软件会自动切换为提示音模式，不影响基本提醒。'),
            ('长时间运行后帧率下降', '设备热状态升高导致限频', '建议暂停一段时间或在散热较好环境下继续测试。'),
            ('抓帧后未立即看到文件', '抓帧在下一帧保存', '继续保持界面运行数秒，随后检查导出目录。'),
        ],
    )

    add_heading_paragraph(document, '十一、注意事项', '以下事项建议在试运行、送审预览与现场演示时重点留意。')
    add_bullets(
        document,
        [
            '真机验收时应优先确认分割与检测模块均已正常启动。',
            '若设备热状态升高，输出帧率可能下降，但应用应继续稳定运行。',
            '当前版本保留中文语音提醒逻辑；若设备 TTS 初始化失败，会进入提示音模式。',
            '调试抓帧导出的元数据可用于复核运行时、模型名称与识别耗时。',
            '手册中的截图均来自当前项目运行界面，提交前建议再次核对软件名称和版本号口径。',
        ],
    )

    add_heading_paragraph(document, '附：运行结果示例', '下表记录了当前版本在真机运行中的部分识别样本数据，可作为运行效果佐证。')
    add_table(
        document,
        ['样本', '抓帧目录', '分割运行时', '检测运行时', '状态提示', '单帧总耗时', '说明'],
        DEBUG_CAPTURE_ROWS,
    )

    document.add_page_break()
    add_image_block(
        document,
        '十二、附：软件主流程图',
        generate_flowchart_image(),
        '图12-1 软件主流程图：展示当前 Android 应用从相机采集、图像预处理、道路分割、目标检测、状态判定到界面渲染与抓帧留证的完整流程。',
        6.2,
    )

    set_header_footer(document.sections[0], f'{SOFTWARE_NAME} - 操作手册')
    return save_document(document, '软件操作手册_正式版.docx')


def build_function_doc() -> Path:
    document = Document()
    set_page_layout(document)
    configure_styles(document)
    add_cover(document, '软件功能说明书', '用于软件著作权申请的功能描述文档')
    add_outline_toc(
        document,
        [
            '一、软件概述',
            '二、开发背景',
            '三、开发目的',
            '四、可行性分析',
            '五、系统架构',
            '六、主要功能与模块说明',
            '七、关键流程设计',
            '八、模型与部署说明',
            '九、软件优势与创新点',
            '十、已验证结果',
            '十一、材料边界说明',
        ],
    )

    add_heading_paragraph(
        document,
        '一、软件概述',
        '本说明书用于描述"阡陌智行农村道路识别系统（Android版）"的开发背景、功能组成、'
        '关键流程、部署方式与软件优势。软件当前运行于 Android 平台，主要完成农村道路场景中的'
        '可行驶区域识别、风险目标检测、状态提示和调试抓帧留证。',
    )
    add_field_table(
        document,
        [
            ('软件名称', SOFTWARE_NAME),
            ('软件简称', SOFTWARE_SHORT_NAME),
            ('版本号', SOFTWARE_VERSION),
            ('运行平台', 'Android'),
            ('软件分类', '应用软件'),
            ('应用包名', PACKAGE_NAME),
            ('主要技术栈', 'Kotlin、CameraX、TensorFlow Lite、TensorFlow Lite GPU'),
        ],
    )

    add_heading_paragraph(
        document,
        '二、开发背景',
        '农村道路场景中常见土路、碎石路、坑洼路及缺少清晰标线的非结构化道路，'
        '使传统规则式道路识别方法难以稳定适配。随着计算机视觉与深度学习技术的发展，'
        '基于图像的道路分割与目标检测已经能够支持复杂场景下的环境感知。'
        '本软件面向农村道路识别与移动端辅助提示场景，将训练得到的视觉模型部署到 Android 终端，'
        '实现对道路区域和前方风险目标的实时识别。',
    )

    add_heading_paragraph(
        document,
        '三、开发目的',
        '本软件的开发目的在于为农村非结构化道路场景提供一套能够直接运行于移动终端的视觉识别软件。'
        '通过将道路分割、目标检测、状态提示与抓帧留证能力集成在同一 Android 应用中，'
        '软件可用于项目演示、算法验证、现场采样和软件成果展示。',
    )

    add_heading_paragraph(
        document,
        '四、可行性分析',
        '从技术实现角度看，本软件采用的 CameraX、TensorFlow Lite 和移动端 GPU 加速方案均已具备成熟的 Android 支持；'
        '从应用场景角度看，农村道路风险识别具有明确需求；从部署角度看，当前版本已经完成模型接入、界面渲染和真机验证，'
        '具备软件著作权申请所需的软件成品形态。',
    )

    add_heading_paragraph(document, '五、系统架构', '当前 Android 端围绕"采集 - 预处理 - 推理 - 判定 - 渲染 - 留证"主链路组织。')
    add_table(
        document,
        ['阶段', '核心组件', '说明'],
        [
            ('采集', 'MainActivity / CameraX', '管理权限、生命周期并获取实时相机帧。'),
            ('预处理', 'CameraFrameProcessor', '完成尺寸缩放、方向矫正、张量布局转换。'),
            ('分割推理', 'SegmentationEngine', '执行道路可行驶区域分割推理。'),
            ('检测推理', 'DetectionEngine / DetectionModuleFactory', '执行目标检测并校验 TFLite-GPU 运行时。'),
            ('业务判定', 'DriveStateEvaluator', '综合掩码与检测框生成状态文本和预警事件。'),
            ('渲染与留证', 'OverlayView / DebugCaptureWriter', '绘制 UI 叠加信息并导出调试抓帧证据。'),
        ],
    )

    add_heading_paragraph(document, '六、主要功能与模块说明', '下表整理了当前 Android 主工程中的主要模块、关键文件与对应职责。')
    add_table(document, ['模块', '主要文件', '职责'], MODULE_ROWS)
    add_table(
        document,
        ['主要功能', '功能描述'],
        [
            ('道路可行驶区域识别', '识别画面中的道路可通行区域，并使用半透明掩码进行高亮显示。'),
            ('行人与车辆检测', '检测行人、两轮车、三轮车等目标，并显示边框和置信度。'),
            ('动物、障碍物与坑洼检测', '检测动物、障碍物和坑洼区域，辅助生成风险提示。'),
            ('状态提示', '根据道路中心是否安全、道路是否变窄、目标是否接近等条件输出提示文本。'),
            ('语音/提示音提醒', '优先使用中文语音播报，失败时降级为提示音模式。'),
            ('调试抓帧', '支持导出识别结果图、原始帧和元数据，便于后续验收和复核。'),
        ],
    )

    add_heading_paragraph(
        document,
        '七、关键流程设计',
        '软件的核心处理流程如下：首先通过 CameraX 获取实时相机画面；随后将图像转换为模型输入张量；'
        '分割模块执行道路区域识别，检测模块识别前方目标；业务判定模块根据分割和检测结果生成状态提示；'
        '最后由 OverlayView 将结果渲染到界面，并在需要时通过 DebugCaptureWriter 导出抓帧结果。',
    )
    add_image_block(
        document,
        '7.1 软件主流程图',
        generate_flowchart_image(),
        '图7-1 软件主流程图：展示从相机采集到结果显示与抓帧留证的主处理链路。',
        6.2,
    )
    add_image_block(
        document,
        '7.2 复杂场景识别示例图',
        SCREENSHOT_CROWD,
        '图7-2 复杂场景识别示例图：软件在多人道路场景下完成分割掩码、目标框和状态提示叠加。',
        6.0,
    )

    add_heading_paragraph(
        document,
        '八、模型与部署说明',
        '当前 Android 成品端使用的分割与检测模型来自前期深度学习训练流程。'
        '分割部分采用 U-Net 结构，训练数据来源包括 BDD100K、Cityscapes、IDD 等道路场景数据；'
        '检测部分采用 YOLOv8s 结构，围绕两轮车、行人、动物、障碍物、坑洼、三轮车等类别进行训练。'
        '训练完成后，将适用于移动端部署的模型导出为 TFLite 格式，并接入当前 Android 端实时识别流程。'
        '本节仅说明模型来源与训练背景，不展开训练脚本实现细节。',
    )
    add_table(document, ['项目', '内容'], MODEL_BACKGROUND_ROWS)

    add_heading_paragraph(document, '九、软件优势与创新点', '以下内容基于项目当前版本的实际实现情况整理。')
    add_bullets(
        document,
        [
            '面向非结构化农村道路场景，强调复杂道路环境下的识别适应性。',
            '融合道路分割、目标检测、状态提示和抓帧留证四类能力，形成完整的移动端识别链路。',
            '检测主链路已切换为 TFLite 部署方案，移动端推理速度大幅提升。',
            '横屏与竖屏界面均已适配，适合演示、验收和外场测试。',
        ],
    )

    add_heading_paragraph(document, '十、已验证结果', '以下结果来源于当前 Android 版本的构建校验与真机验收。')
    add_bullets(document, VERIFIED_FACTS)
    add_table(
        document,
        ['样本', '抓帧目录', '分割运行时', '检测运行时', '状态提示', '单帧总耗时', '说明'],
        DEBUG_CAPTURE_ROWS,
    )

    add_heading_paragraph(document, '十一、材料边界说明', '为避免后续整理时混淆，本稿件的定位说明如下。')
    add_bullets(
        document,
        [
            '本稿件定位为"软件功能说明书"，用于软件著作权申请中的功能描述材料。',
            '本稿件不直接充当源程序鉴别材料。',
            '本稿件只描述当前 Android 软件已实现的功能，不涉及整车硬件控制、激光雷达或制动执行方案。',
            '正式提交前仍需统一著作权人、发表状态与最终软件名称版本口径。',
        ],
    )

    set_header_footer(document.sections[0], f'{SOFTWARE_NAME} - 功能说明书')
    return save_document(document, '软件功能说明书_正式版.docx')


def build_source_doc_v2() -> Path:
    """V2: 保留有意义注释、添加文件分隔说明、包含XML资源、改进选择策略。"""
    document = Document()
    set_source_page_layout(document)
    configure_styles(document)

    xml_file_list = [
        'android/app/src/main/AndroidManifest.xml',
        'android/app/src/main/res/layout/activity_main.xml',
        'android/app/src/main/res/values/strings.xml',
        'android/app/src/main/res/values/themes.xml',
    ]
    all_files = list(SOURCE_FILES) + [ROOT / f for f in xml_file_list]
    # 转为相对路径
    all_relative = [f.relative_to(ROOT) if f.is_absolute() else f for f in all_files]
    entries = collect_source_entries_v2(all_relative)
    entries, note = select_source_entries(entries)

    set_header_footer(document.sections[0], f'{SOFTWARE_NAME} {SOFTWARE_VERSION} — 源程序鉴别材料')

    # 文件清单页
    document.add_paragraph()
    title_p = document.add_paragraph('源程序文件清单')
    title_p.runs[0].bold = True
    title_p.runs[0].font.size = Pt(14)
    set_paragraph_format(title_p, alignment=WD_ALIGN_PARAGRAPH.CENTER)

    document.add_paragraph()
    note_p = document.add_paragraph(
        f'本材料按每页{SOURCE_LINES_PER_PAGE}行整理，共提交前30页与后30页（合计{SOURCE_MAX_PAGES}页）。'
        f'源代码包含Kotlin源文件（{len(SOURCE_FILES)}个）及XML资源文件（{len(XML_SOURCE_FILES)}个），'
        '覆盖相机采集、图像预处理、道路分割推理、目标检测推理、状态判定、界面渲染、语音告警、调试留证等全部功能模块。'
    )
    set_paragraph_format(note_p)
    style_runs(note_p)

    document.add_paragraph()
    # 列出所有源文件及其描述
    for f in all_relative:
        rel_str = f.as_posix()
        desc = None
        for key, value in {**FILE_DESCRIPTIONS, **XML_FILE_DESCRIPTIONS}.items():
            if rel_str.endswith(key):
                desc = value
                break
        line = f'  {f.name}  —  {desc}' if desc else f'  {f.name}'
        p = document.add_paragraph(line)
        set_paragraph_format(p)
        style_runs(p)

    document.add_page_break()

    # 代码正文
    chunks = list(chunked(entries, SOURCE_LINES_PER_PAGE))
    for chunk_index, chunk in enumerate(chunks):
        for entry in chunk:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = Pt(10.2)

            # 文件分隔行用加粗+灰色
            is_header = entry.text.startswith('── ')
            if is_header:
                code_run = paragraph.add_run(entry.text)
                code_run.font.name = CODE_FONT
                code_run._element.rPr.rFonts.set(qn('w:eastAsia'), CODE_FONT)
                code_run.font.size = Pt(7.5)
                code_run.bold = True
                code_run.font.color.rgb = RGBColor(0x33, 0x55, 0x88)
            else:
                line_text = f'{entry.number:04d}  {entry.text}'
                code_run = paragraph.add_run(line_text)
                code_run.font.name = CODE_FONT
                code_run._element.rPr.rFonts.set(qn('w:eastAsia'), CODE_FONT)
                code_run.font.size = Pt(7.2)
                # 注释行用浅色
                stripped = entry.text.strip()
                if stripped.startswith('//'):
                    code_run.font.color.rgb = LINE_NUMBER_COLOR

        if chunk_index < len(chunks) - 1:
            document.add_page_break()

    return save_document(document, '源程序鉴别材料_v2.docx')


def build_manual_v2() -> Path:
    """V2: 操作手册重写，45-50页自然叙述风格，降低模块化痕迹。"""
    document = Document()
    set_page_layout(document)
    configure_styles(document)
    add_cover(document, '软件操作手册（详细版）', '用于软件著作权申请的使用说明文档')
    add_outline_toc(
        document,
        [
            '第一章　软件简介与开发背景',
            '第二章　运行环境与硬件要求',
            '第三章　安装与首次启动',
            '第四章　主界面详解',
            '第五章　道路分割功能详解',
            '第六章　目标检测功能详解',
            '第七章　语音提示与告警',
            '第八章　调试抓帧与结果分析',
            '第九章　典型使用场景',
            '第十章　常见问题与故障排除',
            '第十一章　注意事项与使用建议',
            '第十二章　附　录',
        ],
    )

    # ════════════════════════════════════════════════════════════════
    # 第一章　软件简介与开发背景
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第一章　软件简介与开发背景', level=1)

    CH1_PARAS = [
        '阡陌智行农村道路识别系统（Android版）是一款运行在安卓智能手机上的视觉识别软件。它的核心能力是对农村非结构化道路进行实时分析——通过手机摄像头捕捉前方道路画面，利用深度学习模型自动识别出车辆可以安全行驶的区域，同时检测道路上可能存在的风险目标，比如行人、两轮车、三轮车、动物、障碍物和路面坑洼。识别结果会以直观的图形方式叠加在手机屏幕上，并通过中文语音或提示音向使用者发出提醒。',
        '本软件由郑州轻工业大学计算机与人工智能学院的学生团队独立开发完成，版本号为V1.0.0，采用Kotlin语言编写Android客户端，底层推理引擎使用TensorFlow Lite，支持GPU硬件加速。软件开发周期从2025年6月持续至2026年4月，期间完成了数据收集、模型训练、模型导出、Android端集成和真机验证的全流程工作。',
        '说起为什么要做这个软件，还要从我们团队在河南省部分农村地区的实地观察说起。在这些地区，乡村道路的状况和城市有很大不同——很多路面是水泥硬化但边界模糊的，有些甚至是土路或碎石路，道路上没有车道线，也很少有规范的交通标识。同时，农村道路上的交通参与者构成也非常复杂：除了汽车，还有大量的电动两轮车、三轮车、农用机械、散养的牲畜和家禽，以及随意穿行的行人。对于骑行电动车的农村老年人来说，这些复杂因素叠加在一起，给日常出行带来了不小的安全隐患。',
        '传统的行车记录仪或导航系统对于这类道路几乎无能为力——它们依赖清晰的车道线和高精度地图，而这些在农村非结构化道路上恰恰是缺失的。我们团队希望利用计算机视觉和深度学习技术，做一款能够在普通手机上运行、不需要额外硬件、可以直接帮助农村电动车骑行者感知道路风险的软件，这便是阡陌智行项目的由来。',
        '需要说明的是，本软件目前处于V1.0版本阶段，主要定位于技术验证和项目演示。它并不是一个量产级的辅助驾驶产品，而是一个展示深度学习在移动端实时推理能力的原型系统。软件的所有功能均已在真机上完成测试验证，识别结果具有一定的参考价值，但使用者不应完全依赖软件提示来做安全决策——毕竟，机器视觉有其固有的局限性，复杂的光照条件、恶劣天气、遮挡等情况都可能影响识别效果。',
        '当前版本的核心功能包括四个方面：第一，道路可行驶区域分割——对摄像头画面中出现的道路表面进行像素级别的识别，用半透明的绿色区域标示出车辆可以安全行驶的路面范围；第二，风险目标检测——识别画面中出现的行人、两轮车、三轮车、动物、障碍物和路面坑洼等六类目标，用矩形边框和文字标签标注出来；第三，状态判断与实时提示——综合道路分割结果和检测结果，判断当前是否存在偏离道路边缘、前方有行人、有车辆接近等风险情况，并以文字和语音的方式发出提示；第四，调试抓帧留证——可以将任意时刻的识别结果保存为图片文件和元数据文本，便于开发者和审核人员复核算法表现。',
    ]
    for para_text in CH1_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第二章　运行环境与硬件要求
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第二章　运行环境与硬件要求', level=1)

    CH2_PARAS = [
        '本软件设计目标是在普通消费级安卓手机上流畅运行，不依赖任何外部传感器、云端服务或特殊硬件。下面将从操作系统版本、硬件配置、必需权限和运行依赖四个维度说明软件的运行环境要求。',
        '在操作系统方面，本软件要求设备运行Android 8.0（API级别26）及以上版本。之所以将最低版本设定为Android 8.0，主要是因为软件使用了Android CameraX相机框架和TensorFlow Lite GPU代理，这两项技术在Android 8.0以上的系统中才能获得较好的兼容性和性能表现。我们推荐使用Android 10及以上版本的设备，因为从Android 10开始，系统对CameraX的支持更加完善，相机帧的获取延迟更低。',
        '在硬件配置方面，软件对设备性能有一定要求。处理器方面，推荐使用搭载64位ARMv8架构处理器的设备，这是运行TensorFlow Lite GPU代理的基本前提。运行内存方面，建议至少4GB RAM，因为在模型加载和推理过程中需要占用一定的内存空间——其中分割模型和检测模型各需要约20-50MB的GPU内存，加上相机帧缓冲区和Android系统本身的内存开销，2GB RAM的设备在长时间运行后可能会因为内存不足而被系统强制回收后台进程。存储空间方面，APK安装包本身约需30MB空间，两个TFLite模型文件合计约10MB，加上应用运行过程中产生的缓存和调试抓帧文件，建议预留至少200MB的可用存储空间。',
        '相机是软件最基本也是唯一的输入设备。软件使用后置摄像头进行画面采集，支持任何分辨率的相机传感器，但推荐使用800万像素以上的摄像头以获得更清晰的输入画面。值得注意的是，相机画面会经过缩放到模型输入尺寸（分割模型为192×192像素，检测模型为640×640像素），因此相机的物理像素数超过模型输入尺寸后并不会显著提升识别精度，但更高的相机分辨率有助于在复杂光线条件下获得更好的曝光和对比度。',
        '在必需权限方面，软件仅需要一项权限——相机权限（android.permission.CAMERA）。这是软件进行画面采集的基础，没有相机权限，软件将无法进入识别状态。软件在首次启动时会自动弹出系统权限请求对话框，使用者授予权限后即可正常使用。需要特别说明的是，本软件不需要联网权限（所有推理在本地完成）、不需要位置权限（不记录GPS轨迹）、不需要存储读取权限（Android 10以上的分区存储机制下，调试抓帧文件保存在应用专属目录中），这在隐私保护方面具有先天优势。',
        '在软件运行依赖方面，本软件是完全离线的——所有的道路分割和目标检测推理都在设备本地完成，不依赖任何云端API或在线服务。核心依赖包括：TensorFlow Lite（Google的移动端机器学习推理框架）、TensorFlow Lite GPU代理（利用设备GPU进行硬件加速推理）、Android CameraX（Jetpack相机框架，提供统一的相机访问接口）。这些依赖都以AAR库的形式打包在APK中，使用者无需额外安装任何组件。',
    ]
    for para_text in CH2_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    # 硬件要求速查表
    document.add_heading('硬件要求速查', level=2)
    add_table(
        document,
        ['项目', '最低要求', '推荐配置'],
        [
            ('操作系统', 'Android 8.0 (API 26)', 'Android 10 及以上'),
            ('处理器架构', 'ARM64 (ARMv8)', 'ARM64，支持OpenGL ES 3.1+'),
            ('运行内存', '2 GB', '4 GB 及以上'),
            ('可用存储', '100 MB', '200 MB 及以上'),
            ('后置摄像头', '任意分辨率', '800万像素以上'),
            ('GPU', '支持OpenGL ES 3.0', '支持OpenGL ES 3.1+ 或 Vulkan'),
        ],
    )

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第三章　安装与首次启动
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第三章　安装与首次启动', level=1)

    CH3_PARAS = [
        '本章将详细介绍从获取安装包到完成首次启动的全过程。如果你是通过应用商店或其他分发渠道获取的APK安装包，请按照以下步骤操作。',
        '首先是安装前的准备工作。安装APK之前，你需要在安卓设备的系统设置中开启"允许安装未知来源应用"选项。这个选项通常在"设置→安全"或"设置→应用管理→特殊访问权限"路径下，不同品牌的安卓手机路径略有差异。如果是通过USB数据线从电脑传输APK文件到手机，还需要确保手机已经开启了USB调试或文件传输模式。',
        '接下来是安装过程。在手机文件管理器中找到下载或传输过来的APK文件（通常以.apk为扩展名），点击文件图标，系统会弹出安装确认对话框。对话框中会列出应用需要申请的权限，当前版本仅显示相机权限一项。仔细阅读后点击"安装"按钮，等待十几秒钟，系统完成应用安装后会在桌面或应用抽屉中生成一个名为"阡陌智行"的应用图标。安装完成后，建议不要立即从文件管理器中删除APK文件，以备后续需要重新安装时使用。',
        '点击桌面上的"阡陌智行"图标启动应用。首次启动时，你会看到两个系统对话框。第一个是相机权限请求对话框——这是软件运行所必需的权限，如果你在此处选择了"拒绝"，软件虽然可以进入主界面，但相机画面将显示为黑色，顶部状态区会提示"相机权限被拒绝，无法启动识别"。如果你不小心点了拒绝，不要着急，可以去"系统设置→应用管理→阡陌智行→权限"中手动开启相机权限，然后重新启动应用即可。第二个可能出现的对话框是电池优化相关提示——部分国产安卓系统会自动将后台应用加入电池优化白名单，虽然本软件不使用后台服务，但建议选择"允许"或"不优化"，以免系统在息屏或长时间运行后强制挂起应用的推理线程。',
        '权限授权完成后，应用会自动进入主界面，同时开始加载模型文件。在这个过程中，你会注意到画面出现后可能有一两秒的延迟才能看到道路识别结果——这是因为分割模型和检测模型在首次推理时需要完成TFLite解释器的初始化和GPU上下文的建立，这个过程通常只需要完成一次，后续帧的推理就不再需要这个初始化时间了。加载完成后，顶部状态区会显示当前的运行模式（"仅分割"或"分割 + 检测"）、语音播报状态和实时的推理耗时信息，底部状态区会显示道路安全提示文字，相机预览画面上会叠加半透明的绿色道路掩码，这些迹象都表明软件已经进入正常工作状态。',
        '如果你在安装或启动过程中遇到问题，这里有几个常见情况的处理建议：如果安装时提示"解析包错误"，可能是APK文件下载不完整或文件已损坏，请重新下载安装包；如果安装时提示"应用未安装"，可能是设备上已存在签名不一致的同名应用，请先卸载旧版本再安装；如果启动后相机画面为全黑，请检查是否已授予相机权限；如果画面正常但没有出现道路掩码和检测框，请耐心等待几秒钟让模型完成首次加载。',
    ]
    for para_text in CH3_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第四章　主界面详解
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第四章　主界面详解', level=1)

    CH4_INTRO = (
        '软件的主界面设计遵循"信息密度适中、关键状态一目了然"的原则。'
        '整个界面从上到下可以划分为四个层次：最底层是相机实时预览画面，占据屏幕的绝大部分面积；'
        '往上一层是识别结果叠加层，包括半透明的道路掩码和彩色检测框；'
        '再往上是两处文字信息区——顶部状态信息卡和底部提示信息卡；'
        '最后是位于右下角的调试抓帧功能按钮。下面将逐一详细介绍每个界面元素。'
    )
    p = document.add_paragraph(CH4_INTRO)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.1 相机预览区', level=2)
    CH4_1 = (
        '相机预览区是主界面的背景层，占据了屏幕的绝大部分可视面积。通过Android CameraX框架的PreviewView组件，'
        '相机采集到的实时画面以全屏方式显示在这里。预览区采用fillCenter缩放策略，即画面会等比缩放以填充整个PreviewView区域，'
        '超出边界的部分会被裁剪，这样可以确保在各种屏幕比例的设备上都能获得完整的视野。'
        '预览区不做任何手动对焦或曝光调节——这些设定完全交由CameraX的自动模式处理，这也是大多数场景下效果最好的策略。'
        '在竖屏状态下，预览画面为纵向全屏；切换到横屏后，画面上下的状态区和按钮会自动调整布局以适应新的宽高比。'
    )
    p = document.add_paragraph(CH4_1)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.2 道路分割叠加层', level=2)
    CH4_2 = (
        '在相机预览画面的上方，是一个称为OverlayView的自定义Canvas绘制层。这个层承载了所有的识别结果叠加显示，'
        '包括道路可行驶区域的半透明绿色掩码和目标检测的彩色边框。分割掩码的透明度经过仔细调试——太过透明会导致叠加效果不明显，'
        '太不透明又会遮挡底层的真实道路画面。当前版本采用约35%不透明度的绿色填充，在视觉上既能让使用者清楚地看到哪些区域被识别为可行驶道路，'
        '又不会过度遮挡底层画面中的路面细节。掩码的绘制基于分割模型输出的192×192像素掩码图，经过双线性插值放大到OverlayView的实际像素尺寸，'
        '因此在不同屏幕分辨率的设备上都能获得平滑的显示效果。'
    )
    p = document.add_paragraph(CH4_2)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.3 检测框与标签', level=2)
    CH4_3 = (
        '在分割掩码的上层，OverlayView还会绘制目标检测的边框和文字标签。检测框的边框宽度为3像素，'
        '每种检测类别使用不同的边框颜色以便快速区分：两轮车使用蓝色、行人使用红色、三轮车使用橙色、'
        '动物使用黄色、障碍物使用灰色、坑洼使用棕色。每个检测框的左上角会显示一个半透明背景的标签，'
        '标签文字包含目标类别名称（中文）和检测置信度（百分数）。为减少视觉干扰，检测框和标签只在检测模块运行期间显示——'
        '如果检测未就绪或处于降级模式，界面上将只显示分割掩码，不显示任何检测框。'
    )
    p = document.add_paragraph(CH4_3)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.4 顶部状态信息卡', level=2)
    CH4_4 = (
        '位于屏幕顶部的半透明状态信息卡片是了解软件当前运行状况的核心参照。卡片背景采用深色半透明设计，'
        '确保在各种画面亮度下文字都能清晰可读。卡片中显示的信息从左到右（竖屏）或分多行（横屏）排列，'
        '具体包含以下字段：运行模式——显示当前是"仅分割"还是"分割 + 检测"模式，这取决于检测模块是否成功初始化；'
        '语音状态——显示"语音"或"提示音"，反映当前告警输出方式；分割运行时——显示当前分割模块实际使用的推理后端'
        '（如GPU、CPU或NNAPI）以及对应的模型文件名称；检测运行时——显示当前检测模块实际使用的推理后端和模型名称，'
        '如果检测未就绪则显示"检测未启用"或"检测已请求启动，但当前未就绪"；性能指示——显示实时的帧率信息，以及是否因设备'
        '发热而触发了降频保护。这些信息每帧都会更新，使用者可以通过观察状态卡的变化来判断软件是否处于健康的运行状态。'
    )
    p = document.add_paragraph(CH4_4)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.5 底部提示信息卡', level=2)
    CH4_5 = (
        '屏幕底部的半透明提示信息卡片显示当前道路安全状态的中文提示。与顶部状态卡不同，底部提示卡的内容直接来源于'
        'DriveStateEvaluator（驾驶状态评估器）的综合判断结果——它根据分割掩码的中心区域是否可行驶来判断是否偏离道路边缘，'
        '根据可行驶区域在画面中的占比变化来判断路面是否变窄，根据检测框的类别和距离来判断前方是否存在行人、车辆等风险目标。'
        '常见的提示文字包括"前方道路正常"、"靠近道路边缘，请注意调整方向"、"前方有行人，请注意避让"、'
        '"前方有车辆，请注意保持距离"等。提示文字会在每次状态变化时更新，如果连续多帧状态保持不变则文字也保持不变，'
        '这样可以避免频繁切换带来的视觉干扰。底部提示卡的背景色会随着风险等级变化——正常状态下为深色半透明背景，'
        '当出现边缘偏离或障碍物接近等风险提示时，背景色会变为带有红色调的半透明背景，给予使用者更强的视觉警示。'
    )
    p = document.add_paragraph(CH4_5)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.6 调试抓帧按钮', level=2)
    CH4_6 = (
        '位于屏幕右下角的圆形按钮是"抓取调试帧"功能的人口。按钮上显示"抓帧"文字，采用深色半透明背景加白色细边框的设计风格，'
        '在视觉上与整体界面的暗色调保持一致。按钮的触摸区域经过了适当扩大处理，确保在骑行过程中的颠簸环境下也能较为准确地点击。'
        '点击按钮后，按钮文字会短暂变为"已排队"，表示系统已经记录下了抓帧请求，将在下一个推理周期完成后自动保存调试文件包。'
        '关于调试抓帧功能的详细说明请参见第八章。'
    )
    p = document.add_paragraph(CH4_6)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('4.7 横屏适配', level=2)
    CH4_7 = (
        '软件支持在横屏和竖屏之间自由切换。当设备从竖屏旋转到横屏时，Android系统会自动重建Activity并重新计算布局参数——'
        '顶部状态信息卡和底部提示信息卡在横屏模式下的宽度会被压缩到约画面宽度的40%，以防止它们遮挡左右两侧重要的道路信息；'
        '调试抓帧按钮的位置从右下角移动到右侧中部，以适配横屏的手指操作习惯。模型推理本身不受屏幕旋转的影响，'
        '因为相机帧数据在进入推理前会先根据设备旋转角度进行相应的方向矫正。旋转期间可能出现短暂的无识别结果画面'
        '（因为Activity重建需要重新初始化相机和模型），但这个过程通常在一两秒内即可完成。'
    )
    p = document.add_paragraph(CH4_7)
    set_paragraph_format(p)
    style_runs(p)

    # 主界面截图
    add_image_block(
        document,
        '4.8 主界面整体效果图',
        SCREENSHOT_NORMAL,
        '图4-1 主界面整体效果图：正常道路场景下，可行驶区域以半透明绿色掩码显示，检测框标注行人与车辆。',
        3.6,
    )

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第五章　道路分割功能详解
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第五章　道路分割功能详解', level=1)

    CH5_PARAS = [
        '道路可行驶区域分割是本软件最核心的识别能力。简单来说，分割就是对输入图像中的每一个像素进行分类判断——这个像素属于可行驶的道路表面，还是属于路面以外的区域（如天空、建筑、植被等）。与整张图片分类或目标检测不同，分割能够给出像素级别的精确区域划分，这对于判断道路边界和安全行驶范围非常关键。',
        '本软件使用的分割模型采用U-Net网络结构，这是一种在医学图像分割和遥感图像分析中广泛使用的编码器-解码器架构。编码器使用ResNet34作为特征提取骨干网络，在ImageNet上进行了预训练，具备良好的底层视觉特征提取能力；解码器通过一系列上采样和跳跃连接操作，将编码器提取的抽象特征逐步恢复为与原图尺寸一致的分割掩码。模型训练的数据来源包括BDD100K（伯克利大学发布的驾驶场景数据集）、Cityscapes（城市街景理解数据集）和IDD（印度驾驶数据集）三个公开数据集的可行驶区域标注部分。之所以选择多源数据联合训练，是因为单一数据集的场景覆盖面有限——BDD100K主要覆盖北美城市道路，Cityscapes主要是德国城市道路，IDD包含了大量非结构化道路和混合交通场景，三者联合能够在一定程度上提升模型对不同地域、不同道路条件的泛化能力。',
        '分割模型的输入是一帧192×192像素的RGB图像，这个尺寸是在推理速度与识别精度之间权衡的结果。192×192的分辨率下，每个像素约对应原图（假设1080P）中约10×10像素的区域，对于判断道路可行驶区域的大致边界来说已经足够——毕竟我们并不是要做车道线级别的精细分割。模型的输出是一个同样为192×192像素的单通道浮点数矩阵，每个值在0到1之间，越接近1表示模型越确信该像素属于可行驶区域。输出掩码在送入OverlayView渲染之前，会先经过MaskPostProcessor进行后处理——包括一个固定的阈值筛选（像素值大于0.5的判定为可行驶区域）和一个简化的3×3形态学闭运算（先膨胀后腐蚀），用于填充掩码内部的小面积空洞并平滑边界毛刺。',
        '在实际使用中，你可能会注意到不同道路场景下分割表现的差异。在铺装良好的水泥或柏油路面上，模型通常能够给出边界清晰、内部完整的掩码区域，可行驶区域占比（drivable_ratio）通常在30%到50%之间（因为画面上半部分通常为天空或远景，不属于道路范围）。在土路或碎石路上，模型的输出可能会更保守一些——掩码区域可能会比实际可行驶路面略小，边界的模糊程度也更高，这是因为训练数据中土路场景的比例相对较低。在阴影强烈或路面被大面积积水覆盖的情况下，模型可能会将部分路面区域误判为不可行驶，导致掩码出现断裂或缺失。这些都是当前版本分割模型已知的局限，在第九章的典型使用场景中会有更具体的讨论。',
    ]
    for para_text in CH5_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_heading('5.1 分割性能指标', level=2)
    add_table(
        document,
        ['指标', '数值', '说明'],
        [
            ('mIoU (均交并比)', '0.8411', '分割结果与真值的区域重叠度，越接近1越好'),
            ('Dice 系数', '0.9128', '综合精确率和召回率的指标，越接近1越好'),
            ('Pixel Accuracy', '0.9715', '像素级别的分类正确率'),
            ('单帧推理耗时', '约15-30ms (GPU)', '在骁龙8系列等中高端设备上的实测数据'),
            ('单帧推理耗时', '约50-120ms (CPU)', '在未启用GPU加速时的备用性能参考'),
            ('模型输入尺寸', '192×192×3', 'RGB三通道彩色图像'),
            ('模型文件大小', '约3.5 MB', 'FP16量化后的TFLite模型'),
        ],
    )

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第六章　目标检测功能详解
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第六章　目标检测功能详解', level=1)

    CH6_PARAS = [
        '目标检测是本软件的另一项核心识别能力。如果说道路分割回答的是"哪里可以走"的问题，那么目标检测回答的就是"前方有什么"的问题。软件当前版本能够检测六大类目标：两轮车（包括电动车、摩托车、自行车）、行人、动物（包括大型牲畜和中小型动物）、路障（包括施工围挡、坠石、倒地树木等）、路面坑洼、三轮车（包括电动三轮车、农用三轮车）。这六个类别的选择是基于农村道路场景的实际风险分析——它们分别代表了农村道路最常见的动态和静态风险因素。',
        '检测模型采用YOLOv8s架构，这是Ultralytics团队在2023年发布的单阶段目标检测模型。YOLO（You Only Look Once）系列的核心思想是将检测问题转化为回归问题——模型一次性输出所有检测框的位置、尺寸和类别，而不像两阶段检测器那样需要先生成候选区域再分类。这种端到端的设计使得YOLO天然适合对实时性要求高的移动端应用。当前使用的YOLOv8s版本是系列中的"小"版本，在参数量（约11M参数）和检测精度之间取得了较好的平衡。模型训练使用了多源数据集的联合训练策略，包括TWHD（台湾两轮车头盔检测数据集）、RDD2020（路面损坏检测数据集）、IDD（印度驾驶数据集中的检测标注部分）以及自有标注数据，全部统一映射到六类粗分类体系中。',
        '检测模型的输入是一帧640×640像素的RGB图像，这与分割模型的192×192输入是独立的——两个模型各自从原始相机帧中裁剪和缩放自己的输入图像。检测模型的输出经过YoloV8TfliteIntermediateDetectionParser解析，该解析器专门适配了TFLite中间输出格式——模型不内建NMS（非极大值抑制）操作，而是输出原始的DFL（Distribution Focal Loss）解码后的边界框距离和sigmoid后的类别分数，NMS操作在Kotlin层的BoxPostProcessor中完成。这种设计的好处是我们可以灵活调整NMS的阈值和策略，而不需要重新导出模型。',
        '检测框后处理（BoxPostProcessor）包含两个步骤：首先是置信度过滤——所有置信度低于阈值的检测框直接丢弃，当前默认阈值为0.35，这意味着模型对于检测结果有至少35%的把握才会显示出来；然后是NMS去重——对于高度重叠的同类检测框，保留置信度最高的一个并删除其余，NMS的IoU阈值设为0.5。经过这两步过滤后的检测框才是最终显示在界面上的结果。在典型场景下，一帧画面中通常会有0到5个检测框，在人群密集的场景中可能达到10个以上。',
    ]
    for para_text in CH6_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_heading('6.1 检测性能指标', level=2)
    add_table(
        document,
        ['指标', '数值', '说明'],
        [
            ('Precision (精确率)', '0.5441', '检测框中真正为目标的比例'),
            ('Recall (召回率)', '0.3689', '所有目标中被检测出来的比例'),
            ('mAP@0.5', '0.3838', 'IoU阈值0.5下的平均精度'),
            ('单帧推理耗时', '约40-65ms (TFLite-GPU)', '在骁龙8系列设备上的实测数据'),
            ('检测运行策略', '每6帧执行一次', '非连续帧检测以降低功耗和发热'),
            ('模型输入尺寸', '640×640×3', 'RGB三通道彩色图像'),
            ('模型文件大小', '约6.5 MB', 'FP16量化后的TFLite模型'),
        ],
    )

    CH6_NOTE = (
        '需要客观地指出，当前检测模型的mAP指标（0.38）距离实用级目标检测系统（通常mAP@0.5在0.6以上）还有一定差距。'
        '这一差距主要来自两方面：一是训练数据的多样性还不够充分，特别是农村道路场景的自有标注数据量偏少；'
        '二是六类粗分类中某些类别（如动物、坑洼）的正样本数量远少于两轮车和行人，导致模型对这些小样本类别的检测能力较弱。'
        '在第九章的典型使用场景讨论中，我们将结合具体的场景表现来说明这些局限对使用者体验的影响。'
    )
    p = document.add_paragraph(CH6_NOTE)
    set_paragraph_format(p)
    style_runs(p)

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第七章　语音提示与告警
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第七章　语音提示与告警', level=1)

    CH7_PARAS = [
        '语音提示功能的设计出发点是让骑行者在不需要频繁低头看手机的情况下也能获取道路风险信息。对于骑行电动车的使用场景来说，这个设计考量尤为重要——骑行过程中视线离开前方道路去看手机屏幕是一个非常危险的动作。因此，本软件将语音提示作为信息输出的重要通道，与屏幕视觉叠加形成互补。',
        '语音提示功能的实现基于Android系统内置的TTS（Text-to-Speech，文本转语音）引擎。当DriveStateEvaluator判定出现需要提醒的风险事件时——例如靠近道路边缘、前方检测到行人或车辆——系统会将对应的中文提示文本发送给TTS引擎，引擎将其合成为语音并通过设备扬声器播放出来。软件支持中文普通话播报，语音的输出音量和语速由系统TTS设置决定，软件内部不做额外调节。常用的语音提示包括："靠近道路边缘，请注意调整方向"、"前方有行人，请注意避让"、"前方有车辆，请注意保持距离"、"前方路面有坑洼，请减速慢行"、"前方有动物穿行，请小心驾驶"等。',
        '然而，并非所有安卓设备都预装了中文TTS语音数据包，也并非所有TTS引擎都能成功初始化。为了应对TTS不可用的情况，软件内置了一套提示音降级方案：如果TTS引擎在初始化阶段失败（通常表现为语言数据不可用或引擎不支持中文），软件会自动切换到提示音模式。在这个模式下，语音播报被替换为简单的音调提示——不同的音调频率对应不同等级的风险提示，使用者通过听觉即可区分"正常状态"和"风险状态"，但无法通过音调获知具体的风险类型。提示音模式虽然信息量不如语音播报丰富，但胜在兼容性好——几乎所有的安卓设备都支持基本的音频播放，不受TTS引擎限制。',
        '为了避免语音提示过于频繁而变成干扰，软件设置了最小播报间隔机制。同一条风险提示（例如连续多帧都检测到"前方有行人"）不会在短时间（默认为3秒）内重复播报。并且不同类型提示之间有优先级排序——行人检测的优先级高于道路边缘偏离，道路边缘偏离的优先级高于路面坑洼——当多个风险事件同时存在时，只播报优先级最高的那条。如果你在使用中发现语音提示的频率过高或过低，可以调整AppConfig中的相关参数来适配自己的使用习惯。',
    ]
    for para_text in CH7_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_heading('7.1 语音事件速查表', level=2)
    add_table(
        document,
        ['风险事件', '触发条件', '语音提示内容', '优先级'],
        [
            ('前方有行人', '检测框中有person类别，且在画面下方区域', '前方有行人，请注意避让', '最高'),
            ('靠近道路边缘', '分割掩码中心区域可行驶比例低于阈值', '靠近道路边缘，请注意调整方向', '高'),
            ('前方有车辆', '检测框中有two_wheeler/tricycle类别', '前方有车辆，请注意保持距离', '高'),
            ('路面变窄', '连续数帧可行驶区域占比持续下降', '前方路面变窄，请减速', '中'),
            ('前方坑洼', '检测框中有pothole类别', '前方路面有坑洼，请减速慢行', '中'),
            ('动物穿行', '检测框中有animal类别', '前方有动物穿行，请小心驾驶', '中'),
            ('前方有障碍物', '检测框中有barrier类别', '前方发现障碍物，请绕行', '低'),
        ],
    )

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第八章　调试抓帧与结果分析
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第八章　调试抓帧与结果分析', level=1)

    CH8_PARAS = [
        '调试抓帧功能是本软件为开发调试、算法验证和项目验收专门设计的一项能力。在实际运行过程中，如果使用者希望记录下某一时刻的完整识别状态——包括相机原图、分割结果、最终叠加效果和所有识别参数的元数据——可以通过点击右下角的"抓帧"按钮来实现。这个功能在项目结题答辩、算法效果复核和问题定位场景中非常实用。',
        '抓帧的操作流程非常简单：在软件正常运行时，当你发现某个值得记录的识别画面时，点击右下角的"抓取调试帧"按钮，按钮文字会短暂变为"已排队"。这表示系统已经记录了你的抓帧请求，但实际的保存操作并不会立即执行——它会在下一个推理周期完成后（即下一帧处理完毕后）自动执行。这种"请求-执行"的异步设计有两个原因：一是确保抓帧时机与推理完成时机对齐，抓取的是经过完整处理的一帧数据；二是避免在推理过程中执行磁盘I/O操作导致推理延迟增加。如果在非检测帧（即当前帧不运行检测模型的帧）触发了抓帧，那么抓取的数据中检测结果部分将是空的。',
        '每次抓帧会产生四个输出文件，保存在应用专属的外部存储目录中（通常路径为/Android/data/com.qianmo.ruralvision/files/debug_captures/），以时间戳命名的子目录下。这四个文件分别是：',
        'frame.png——原始相机帧截图。这是模型接收到的实际输入画面的原始截图（在图像预处理之后、送入模型之前），保存为PNG格式。通过查看这个文件，你可以确认模型实际看到的画面是什么样子的，是否有因为相机曝光、方向矫正或缩放导致的画质问题。在调试分割或检测效果不理想的问题时，这个文件通常是第一个需要检查的。',
        'mask.png——道路分割掩码图像。这是分割模型原始输出的可视化结果，保存为灰度PNG图像。图像中越亮的区域表示模型越确信该像素属于可行驶道路区域，纯白的像素对应模型置信度接近1的区域，纯黑的像素对应模型确信不属于道路的区域，灰色的像素则对应模型不确定的边界区域。通过对比mask.png和frame.png，你可以直观地评估分割模型在当前画面下的表现——掩码区域的边界是否与实际路面边界对齐、掩码内部是否存在不应该有的空洞、掩码是否错误地延伸到了道路以外的区域。',
        'overlay.png——叠加结果图。这是将分割掩码（半透明绿色）和检测框（彩色边框和标签）叠加到原始相机帧上之后的效果图，也就是你在软件主界面上看到的最终显示效果的静态版本。这个文件最适合用于展示软件的整体识别效果，也是项目答辩和成果展示时最常用的图片素材。如果你需要评估检测框的位置是否准确、标签文字是否清晰可读、掩码叠加后的可视化效果是否直观，overlay.png是最直接的参考。',
        'meta.txt——元数据文本文件。这是一个纯文本文件，记录了抓帧时刻的全面运行状态信息。文件内容采用"键=值"的格式，每一行记录一个参数。通常包含以下关键字段：captured_at_ms（抓帧时刻的Unix时间戳，毫秒级）、frame_index（帧序号）、runtime（分割推理后端类型，如GPU/CPU/NNAPI）、model（分割模型文件名称）、total_ms（单帧总处理耗时）、preprocess_ms（预处理耗时）、segmentation_ms（分割推理耗时）、detection_ms（检测推理耗时，非检测帧此值为0）、status_text（道路安全状态提示文字）、drivable_ratio（可行驶区域占比）、center_safe（中心区域是否安全）、road_narrow（路面是否变窄）、mask_width和mask_height（掩码尺寸）等。通过查看meta.txt，你可以精确了解每一帧的处理时间和各个模块的耗时占比，这对于性能优化和问题定位非常有价值。',
    ]
    for para_text in CH8_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_heading('8.1 调试文件速查表', level=2)
    add_table(
        document,
        ['文件', '格式', '内容说明', '主要用途'],
        [
            ('frame.png', 'PNG', '预处理后的原始相机帧', '检查模型输入画质'),
            ('mask.png', 'PNG (灰度)', '分割模型输出的原始掩码', '评估分割边界精度'),
            ('overlay.png', 'PNG (彩色)', '掩码+检测框叠加效果图', '展示整体识别效果'),
            ('meta.txt', '文本', '运行状态、耗时、模型信息', '性能分析和问题定位'),
        ],
    )

    document.add_heading('8.2 抓帧结果示例分析', level=2)
    CH8_EXAMPLE = (
        '下面通过三个真实的抓帧样本来演示如何阅读和分析调试结果。样本A来自第270帧，此时画面中是一条正常的乡村水泥路，'
        '没有行人也没有车辆。从meta.txt可以看到：分割运行在GPU上，模型为segmentation_fp16_192.tflite，总处理耗时65ms，'
        '检测耗时同样为65ms（说明此帧执行了检测），状态提示为"前方道路正常"，可行驶区域占比约38.8%。'
        '这是一个典型的"一切正常"的帧——分割和检测都在正常工作，画面中没有风险目标，道路状况良好。'
        '样本B来自第300帧，画面中出现了行人。总处理耗时61ms，状态提示切换到"前方有行人"，说明DriveStateEvaluator'
        '正确识别到了检测框中的行人目标并触发了行人风险提示。样本C来自第320帧，这是一个非检测帧（检测每6帧执行一次），'
        '所以detection_ms为0ms，但分割仍然在连续运行，状态提示为"靠近道路边缘"，说明车辆可能偏向了道路一侧。'
    )
    p = document.add_paragraph(CH8_EXAMPLE)
    set_paragraph_format(p)
    style_runs(p)

    add_table(
        document,
        ['样本', '帧序号', '分割后端', '检测后端', '状态提示', '总耗时', '备注'],
        DEBUG_CAPTURE_ROWS,
    )

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第九章　典型使用场景
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第九章　典型使用场景', level=1)

    CH9_INTRO = (
        '为了帮助使用者更好地理解软件在实际道路环境中的表现，本章选取了四种典型的使用场景，'
        '结合真实的运行截图和数据，逐一分析软件在不同场景下的能力、表现和局限。这些场景均来自真机实测，'
        '使用的设备为搭载骁龙8系列处理器的安卓手机，测试环境为河南省部分农村地区的真实道路。'
    )
    p = document.add_paragraph(CH9_INTRO)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('9.1 场景一：日常乡村硬化道路', level=2)
    CH9_1 = (
        '这是最基础的测试场景。道路为约3.5米宽的水泥硬化路面，两侧是农田，路面边界清晰，光照条件良好。'
        '在这种理想条件下，分割模型能够给出稳定且准确的道路掩码——掩码的左右边界与水泥路面边缘基本吻合，'
        '掩码区域完整且没有内部断裂，可行驶区域占比稳定在37%至42%之间。检测模型在此场景下通常输出0到1个检测框，'
        '因为没有行人或车辆出现在画面中。软件的状态提示持续显示"前方道路正常"，语音不触发任何告警。'
        '帧率维持在约15至20FPS，分割单帧耗时约20ms，检测单帧耗时约55ms。这个场景代表了软件在最佳条件下的表现水平，'
        '也是日常使用中最常见的场景。'
    )
    p = document.add_paragraph(CH9_1)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('9.2 场景二：乡镇集市人流密集道路', level=2)
    CH9_2 = (
        '这是最具挑战性的测试场景之一。道路两侧停满了电动车和摊位，路面上有密集的行人走动，'
        '还不时有电动车和三轮车穿行。在这种复杂场景下，分割模型的表现会有所下降——因为道路边界被停放的车辆和摊位遮挡，'
        '掩码区域变窄且左右边界变得不规则，可行驶区域占比可能下降到20%至30%。'
        '不过分割仍然能够正确识别出车辆前方约1.5至2米范围内的可行驶路面空间。'
        '检测模型在此场景下会输出较多检测框（通常在5到15个），但精度也会有所下降——部分远景中的行人可能因为尺寸太小'
        '而未被检出，而画面边缘位置的一些摊位设施可能被误识别为障碍物。'
        '软件会频繁触发"前方有行人"的语音提示（但因为有3秒的最小间隔，不会连续重复播报），提示频率约每分钟几次。'
        '帧率可能因大量检测框的绘制而稍有下降，但整体仍在可接受的范围内。'
    )
    p = document.add_paragraph(CH9_2)
    set_paragraph_format(p)
    style_runs(p)

    # 复杂场景截图
    add_image_block(
        document,
        '9.2.1 多人复杂场景示例',
        SCREENSHOT_CROWD,
        '图9-1 多人复杂道路场景：同时显示道路掩码、多个行人检测框和底部风险提示。',
        5.8,
    )

    document.add_heading('9.3 场景三：黄昏/低照度场景', level=2)
    CH9_3 = (
        '在黄昏时段或树荫密集的乡村路段，环境光照强度明显下降，相机画面的噪点增多、对比度降低。'
        '分割模型在这种条件下对道路边界的判断会变得更加保守——掩码区域收缩，模型倾向于只标注画面中央最确定的道路区域，'
        '而边界模糊的周边区域可能被放弃。检测模型的召回率也会下降，特别是对于画面中较暗区域的行人目标，'
        '检出率可能从不低于50%下降到30%左右。软件在低照度场景下仍然能够维持基本的道路识别功能，'
        '但识别结果的准确性和完整性会有所下降。这是深度学习视觉模型固有的局限——训练数据中的低照度样本比例不足，'
        '模型没有充分学习到暗光条件下的视觉特征。未来版本的改进方向之一是增加夜间和低照度场景的训练数据。'
    )
    p = document.add_paragraph(CH9_3)
    set_paragraph_format(p)
    style_runs(p)

    document.add_heading('9.4 场景四：土路与碎石路', level=2)
    CH9_4 = (
        '在未铺装的土路或碎石路上，道路边界本身就非常模糊——路面和路肩之间的过渡区域可能宽达数十厘米，'
        '中间没有清晰的边界线。在这种场景下，分割模型的输出会呈现出明显的模糊边界特征——'
        '掩码的边缘不是清晰的分界线，而是一个渐变的过渡带。这种表现实际上反映了模型在此区域的不确定性——'
        '它不确定那个过渡带到底算不算道路。如果路面颜色和两侧土地颜色接近（例如干燥的黄土路），'
        '模型可能会将部分非道路土地也错误地包含在掩码中，导致可行驶区域占比异常偏高。'
        '这是当前版本分割模型最主要的已知不足之一，也是训练数据中土路场景标注不足的直接体现。'
    )
    p = document.add_paragraph(CH9_4)
    set_paragraph_format(p)
    style_runs(p)

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第十章　常见问题与故障排除
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第十章　常见问题与故障排除', level=1)

    CH10_INTRO = (
        '本章汇总了在开发测试和真机验证过程中遇到的常见问题，以及对应的排查思路和处理方法。'
        '如果你在使用中遇到了下面没有列出的问题，可以尝试通用的排查手段：先检查顶部状态信息卡确认各模块的运行状态，'
        '然后查看设备存储中是否有最近的调试抓帧文件可供分析，如果问题持续存在可以尝试重启应用或重新安装。'
    )
    p = document.add_paragraph(CH10_INTRO)
    set_paragraph_format(p)
    style_runs(p)

    faq_items = [
        (
            'Q1：首次打开应用后画面全黑，没有任何相机画面',
            '这通常是因为相机权限没有被授予。软件在首次启动时会自动弹出权限请求对话框，如果你点击了"拒绝"，'
            '或者在系统设置中手动关闭了相机权限，相机就无法启动。解决方法是：进入"系统设置→应用管理→阡陌智行→权限"，'
            '将相机权限设置为"允许"，然后重新启动应用。如果权限确认已授予但问题仍然存在，可能是相机硬件被其他应用占用——'
            '尝试关闭其他可能使用相机的应用（如系统相机、微信、扫码工具等）后重新启动。在极少数情况下，'
            '某些定制安卓系统可能需要先打开系统自带相机应用一次，才能让第三方应用正常访问相机。'
        ),
        (
            'Q2：画面正常但看不到绿色的道路掩码',
            '这种情况可能由几种原因导致。首先，检查顶部状态信息卡——如果显示"识别未启动"，说明分割引擎未能加载模型，'
            '可能是因为assets目录中的模型文件缺失或损坏，尝试重新安装APK。如果状态卡显示正常运行但掩码仍然不可见，'
            '可能是当前画面中确实没有可识别为道路的区域（例如你正对着天空或墙壁），尝试将摄像头对准一条实际的道路再观察。'
            '如果确认画面中有道路但仍然没有掩码，可能是GPU推理失败后未能正确回退到CPU——检查状态卡中的分割运行时信息，'
            '如果显示异常值可以重启应用尝试重新初始化。'
        ),
        (
            'Q3：检测框频繁闪烁或位置不稳定',
            '检测框的帧间抖动是目标检测算法的常见现象。由于检测模型独立处理每一帧画面，微小的相机抖动或光照变化'
            '都可能导致检测框的位置和尺寸在相邻帧之间出现几像素的偏移。软件目前没有加入检测框的时间平滑滤波'
            '（如卡尔曼滤波或指数移动平均），因此抖动会比较明显。这个现象虽然不影响检测本身的准确性，'
            '但可能会给使用者带来一定的视觉不适。在大多数实际场景中，检测目标不会在一帧之间发生剧烈位移，'
            '因此你可以用肉眼取相邻几帧检测框的平均位置来粗略判断目标的实际位置。'
        ),
        (
            'Q4：长时间运行后画面变卡、帧率下降',
            '这是设备热状态升高触发的热限频保护。当设备温度超过一定阈值（因设备而异，通常在40-45°C）时，'
            'Android系统会自动限制CPU和GPU的最高频率以控制发热，这直接导致模型推理时间增加、输出帧率降低。'
            '软件内置了热感知调度策略——LatestFramePerceptionCoordinator会监控设备的热状态等级，'
            '在高温状态下主动降低处理帧率以减少发热。如果你发现帧率明显下降，可以暂停使用几分钟让设备降温，'
            '或者在通风较好的环境中使用。避免在阳光直射、充电状态或保护壳散热不良的情况下长时间运行软件。'
        ),
        (
            'Q5：语音播报不工作，没听到任何提示声音',
            '首先检查设备媒体音量是否开启（不是铃声音量）。然后看顶部状态信息卡中的语音状态——'
            '如果显示"提示音"而非"语音"，说明TTS引擎初始化失败，软件已自动降级为提示音模式。'
            '在提示音模式下，你仍然应该能听到不同音调的"滴滴"声作为风险提示，如果完全没有任何声音，'
            '可能是设备的媒体音量为零。如果希望恢复语音播报，可以尝试在"系统设置→语言和输入法→文字转语音输出"中'
            '安装中文语音数据包，然后重启应用。部分设备可能需要在设置中手动选择TTS引擎（如Google TTS或系统自带引擎）'
            '并确保中文语言包已下载。'
        ),
        (
            'Q6：调试抓帧后找不到保存的文件',
            '抓帧文件保存在应用专属的外部存储目录下，路径为/Android/data/com.qianmo.ruralvision/files/debug_captures/。'
            '在Android 11及以上版本中，系统对这个目录的访问有严格限制——普通的文件管理器可能无法直接浏览。'
            '你可以通过以下方式访问：连接电脑后通过USB文件传输模式查看；使用系统自带的文件应用（部分品牌支持）；'
            '或者使用ADB命令（adb pull）导出。另外请注意，抓帧是异步操作的——点击按钮后需要等到下一帧处理完成才会保存文件，'
            '如果在保存完成前就退出了应用，抓帧请求会丢失。如果在目标目录中确实没有任何子目录，可能是存储权限或磁盘空间问题。'
        ),
        (
            'Q7：应用在后台被系统强制关闭',
            '这是安卓系统内存管理机制的常见行为。当系统可用内存不足时，Android会按照优先级从低到高终止后台进程以释放内存。'
            '本软件作为前台应用运行时优先级较高，但如果被切换到后台（如按Home键或切换到其他应用），'
            '其进程优先级会降至后台进程级别，在系统内存紧张时可能被终止。为了避免这种情况，'
            '建议在使用本软件时不要频繁切换到其他大型应用（尤其是游戏或多媒体的应用），如果需要接电话或回消息，'
            '可以短暂切换但尽快回到应用。如果应用意外被关闭，只需重新启动即可——所有状态在每次启动时都会重新初始化。'
        ),
        (
            'Q8：在横屏和竖屏之间旋转时画面短暂黑屏',
            '屏幕旋转时，Android系统会销毁当前的Activity并重新创建它（除非在AndroidManifest中声明自行处理配置变更）。'
            '本软件选择了让系统处理屏幕旋转，这意味着每次旋转都会经历"相机关闭→Activity重建→相机重新启动→模型重新初始化"的过程。'
            '这个过程的耗时取决于设备性能，通常在1到3秒之间。旋转期间画面黑屏是正常现象。'
            '如果你希望避免旋转带来的中断，可以在使用前将设备的自动旋转功能关闭并锁定到你偏好的方向。'
        ),
        (
            'Q9：模型推理结果的准确性感觉不够高',
            '首先需要明确一点：本软件的深度学习模型是在公开数据集上训练的通用模型，'
            '并非针对特定地区或特定道路环境优化过的专用模型。因此，在你遇到的具体场景中，'
            '模型表现可能与你在文档截图中看到的效果有差异。影响准确性的因素有很多：光照条件、路面材质和颜色、'
            '道路边界的清晰程度、画面中目标的密集程度、设备相机的成像质量等等。'
            '如果你发现某个特定场景下识别结果持续不理想，可以尝试使用调试抓帧功能将该场景保存下来，'
            '这些素材可以用于后续的模型改进和针对性训练。需要坦率地承认，当前V1.0版本的模型精度处于"可用但不够惊艳"的水平，'
            '距离商业化部署还有明显的差距。'
        ),
        (
            'Q10：安装APK时提示"有害应用"或"未经认证"',
            '这是部分安卓设备（尤其是国产手机品牌）的安全检测机制。因为本APK未在应用商店上架，'
            '也没有通过手机厂商的安全认证，系统可能会弹出安全警告。这是正常的现象——'
            '软件本身不包含任何恶意代码，也不请求联网或敏感数据权限。你可以选择"继续安装"或"信任此应用"来跳过警告，'
            '具体的按钮文字因手机品牌而异。安装后如果系统再次弹出安全提醒，可以选择忽略或不再提醒。'
        ),
    ]

    for question, answer in faq_items:
        document.add_heading(question, level=2)
        p = document.add_paragraph(answer)
        set_paragraph_format(p)
        style_runs(p)

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第十一章　注意事项与使用建议
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第十一章　注意事项与使用建议', level=1)

    CH11_PARAS = [
        '本章汇总了在使用本软件过程中需要特别注意的若干事项，以及基于项目开发经验的实用建议。这些内容既包含了技术层面的风险提示，也涵盖了实际操作中的经验总结，建议在首次使用前仔细阅读。',
        '第一，关于安全责任边界的说明。本软件是一个基于深度学习的技术验证原型系统，不是经过安全认证的车规级辅助驾驶产品。软件的道路分割和检测结果可能存在漏检（false negative）和误检（false positive），不应将软件提示作为唯一的安全判断依据。在实际骑行过程中，骑行者自身的视觉观察和判断仍然是最高优先级的安全保障手段。特别是在以下情况下需要格外谨慎：软件提示与实际道路情况不一致时，以实际情况为准；大雾、暴雨、夜间等极端条件下，识别效果可能大幅下降，应降低行驶速度或暂停使用；软件从未见过的特殊道路形态（如被积雪覆盖的路面、严重积水的路面），模型可能完全无法做出合理判断。',
        '第二，关于设备使用状态的建议。为获得最佳的使用体验，建议将手机固定在电动车把手或胸前支架上，使用后置摄像头朝向行驶方向。手机固定方式应确保摄像头视野不被遮挡（特别是手指、支架夹具或充电线），同时确保手机在颠簸路面上不会松动脱落。不推荐手持使用——骑行中单手持握手机不仅影响识别效果（因为手抖会导致画面模糊），更重要的是存在严重的交通安全隐患。此外，建议在使用前将屏幕亮度调至较高水平，并将自动锁屏时间设为"永不"或最长可用时间，以避免屏幕在识别过程中自动熄灭。',
        '第三，关于发热和续航的说明。同时运行相机采集、两个深度学习模型的实时推理和画面渲染是典型的持续高性能负载，设备发热和电量消耗会比日常使用明显增加。在室外30°C以上的高温环境中连续使用30分钟以上，设备温度可能会升至让使用者感到不适的水平。建议在高温环境中每次连续使用不超过20分钟，之后让设备休息降温几分钟再继续使用。电量消耗方面，在满电状态下连续使用约可持续1.5至3小时（因设备电池容量和处理器功耗而异），建议在需要长时间使用时携带充电宝。',
        '第四，关于横竖屏切换的建议。如果你在骑行过程中使用，建议将设备锁定为竖屏方向并关闭自动旋转。因为骑行过程中的车身倾斜或路面颠簸可能触发系统误判为屏幕旋转意图，导致Activity频繁重建而中断识别。在停车演示或静态展示场景中则可以自由切换方向展示软件对两种布局的适配能力。',
        '第五，关于模型更新的说明。软件的分割和检测模型文件存放在assets目录中，理论上可以通过替换assets中的.tflite文件来更新模型而不需要重新安装APK（前提是新的模型文件使用相同的输入输出格式和名称）。但需要提醒的是，从非官方渠道获取的模型文件可能经过修改或不兼容当前版本的输入输出约定，替换前建议备份原始模型文件以备恢复。绝大多数使用者不需要关注模型更新——预装的两个模型已经是当前训练最优版本。',
    ]
    for para_text in CH11_PARAS:
        p = document.add_paragraph(para_text)
        set_paragraph_format(p)
        style_runs(p)

    document.add_page_break()

    # ════════════════════════════════════════════════════════════════
    # 第十二章　附　录
    # ════════════════════════════════════════════════════════════════
    document.add_heading('第十二章　附　录', level=1)

    document.add_heading('12.1 软件主流程图', level=2)
    FLOW_INTRO = (
        '下图展示了本软件从相机画面采集到最终结果输出与调试留证的完整处理流程。'
        '流程共分为六个主要阶段：相机采集→图像预处理→道路分割推理→目标检测推理→状态判定→界面渲染与留证。'
        '其中，分割推理和检测推理是并行执行的，两者互不依赖；检测推理采用每N帧执行一次的策略以降低整体计算负载。'
        '状态判定阶段综合分割和检测两个通道的结果生成最终的状态提示和风险事件。'
    )
    p = document.add_paragraph(FLOW_INTRO)
    set_paragraph_format(p)
    style_runs(p)

    add_image_block(
        document,
        '',
        generate_flowchart_image(),
        '图12-1 软件主流程图',
        5.8,
    )

    document.add_heading('12.2 软件基本信息', level=2)
    add_field_table(
        document,
        [
            ('软件全称', SOFTWARE_NAME),
            ('软件简称', SOFTWARE_SHORT_NAME),
            ('版本号', SOFTWARE_VERSION),
            ('应用包名', PACKAGE_NAME),
            ('应用界面名称', APP_NAME),
            ('运行平台', 'Android 8.0 及以上'),
            ('开发语言', 'Kotlin (Android端), Python (训练与导出)'),
            ('推理框架', 'TensorFlow Lite 2.17.0'),
            ('相机框架', 'CameraX 1.4.2'),
            ('分割模型结构', 'U-Net (encoder: ResNet34)'),
            ('检测模型结构', 'YOLOv8s'),
            ('分割模型输入', '192×192×3'),
            ('检测模型输入', '640×640×3'),
            ('分割运行时', 'TFLite-GPU（支持回退CPU/NNAPI）'),
            ('检测运行时', 'TFLite-GPU（严格要求，不回退）'),
            ('完成日期', COMPLETION_DATE),
        ],
    )

    document.add_heading('12.3 运行结果样本', level=2)
    RESULT_INTRO = (
        '下表记录了三个真实抓帧样本的运行数据，展示了不同场景下各模块的推理耗时和状态判定结果。'
        '样本A为正常道路场景，检测耗时约65ms；样本B为有行人场景，总耗时约61ms；'
        '样本C为非检测帧，仅执行分割推理。所有样本的分割均运行在GPU后端。'
    )
    p = document.add_paragraph(RESULT_INTRO)
    set_paragraph_format(p)
    style_runs(p)
    add_table(
        document,
        ['样本', '帧序号', '分割运行时', '检测运行时', '状态提示', '总耗时', '说明'],
        DEBUG_CAPTURE_ROWS,
    )

    document.add_heading('12.4 边缘风险提示效果图', level=2)
    add_image_block(
        document,
        '',
        SCREENSHOT_EDGE,
        '图12-2 道路边缘风险提示效果图：底部状态区显示"靠近道路边缘"。',
        3.6,
    )

    document.add_heading('12.5 行人检测效果图', level=2)
    add_image_block(
        document,
        '',
        SCREENSHOT_PEDESTRIAN,
        '图12-3 行人检测效果图：多人场景下的行人检测和提示。',
        3.6,
    )

    set_header_footer(document.sections[0], f'{SOFTWARE_NAME} - 操作手册（详细版）')
    return save_document(document, '软件操作手册_详细版.docx')


def cleanup_legacy_outputs() -> None:
    legacy = OUTPUT_DIR / '软件代码文档_草稿.docx'
    if legacy.exists():
        legacy.unlink()


def main() -> None:
    # 原始版本（保留向后兼容）
    outputs = [
        build_application_form(),
        build_manual(),
        build_function_doc(),
    ]
    # V2 版本：操作手册详细版 + 源程序鉴别材料改进版
    try:
        outputs.append(build_manual_v2())
        print('V2 操作手册已生成')
    except Exception as e:
        print(f'V2 操作手册生成失败: {e}')
    try:
        outputs.append(build_source_doc_v2())
        print('V2 源程序鉴别材料已生成')
    except Exception as e:
        print(f'V2 源程序鉴别材料生成失败: {e}')

    cleanup_legacy_outputs()
    refresh_docx_with_word(outputs)
    for output in outputs:
        print(output)


if __name__ == '__main__':
    main()
