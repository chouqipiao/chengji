#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF导出模块 - 将分析结果导出为PDF文档
包含表格、图表和统计分析结果
"""

import pandas as pd

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os
import io

import logging
from typing import Dict, Any

# 设置中文字体支持
try:
    # 尝试注册中文字体
    font_path = os.path.join(os.path.dirname(__file__), "static", "fonts", "simhei.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("SimHei", font_path))
    else:
        # 使用系统默认字体
        pass
except Exception as e:
    # logging may not be configured at import time; use local import to avoid NameError
    try:
        import logging as _logging

        _logging.getLogger(__name__).debug(f"中文字体注册失败: {e}")
    except Exception:
        # best-effort logging; swallow to avoid import-time failure
        pass

# 配置Plotly静态图片导出（兼容性处理）
try:
    # 使用新的API设置mathjax
    if hasattr(pio, 'defaults') and hasattr(pio.defaults, 'mathjax'):
        pio.defaults.mathjax = None
    elif pio.kaleido.scope is not None:
        # 兼容旧版本API（已弃用）
        pio.kaleido.scope.mathjax = None
except AttributeError:
    # 兼容不同版本的kaleido
    pass

logger = logging.getLogger(__name__)


class PDFExporter:
    """PDF导出器类"""

    def __init__(self, output_path: str):
        """
        初始化PDF导出器

        Args:
            output_path: PDF输出路径
        """
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        self.styles = getSampleStyleSheet()
        self.elements = []
        self._setup_chinese_styles()

    def _setup_chinese_styles(self):
        """设置中文字体样式"""
        try:
            # 尝试使用系统中文字体
            chinese_fonts = [
                "SimHei",
                "SimSun",
                "Microsoft YaHei",
                "Arial Unicode MS",
            ]
            font_name = "Helvetica"  # 默认字体

            # 测试可用的中文字体
            for font in chinese_fonts:
                try:
                    pdfmetrics.registerFont(TTFont(font, f"{font}.ttf"))
                    font_name = font
                    logger.info(f"成功注册中文字体: {font}")
                    break
                except Exception:
                    try:
                        # 尝试系统字体路径
                        import sys

                        if sys.platform == "win32":
                            font_paths = [
                                f"C:/Windows/Fonts/{font}.ttf",
                                f"C:/Windows/Fonts/{font}.ttc",
                                f"C:/Windows/Fonts/{font} Regular.ttf",
                            ]
                            for font_path in font_paths:
                                if os.path.exists(font_path):
                                    pdfmetrics.registerFont(TTFont(font, font_path))
                                    font_name = font
                                    logger.info(f"成功注册系统中文字体: {font}")
                                    break
                    except Exception as e2:
                        logger.debug(f"尝试注册系统字体时出错: {e2}")

            # 创建支持中文的样式
            self.styles.add(
                ParagraphStyle(
                    name="ChineseTitle",
                    parent=self.styles["Title"],
                    fontName=font_name,
                    fontSize=18,
                    textColor=colors.darkblue,
                    alignment=1,  # 居中
                )
            )

            self.styles.add(
                ParagraphStyle(
                    name="ChineseHeading",
                    parent=self.styles["Heading1"],
                    fontName=font_name,
                    fontSize=14,
                    textColor=colors.darkgreen,
                )
            )

            self.styles.add(
                ParagraphStyle(
                    name="ChineseNormal",
                    parent=self.styles["Normal"],
                    fontName=font_name,
                    fontSize=10,
                )
            )

            self.styles.add(
                ParagraphStyle(
                    name="ChineseSmall",
                    parent=self.styles["Normal"],
                    fontName=font_name,
                    fontSize=8,
                )
            )

        except Exception as e:
            # 如果中文字体设置失败，使用默认样式
            logger.warning(f"中文字体设置失败，使用默认字体: {e}")
            # 使用默认样式名称
            self.styles.add(
                ParagraphStyle(
                    name="ChineseTitle",
                    parent=self.styles["Title"],
                    fontSize=18,
                    textColor=colors.darkblue,
                    alignment=1,
                )
            )

            self.styles.add(
                ParagraphStyle(
                    name="ChineseHeading",
                    parent=self.styles["Heading1"],
                    fontSize=14,
                    textColor=colors.darkgreen,
                )
            )

            self.styles.add(
                ParagraphStyle(
                    name="ChineseNormal",
                    parent=self.styles["Normal"],
                    fontSize=10,
                )
            )

            self.styles.add(
                ParagraphStyle(
                    name="ChineseSmall",
                    parent=self.styles["Normal"],
                    fontSize=8,
                )
            )

    def add_title(self, title: str, level: int = 1):
        """
        添加标题

        Args:
            title: 标题文本
            level: 标题级别 (1-3)
        """
        try:
            if level == 1:
                style = "ChineseTitle" if "ChineseTitle" in self.styles else "Title"
            elif level == 2:
                style = (
                    "ChineseHeading" if "ChineseHeading" in self.styles else "Heading1"
                )
            else:
                style = (
                    "ChineseNormal" if "ChineseNormal" in self.styles else "Heading2"
                )

            self.elements.append(Paragraph(title, self.styles[style]))
            self.elements.append(Spacer(1, 0.3 * cm))
        except Exception as e:
            logger.error(f"添加标题失败: {e}")

    def add_paragraph(self, text: str):
        """
        添加段落

        Args:
            text: 段落文本
        """
        try:
            style = "ChineseNormal" if "ChineseNormal" in self.styles else "Normal"
            self.elements.append(Paragraph(text, self.styles[style]))
            self.elements.append(Spacer(1, 0.2 * cm))
        except Exception as e:
            logger.error(f"添加段落失败: {e}")

    def add_dataframe_table(
        self, df: pd.DataFrame, title: str = None, max_rows: int = 20
    ):
        """
        添加DataFrame表格

        Args:
            df: pandas DataFrame
            title: 表格标题
            max_rows: 最大显示行数
        """
        try:
            if title:
                self.add_title(title, level=2)

            # 限制行数
            if len(df) > max_rows:
                display_df = df.head(max_rows).copy()
                # 添加省略行
                ellipsis_row = {col: "..." for col in df.columns}
                display_df = pd.concat(
                    [display_df, pd.DataFrame([ellipsis_row])],
                    ignore_index=True,
                )
                # 添加总计行
                total_row = {
                    col: f"共{len(df)}行" if i == 0 else ""
                    for i, col in enumerate(df.columns)
                }
                display_df = pd.concat(
                    [display_df, pd.DataFrame([total_row])], ignore_index=True
                )
            else:
                display_df = df.copy()

            # 转换数据为字符串
            for col in display_df.columns:
                display_df[col] = display_df[col].astype(str).replace("nan", "-")

            # 准备表格数据
            data = [display_df.columns.tolist()] + display_df.values.tolist()

            # 创建表格
            table = Table(data)

            # 设置表格样式
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ]
                )
            )

            self.elements.append(table)
            self.elements.append(Spacer(1, 0.5 * cm))

        except Exception as e:
            logger.error(f"添加表格失败: {e}")
            self.add_paragraph(f"表格生成失败: {str(e)}")

    def add_plotly_figure(
        self, fig, title: str = None, width: int = 400, height: int = 300
    ):
        """
        添加Plotly图表

        Args:
            fig: Plotly图表对象
            title: 图表标题
            width: 图片宽度
            height: 图片高度
        """
        try:
            if title:
                self.add_title(title, level=2)

            # 将Plotly图表转换为图片
            img_bytes = pio.to_image(fig, format="png", width=width, height=height)

            # 创建临时图片文件
            img_buffer = io.BytesIO(img_bytes)

            # 添加到PDF
            img = Image(img_buffer, width=width, height=height)
            self.elements.append(img)
            self.elements.append(Spacer(1, 0.3 * cm))

        except Exception as e:
            logger.error(f"添加Plotly图表失败: {e}")
            self.add_paragraph(f"图表生成失败: {str(e)}")

    def add_matplotlib_figure(
        self, fig, title: str = None, width: int = 400, height: int = 300
    ):
        """
        添加Matplotlib图表

        Args:
            fig: Matplotlib图表对象
            title: 图表标题
            width: 图片宽度
            height: 图片高度
        """
        try:
            if title:
                self.add_title(title, level=2)

            # 保存图表到内存
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
            img_buffer.seek(0)

            # 添加到PDF
            img = Image(img_buffer, width=width, height=height)
            self.elements.append(img)
            self.elements.append(Spacer(1, 0.3 * cm))

            # 关闭图表
            plt.close(fig)

        except Exception as e:
            logger.error(f"添加Matplotlib图表失败: {e}")
            self.add_paragraph(f"图表生成失败: {str(e)}")

    def add_page_break(self):
        """添加分页符"""
        self.elements.append(PageBreak())

    def add_analysis_summary(self, analysis_data: Dict[str, Any]):
        """
        添加分析结果摘要

        Args:
            analysis_data: 分析数据字典
        """
        try:
            self.add_title("分析结果摘要", level=2)

            # 基本统计信息
            if "basic_stats" in analysis_data:
                stats = analysis_data["basic_stats"]
                self.add_paragraph("基本统计信息:")

                stats_text = []
                for key, value in stats.items():
                    if isinstance(value, (int, float)):
                        stats_text.append(f"{key}: {value:.2f}")
                    else:
                        stats_text.append(f"{key}: {value}")

                self.add_paragraph(" | ".join(stats_text))

            # 数据概览
            if "data_overview" in analysis_data:
                overview = analysis_data["data_overview"]
                self.add_paragraph("数据概览:")

                for key, value in overview.items():
                    self.add_paragraph(f"  {key}: {value}")

            self.elements.append(Spacer(1, 0.3 * cm))

        except Exception as e:
            logger.error(f"添加分析摘要失败: {e}")

    def generate_pdf(self) -> str:
        """
        生成PDF文档

        Returns:
            str: 生成的PDF文件路径
        """
        try:
            self.doc.build(self.elements)
            logger.info(f"PDF文档生成成功: {self.output_path}")
            return self.output_path
        except Exception as e:
            logger.error(f"PDF文档生成失败: {e}")
            raise


def export_comprehensive_analysis_to_pdf(
    raw_data: pd.DataFrame, analysis_results: Dict[str, Any], output_path: str
) -> str:
    """
    导出综合分析结果到PDF

    Args:
        raw_data: 原始数据
        analysis_results: 分析结果
        output_path: 输出路径

    Returns:
        str: PDF文件路径
    """
    try:
        exporter = PDFExporter(output_path)

        # 添加文档标题
        exporter.add_title("成绩分析报告 - 综合分析", level=1)
        exporter.add_paragraph(
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        exporter.add_paragraph(f"数据样本数: {len(raw_data)}")
        exporter.add_paragraph(f"分析维度: {len(raw_data.columns)}")

        # 添加数据概览
        exporter.add_title("数据概览", level=1)
        exporter.add_dataframe_table(raw_data.describe(), "基本统计信息")

        # 添加分析结果摘要
        exporter.add_analysis_summary(analysis_results)

        # 添加详细数据表
        if "detailed_results" in analysis_results:
            detailed_df = pd.DataFrame(analysis_results["detailed_results"])
            exporter.add_dataframe_table(detailed_df, "详细分析结果")

        # 添加图表
        if "figures" in analysis_results:
            for fig_name, fig_data in analysis_results["figures"].items():
                if isinstance(fig_data, (go.Figure, px.Figure)):
                    exporter.add_plotly_figure(fig_data, f"{fig_name}图表")

        # 生成PDF
        return exporter.generate_pdf()

    except Exception as e:
        logger.error(f"导出综合分析PDF失败: {e}")
        raise


def export_quadrant_analysis_to_pdf(
    raw_data: pd.DataFrame, quadrant_results: Dict[str, Any], output_path: str
) -> str:
    """
    导出四象限分析结果到PDF

    Args:
        raw_data: 原始数据
        quadrant_results: 四象限分析结果
        output_path: 输出路径

    Returns:
        str: PDF文件路径
    """
    try:
        exporter = PDFExporter(output_path)

        # 添加文档标题
        exporter.add_title("成绩分析报告 - 四象限分析", level=1)
        exporter.add_paragraph(
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        exporter.add_paragraph(f"数据样本数: {len(raw_data)}")

        # 添加分析参数
        if "analysis_params" in quadrant_results:
            params = quadrant_results["analysis_params"]
            exporter.add_title("分析参数", level=2)
            for key, value in params.items():
                exporter.add_paragraph(f"{key}: {value}")

        # 添加四象限分布表
        if "quadrant_distribution" in quadrant_results:
            dist_df = pd.DataFrame(quadrant_results["quadrant_distribution"])
            exporter.add_dataframe_table(dist_df, "四象限分布统计")

        # 添加四象限图表
        if "quadrant_figure" in quadrant_results:
            exporter.add_plotly_figure(
                quadrant_results["quadrant_figure"],
                "四象限分布图",
                width=500,
                height=400,
            )

        # 添加详细分析表
        if "quadrant_details" in quadrant_results:
            details_df = pd.DataFrame(quadrant_results["quadrant_details"])
            exporter.add_dataframe_table(details_df, "四象限详细分析")

        # 生成PDF
        return exporter.generate_pdf()

    except Exception as e:
        logger.error(f"导出四象限分析PDF失败: {e}")
        raise


def export_cascade_statistics_to_pdf(
    raw_data: pd.DataFrame, cascade_results: Dict[str, Any], output_path: str
) -> str:
    """
    导出三级联动统计结果到PDF

    Args:
        raw_data: 原始数据
        cascade_results: 三级联动统计结果
        output_path: 输出路径

    Returns:
        str: PDF文件路径
    """
    try:
        exporter = PDFExporter(output_path)

        # 添加文档标题
        exporter.add_title("成绩分析报告 - 三级联动统计", level=1)
        exporter.add_paragraph(
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        exporter.add_paragraph(f"数据样本数: {len(raw_data)}")

        # 添加统计概览
        if "statistics_overview" in cascade_results:
            overview = cascade_results["statistics_overview"]
            exporter.add_title("统计概览", level=2)
            for key, value in overview.items():
                exporter.add_paragraph(f"{key}: {value}")

        # �添加详细统计表
        if "detailed_statistics" in cascade_results:
            stats_df = pd.DataFrame(cascade_results["detailed_statistics"])
            exporter.add_dataframe_table(stats_df, "详细统计数据")

        # 添加统计图表
        if "statistics_figures" in cascade_results:
            for fig_name, fig_data in cascade_results["statistics_figures"].items():
                if isinstance(fig_data, (go.Figure, px.Figure)):
                    exporter.add_plotly_figure(fig_data, f"{fig_name}统计图")

        # 生成PDF
        return exporter.generate_pdf()

    except Exception as e:
        logger.error(f"导出三级联动统计PDF失败: {e}")
        raise


def export_goal_completion_to_pdf(
    goal_completion_results: Dict[str, Any], output_path: str
) -> str:
    """
    导出目标完成分析结果到PDF

    Args:
        goal_completion_results: 目标完成分析结果
        output_path: 输出路径

    Returns:
        str: PDF文件路径
    """
    try:
        exporter = PDFExporter(output_path)

        # 添加文档标题
        exporter.add_title("目标完成统计分析报告", level=1)
        exporter.add_paragraph(
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 添加目标完成分析结果
        for goal_type, results in goal_completion_results.items():
            if isinstance(results, dict) and "basic_stats" in results:
                basic = results["basic_stats"]

                exporter.add_page_break()
                exporter.add_title(
                    f"{basic.get('goal_name', goal_type)}分析结果", level=2
                )

                # 基本统计信息
                exporter.add_paragraph("基本统计信息:")
                basic_stats = [
                    f"目标类型: {basic.get('goal_name', goal_type)}",
                    f"分数线: {basic.get('line_score', 0)}",
                    f"分析科目: {basic.get('target_column', '')}",
                    f"总学生数: {basic.get('total_students', 0)}",
                    f"达标人数: {basic.get('reached_students', 0)}",
                    f"达标率: {basic.get('reach_rate', 0):.2f}%",
                    f"平均分: {basic.get('avg_score', 0):.2f}",
                    f"最高分: {basic.get('max_score', 0):.2f}",
                    f"最低分: {basic.get('min_score', 0):.2f}",
                    f"标准差: {basic.get('std_score', 0):.2f}",
                    f"与线差距: {basic.get('score_gap_to_line', 0):.2f}",
                ]

                for stat in basic_stats:
                    exporter.add_paragraph(f"  {stat}")

                # 层级统计
                if "hierarchy_stats" in results and results["hierarchy_stats"]:
                    exporter.add_title("分层统计分析", level=3)

                    for level, groups in results["hierarchy_stats"].items():
                        exporter.add_paragraph(f"{level}层级统计:")

                        # 创建层级统计表格数据
                        table_data = [
                            ["分组", "总人数", "完成人数", "完成率", "平均分"]
                        ]

                        for group_name, stats in groups.items():
                            table_data.append(
                                [
                                    str(group_name),
                                    str(stats.get("total_count", 0)),
                                    str(stats.get("reached_count", 0)),
                                    f"{stats.get('reach_rate', 0):.2f}%",
                                    f"{stats.get('avg_score', 0):.2f}",
                                ]
                            )

                        exporter.add_table(table_data, f"{level}层级统计表")

                # 分布分析
                if "distribution_stats" in results:
                    dist_stats = results["distribution_stats"]
                    exporter.add_title("分数分布分析", level=3)

                    exporter.add_paragraph(
                        f"目标线位置: {dist_stats.get('target_position', 0)}"
                    )
                    exporter.add_paragraph(
                        f"低于目标人数: {dist_stats.get('below_target', 0)}"
                    )
                    exporter.add_paragraph(
                        f"高于目标人数: {dist_stats.get('above_target', 0)}"
                    )

                    # 分数区间分布
                    if "score_ranges" in dist_stats:
                        exporter.add_paragraph("分数区间分布:")

                        range_data = [["分数区间", "学生数"]]
                        for range_label, count in dist_stats["score_ranges"].items():
                            range_data.append([str(range_label), str(count)])

                        exporter.add_table(range_data, "分数区间分布表")

        # 生成PDF
        return exporter.generate_pdf()

    except Exception as e:
        logger.error(f"导出目标完成分析PDF失败: {e}")
        raise


def create_goal_completion_report(report_text: str) -> bytes:
    """
    根据报告文本创建PDF文档

    Args:
        report_text: str, 报告文本内容

    Returns:
        bytes: PDF文件字节流
    """
    try:
        # 创建临时文件
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            output_path = tmp_file.name

        exporter = PDFExporter(output_path)

        # 添加文档标题
        exporter.add_title("目标完成统计分析报告", level=1)
        exporter.add_paragraph(
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 添加报告内容
        paragraphs = report_text.split("\n")
        for para in paragraphs:
            if para.strip():
                # 处理特殊格式
                if para.startswith("="):
                    continue  # 跳过分隔线
                elif para.startswith("【"):
                    exporter.add_title(para.strip("【】"), level=2)
                elif para.startswith("  "):
                    exporter.add_paragraph(para.strip(), style="BodyText")
                else:
                    exporter.add_paragraph(para)

        # 生成PDF
        exporter.generate_pdf()

        # 读取文件内容
        with open(output_path, "rb") as f:
            pdf_data = f.read()

        # 清理临时文件
        os.unlink(output_path)

        return pdf_data

    except Exception as e:
        logger.error(f"创建目标完成报告PDF失败: {e}")
        raise


def export_complete_analysis_to_pdf(
    raw_data: pd.DataFrame,
    comprehensive_results: Dict[str, Any],
    quadrant_results: Dict[str, Any],
    cascade_results: Dict[str, Any],
    output_path: str,
) -> str:
    """
    导出完整分析报告到PDF

    Args:
        raw_data: 原始数据
        comprehensive_results: 综合分析结果
        quadrant_results: 四象限分析结果
        cascade_results: 三级联动统计结果
        output_path: 输出路径

    Returns:
        str: PDF文件路径
    """
    try:
        exporter = PDFExporter(output_path)

        # 添加文档封面
        exporter.add_title("成绩分析完整报告", level=1)
        exporter.add_paragraph(
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        exporter.add_paragraph(f"数据样本数: {len(raw_data)}")
        exporter.add_paragraph(f"分析维度: {len(raw_data.columns)}")

        # 添加目录
        exporter.add_title("报告目录", level=1)
        exporter.add_paragraph("1. 数据概览")
        exporter.add_paragraph("2. 综合分析结果")
        exporter.add_paragraph("3. 四象限分析结果")
        exporter.add_paragraph("4. 三级联动统计结果")

        exporter.add_page_break()

        # 1. 数据概览
        exporter.add_title("1. 数据概览", level=1)
        exporter.add_dataframe_table(raw_data.head(10), "原始数据(前10行)")
        exporter.add_dataframe_table(raw_data.describe(), "基本统计信息")

        exporter.add_page_break()

        # 2. 综合分析结果
        if comprehensive_results:
            exporter.add_title("2. 综合分析结果", level=1)

            if "detailed_results" in comprehensive_results:
                detailed_df = pd.DataFrame(comprehensive_results["detailed_results"])
                exporter.add_dataframe_table(detailed_df, "综合分析详细结果")

            if "figures" in comprehensive_results:
                for fig_name, fig_data in comprehensive_results["figures"].items():
                    if isinstance(fig_data, (go.Figure, px.Figure)):
                        exporter.add_plotly_figure(fig_data, f"{fig_name}图表")

        exporter.add_page_break()

        # 3. 四象限分析结果
        if quadrant_results:
            exporter.add_title("3. 四象限分析结果", level=1)

            if "quadrant_distribution" in quadrant_results:
                dist_df = pd.DataFrame(quadrant_results["quadrant_distribution"])
                exporter.add_dataframe_table(dist_df, "四象限分布统计")

            if "quadrant_figure" in quadrant_results:
                exporter.add_plotly_figure(
                    quadrant_results["quadrant_figure"],
                    "四象限分布图",
                    width=500,
                    height=400,
                )

            if "quadrant_details" in quadrant_results:
                details_df = pd.DataFrame(quadrant_results["quadrant_details"])
                exporter.add_dataframe_table(details_df, "四象限详细分析")

        exporter.add_page_break()

        # 4. 三级联动统计结果
        if cascade_results:
            exporter.add_title("4. 三级联动统计结果", level=1)

            if "detailed_statistics" in cascade_results:
                stats_df = pd.DataFrame(cascade_results["detailed_statistics"])
                exporter.add_dataframe_table(stats_df, "详细统计数据")

            if "statistics_figures" in cascade_results:
                for fig_name, fig_data in cascade_results["statistics_figures"].items():
                    if isinstance(fig_data, (go.Figure, px.Figure)):
                        exporter.add_plotly_figure(fig_data, f"{fig_name}统计图")

        # 生成PDF
        return exporter.generate_pdf()

    except Exception as e:
        logger.error(f"导出完整分析PDF失败: {e}")
        raise
