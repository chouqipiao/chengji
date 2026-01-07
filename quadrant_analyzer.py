#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版四象限坐标系分析模块
支持本科类和特控类分数线分析
用于分析学生在单科和总分分数线上的分布情况
"""

import pandas as pd
import numpy as np
import json

import logging
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc


def safe_divide(numerator, denominator, default=0):
    """安全的除法运算，避免除零错误"""
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def safe_mean(series):
    """安全的均值计算"""
    try:
        if series.empty or series.isna().all():
            return 0
        return series.mean()
    except (TypeError, ValueError):
        return 0


def safe_std(series):
    """安全的标准差计算"""
    try:
        if series.empty or series.isna().all() or len(series) < 2:
            return 0
        return series.std()
    except (TypeError, ValueError):
        return 0


class QuadrantAnalyzer:
    """增强版四象限分析器"""

    def __init__(self, df=None):
        """
        初始化四象限分析器（支持自定义多指标）

        Args:
            df: DataFrame, 包含学生成绩数据
        """
        self.df = df
        self.subject_column = None
        self.total_column = None
        self.analysis_type = "custom"  # 'basic', 'custom'

        # 自定义指标列表
        self.custom_metrics = (
            []
        )  # 每个指标为字典: {'name': str, 'subject_threshold': float, 'total_threshold': float}

        # 基础分数线（保持兼容性）
        self.subject_threshold = 0
        self.total_threshold = 0

        self.quadrant_stats = {}
        self.custom_stats = {}  # 存储自定义指标统计

        # 数据库功能已移除
        self.db = None
        self.DATABASE_AVAILABLE = False

        # 初始化日志
        self.logger = logging.getLogger(__name__)

    def set_data(self, df):
        """设置数据"""
        self.df = df

    def add_custom_metric(self, name, subject_threshold, total_threshold):
        """
        添加自定义指标

        Args:
            name: str, 指标名称
            subject_threshold: float, 单科分数线
            total_threshold: float, 总分分数线
        """
        metric = {
            "name": name,
            "subject_threshold": subject_threshold,
            "total_threshold": total_threshold,
        }
        self.custom_metrics.append(metric)
        self.analysis_type = "custom"

    def remove_custom_metric(self, index):
        """
        删除自定义指标

        Args:
            index: int, 要删除的指标索引
        """
        if 0 <= index < len(self.custom_metrics):
            self.custom_metrics.pop(index)

    def clear_custom_metrics(self):
        """清空所有自定义指标"""
        self.custom_metrics = []

    def set_custom_metrics(self, metrics_list):
        """
        设置自定义指标列表

        Args:
            metrics_list: list, 指标列表，每个元素为字典格式
        """
        self.custom_metrics = metrics_list.copy()
        if metrics_list:
            self.analysis_type = "custom"
        else:
            self.analysis_type = "basic"

    def get_preset_metrics(self):
        """获取预设指标"""
        return [
            {
                "name": "保底线",
                "subject_threshold": 60,
                "total_threshold": 300,
            },
            {
                "name": "本科线",
                "subject_threshold": 75,
                "total_threshold": 375,
            },
            {
                "name": "重点线",
                "subject_threshold": 80,
                "total_threshold": 425,
            },
            {
                "name": "特控线",
                "subject_threshold": 85,
                "total_threshold": 475,
            },
        ]

    def set_basic_thresholds(
        self, subject_column, total_column, subject_threshold, total_threshold
    ):
        """
        设置基础分析参数

        Args:
            subject_column: str, 单科成绩列名
            total_column: str, 总分列名
            subject_threshold: float, 单科分数线
            total_threshold: float, 总分分数线
        """
        self.subject_column = subject_column
        self.total_column = total_column
        self.subject_threshold = subject_threshold
        self.total_threshold = total_threshold
        self.analysis_type = "basic"

    def set_advanced_thresholds(
        self,
        subject_column,
        total_column,
        subject_basic,
        total_basic,
        subject_undergraduate,
        total_undergraduate,
        subject_special_control,
        total_special_control,
    ):
        """
        设置高级分析参数（包含本科类和特控类）

         Args:
             subject_column: str, 单科成绩列名
             total_column: str, 总分列名
             subject_basic: float, 基础单科分数线
             total_basic: float, 基础总分分数线
             subject_undergraduate: float, 本科类单科分数线
             total_undergraduate: float, 本科类总分分数线
             subject_special_control: float, 特控类单科分数线
             total_special_control: float, 特控类总分分数线
        """
        self.subject_column = subject_column
        self.total_column = total_column

        # 基础分数线
        self.subject_threshold = subject_basic
        self.total_threshold = total_basic

        # 本科类分数线
        self.subject_undergraduate = subject_undergraduate
        self.total_undergraduate = total_undergraduate

        # 特控类分数线
        self.subject_special_control = subject_special_control
        self.total_special_control = total_special_control

        self.analysis_type = "advanced"

    def analyze_quadrants(self):
        """
        分析四个象限的学生分布（支持自定义多指标）

        Returns:
            dict: 包含各区域的统计信息
        """
        if self.df is None or self.subject_column is None or self.total_column is None:
            return None

        # 根据分析类型选择不同的分析方法
        if self.analysis_type == "custom" and self.custom_metrics:
            return self.analyze_custom_quadrants()
        else:
            return self.analyze_basic_quadrants()

    def analyze_custom_quadrants(self):
        """
        自定义多指标四象限分析 - 支持动态九宫格分析

        Returns:
            dict: 包含自定义指标区域的统计信息
        """
        if not self.custom_metrics:
            return self.analyze_basic_quadrants()

        # 按分数线数量决定分析方式
        if len(self.custom_metrics) == 1:
            return self.analyze_single_metric_grid(self.custom_metrics[0])
        elif len(self.custom_metrics) == 2:
            return self.analyze_dual_metric_grid(
                self.custom_metrics[0], self.custom_metrics[1]
            )
        else:
            # 多指标：使用传统四象限分析
            return self.analyze_multi_metric_quadrants()

    def analyze_single_metric_grid(self, metric):
        """
        单指标四象限分析

        Args:
            metric: dict, 单个指标信息

        Returns:
            dict: 包含四象限的统计信息
        """
        metric_name = metric["name"]
        subject_th = metric["subject_threshold"]
        total_th = metric["total_threshold"]

        # 添加调试信息
        self.logger.info(f"开始分析指标: {metric_name}")
        print(f"[DEBUG] 开始分析指标: {metric_name}")
        self.logger.info(f"单科列: {self.subject_column}, 总分列: {self.total_column}")
        print(f"[DEBUG] 单科列: {self.subject_column}, 总分列: {self.total_column}")
        self.logger.info(f"单科分数线: {subject_th}, 总分分数线: {total_th}")
        print(f"[DEBUG] 单科分数线: {subject_th}, 总分分数线: {total_th}")
        self.logger.info(f"数据总数: {len(self.df)}")
        print(f"[DEBUG] 数据总数: {len(self.df)}")

        # 数据清理：移除NaN值
        clean_df = self.df.dropna(subset=[self.subject_column, self.total_column])
        self.logger.info(f"清理NaN后数据数: {len(clean_df)}")
        print(f"[DEBUG] 清理NaN后数据数: {len(clean_df)}")

        if len(clean_df) == 0:
            self.logger.error("没有有效数据进行分析")
            print("[DEBUG] 没有有效数据进行分析")
            return None

        # 计算相对值
        subject_diff = clean_df[self.subject_column] - subject_th
        total_diff = clean_df[self.total_column] - total_th

        # 统计各条件下的学生数量
        q1_count = ((subject_diff > 0) & (total_diff > 0)).sum()
        q2_count = ((subject_diff <= 0) & (total_diff > 0)).sum()
        q3_count = ((subject_diff <= 0) & (total_diff <= 0)).sum()
        q4_count = ((subject_diff > 0) & (total_diff <= 0)).sum()

        self.logger.info(
            f"各象限学生数 - Q1:{q1_count}, Q2:{q2_count}, Q3:{q3_count}, Q4:{q4_count}"
        )
        print(
            f"[DEBUG] 各象限学生数 - Q1:{q1_count}, Q2:{q2_count}, Q3:{q3_count}, Q4:{q4_count}"
        )
        self.logger.info(f"总学生数: {q1_count + q2_count + q3_count + q4_count}")
        print(f"[DEBUG] 总学生数: {q1_count + q2_count + q3_count + q4_count}")

        # 定义4个象限的掩码和标签
        quadrants = {
            1: {
                "mask": (subject_diff > 0) & (total_diff > 0),
                "label": f"{metric_name} - 双达标",
                "color": self._get_region_color(metric_name, 1),
            },
            2: {
                "mask": (subject_diff <= 0) & (total_diff > 0),
                "label": f"{metric_name} - 总分达标",
                "color": self._get_region_color(metric_name, 2),
            },
            3: {
                "mask": (subject_diff <= 0) & (total_diff <= 0),
                "label": f"{metric_name} - 双未达标",
                "color": self._get_region_color(metric_name, 3),
            },
            4: {
                "mask": (subject_diff > 0) & (total_diff <= 0),
                "label": f"{metric_name} - 单科达标",
                "color": self._get_region_color(metric_name, 4),
            },
        }

        self.quadrant_stats = {}

        for quadrant, info in quadrants.items():
            students = clean_df[info["mask"]]
            print(f"[DEBUG] 象限 {quadrant}: 找到 {len(students)} 个学生")

            # 计算统计信息
            stats = {
                "count": len(students),
                "percentage": safe_divide(len(students), len(clean_df)) * 100,
                "subject_mean": (
                    safe_mean(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "subject_std": (
                    safe_std(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "total_mean": (
                    students[self.total_column].mean() if len(students) > 0 else 0
                ),
                "total_std": (
                    students[self.total_column].std() if len(students) > 0 else 0
                ),
                "students": students,
                "label": info["label"],
                "color": info["color"],
                "metric_name": metric_name,
                "quadrant": quadrant,
            }

            region_key = f"{metric_name}_Q{quadrant}"
            self.quadrant_stats[region_key] = stats
            print(f"[DEBUG] 已存储区域 {region_key}，包含 {stats['count']} 个学生")

        print(f"[DEBUG] 分析完成，总共生成 {len(self.quadrant_stats)} 个区域统计")
        for region_key, stats in self.quadrant_stats.items():
            print(f"[DEBUG] {region_key}: {stats['count']} 个学生")

        return self.quadrant_stats

    def analyze_dual_metric_grid(self, metric1, metric2):
        """
        双指标九宫格分析（如本科线+特控线）

        Args:
            metric1: dict, 第一个指标（通常是较低的分数线，如本科线）
            metric2: dict, 第二个指标（通常是较高的分数线，如特控线）

        Returns:
            dict: 包含九宫格的统计信息
        """
        # 确保metric1是较低的分数线
        if metric1["subject_threshold"] > metric2["subject_threshold"]:
            metric1, metric2 = metric2, metric1

        metric1_name = metric1["name"]
        metric2_name = metric2["name"]

        # 定义阈值
        subject_low = metric1["subject_threshold"]
        total_low = metric1["total_threshold"]
        subject_high = metric2["subject_threshold"]
        total_high = metric2["total_threshold"]

        # 数据清理：移除NaN值
        clean_df = self.df.dropna(subset=[self.subject_column, self.total_column])
        total_students = len(clean_df)  # 保存总学生数

        # 计算各水平
        subject_above_high = clean_df[self.subject_column] > subject_high
        subject_between = (clean_df[self.subject_column] > subject_low) & (
            clean_df[self.subject_column] <= subject_high
        )
        subject_below_low = clean_df[self.subject_column] <= subject_low

        total_above_high = clean_df[self.total_column] > total_high
        total_between = (clean_df[self.total_column] > total_low) & (
            clean_df[self.total_column] <= total_high
        )
        total_below_low = clean_df[self.total_column] <= total_low

        # 定义9个区域
        regions = {
            1: {  # 右上：双高水平
                "mask": subject_above_high & total_above_high,
                "label": f"双{metric2_name}水平",
                "color": "#FF1493",  # 深粉色
            },
            2: {  # 中上：单科高水平，总分中水平
                "mask": subject_above_high & total_between,
                "label": f"单科{metric2_name}，总分{metric1_name}",
                "color": "#FF69B4",  # 热粉色
            },
            3: {  # 右中：单科中水平，总分高水平
                "mask": subject_between & total_above_high,
                "label": f"单科{metric1_name}，总分{metric2_name}",
                "color": "#FFA07A",  # 浅鲑鱼色
            },
            4: {  # 中中：双中水平
                "mask": subject_between & total_between,
                "label": f"双{metric1_name}水平",
                "color": "#006400",  # 深绿色
            },
            5: {  # 左上：单科低水平，总分高水平
                "mask": subject_below_low & total_above_high,
                "label": f"单科未达{metric1_name}，总分{metric2_name}",
                "color": "#32CD32",  # 绿色
            },
            6: {  # 左中：单科低水平，总分中水平
                "mask": subject_below_low & total_between,
                "label": f"单科未达{metric1_name}，总分{metric1_name}",
                "color": "#90EE90",  # 浅绿色
            },
            7: {  # 左下：双低水平
                "mask": subject_below_low & total_below_low,
                "label": f"双未达{metric1_name}",
                "color": "#D3D3D3",  # 浅灰色
            },
            8: {  # 右下：单科中水平，总分低水平
                "mask": subject_between & total_below_low,
                "label": f"单科{metric1_name}，总分未达{metric1_name}",
                "color": "#87CEEB",  # 天蓝色
            },
            9: {  # 中下：单科高水平，总分低水平
                "mask": subject_above_high & total_below_low,
                "label": f"单科{metric2_name}，总分未达{metric1_name}",
                "color": "#DDA0DD",  # 梅红色
            },
        }

        self.quadrant_stats = {}

        for region_id, info in regions.items():
            students = clean_df[info["mask"]]

            # 计算统计信息
            stats = {
                "count": len(students),
                "percentage": len(students) / total_students * 100,
                "subject_mean": (
                    students[self.subject_column].mean() if len(students) > 0 else 0
                ),
                "subject_std": (
                    students[self.subject_column].std() if len(students) > 0 else 0
                ),
                "total_mean": (
                    students[self.total_column].mean() if len(students) > 0 else 0
                ),
                "total_std": (
                    students[self.total_column].std() if len(students) > 0 else 0
                ),
                "students": students,
                "label": info["label"],
                "color": info["color"],
                "region_id": region_id,
            }

            region_key = f"grid_R{region_id}"
            self.quadrant_stats[region_key] = stats

        return self.quadrant_stats

    def analyze_multi_metric_quadrants(self):
        """
        多指标分层分析（超过2个指标时使用）
        三条分数线：16宫格分析
        三条以上：选择其中一条作为辅助线进行九宫格分析

        Returns:
            dict: 包含各指标区域的统计信息
        """
        if not self.custom_metrics:
            return None

        # 按分数线从高到低排序
        sorted_metrics = sorted(
            self.custom_metrics,
            key=lambda x: max(x["subject_threshold"], x["total_threshold"]),
            reverse=True,
        )

        if len(self.custom_metrics) == 3:
            # 三条分数线：16宫格分析（4x4）
            return self.analyze_triple_metric_grid(
                sorted_metrics[0], sorted_metrics[1], sorted_metrics[2]
            )
        else:
            # 三条以上：选择最高级和最低级进行九宫格分析，其余作为辅助线
            primary_metric = sorted_metrics[0]
            secondary_metric = sorted_metrics[1]
            return self.analyze_dual_metric_grid(primary_metric, secondary_metric)

    def analyze_triple_metric_grid(self, high_metric, mid_metric, low_metric):
        """
        三指标16宫格分析（4x4）

        Args:
            high_metric: dict, 最高级别指标
            mid_metric: dict, 中间级别指标
            low_metric: dict, 最低级别指标

        Returns:
            dict: 包含16宫格的统计信息
        """
        # 定义阈值
        subject_high = high_metric["subject_threshold"]
        total_high = high_metric["total_threshold"]
        subject_mid = mid_metric["subject_threshold"]
        total_mid = mid_metric["total_threshold"]
        subject_low = low_metric["subject_threshold"]
        total_low = low_metric["total_threshold"]

        # 数据清理：移除NaN值
        clean_df = self.df.dropna(subset=[self.subject_column, self.total_column])

        # 计算各水平
        subject_above_high = clean_df[self.subject_column] > subject_high
        subject_between_mid_high = (clean_df[self.subject_column] > subject_mid) & (
            clean_df[self.subject_column] <= subject_high
        )
        subject_between_low_mid = (clean_df[self.subject_column] > subject_low) & (
            clean_df[self.subject_column] <= subject_mid
        )
        subject_below_low = clean_df[self.subject_column] <= subject_low

        total_above_high = clean_df[self.total_column] > total_high
        total_between_mid_high = (clean_df[self.total_column] > total_mid) & (
            clean_df[self.total_column] <= total_high
        )
        total_between_low_mid = (clean_df[self.total_column] > total_low) & (
            clean_df[self.total_column] <= total_mid
        )
        total_below_low = clean_df[self.total_column] <= total_low

        # 定义16个区域（4x4宫格）
        regions = {
            1: {  # 右上：双高水平
                "mask": subject_above_high & total_above_high,
                "label": f"双{high_metric['name']}",
                "color": "#FF1493",  # 深粉色
            },
            2: {  # 右上中：单科高水平，总分中高水平
                "mask": subject_above_high & total_between_mid_high,
                "label": f"单科{high_metric['name']}，总分{mid_metric['name']}",
                "color": "#FF69B4",  # 热粉色
            },
            3: {  # 右上低：单科高水平，总分中低水平
                "mask": subject_above_high & total_between_low_mid,
                "label": f"单科{high_metric['name']}，总分{low_metric['name']}",
                "color": "#FFA07A",  # 浅鲑鱼色
            },
            4: {  # 右下：单科高水平，总分低水平
                "mask": subject_above_high & total_below_low,
                "label": f"单科{high_metric['name']}，总分未达{low_metric['name']}",
                "color": "#FFD700",  # 金色
            },
            5: {  # 中上：单科中高水平，总分高水平
                "mask": subject_between_mid_high & total_above_high,
                "label": f"单科{mid_metric['name']}，总分{high_metric['name']}",
                "color": "#006400",  # 深绿色
            },
            6: {  # 中中上：双中高水平
                "mask": subject_between_mid_high & total_between_mid_high,
                "label": f"双{mid_metric['name']}",
                "color": "#32CD32",  # 绿色
            },
            7: {  # 中中低：单科中高水平，总分中低水平
                "mask": subject_between_mid_high & total_between_low_mid,
                "label": f"单科{mid_metric['name']}，总分{low_metric['name']}",
                "color": "#90EE90",  # 浅绿色
            },
            8: {  # 中下：单科中高水平，总分低水平
                "mask": subject_between_mid_high & total_below_low,
                "label": f"单科{mid_metric['name']}，总分未达{low_metric['name']}",
                "color": "#87CEEB",  # 天蓝色
            },
            9: {  # 左上：单科中低水平，总分高水平
                "mask": subject_between_low_mid & total_above_high,
                "label": f"单科{low_metric['name']}，总分{high_metric['name']}",
                "color": "#4169E1",  # 蓝色
            },
            10: {  # 左中上：单科中低水平，总分中高水平
                "mask": subject_between_low_mid & total_between_mid_high,
                "label": f"单科{low_metric['name']}，总分{mid_metric['name']}",
                "color": "#1E90FF",  # 道奇蓝
            },
            11: {  # 左中低：双中低水平
                "mask": subject_between_low_mid & total_between_low_mid,
                "label": f"双{low_metric['name']}",
                "color": "#DDA0DD",  # 梅红色
            },
            12: {  # 左下：单科中低水平，总分低水平
                "mask": subject_between_low_mid & total_below_low,
                "label": f"单科{low_metric['name']}，总分未达{low_metric['name']}",
                "color": "#FF6347",  # 番茄色
            },
            13: {  # 左上外：单科低水平，总分高水平
                "mask": subject_below_low & total_above_high,
                "label": f"单科未达{low_metric['name']}，总分{high_metric['name']}",
                "color": "#FFA500",  # 橙色
            },
            14: {  # 左中外：单科低水平，总分中高水平
                "mask": subject_below_low & total_between_mid_high,
                "label": f"单科未达{low_metric['name']}，总分{mid_metric['name']}",
                "color": "#FF8C00",  # 深橙色
            },
            15: {  # 左下外：单科低水平，总分中低水平
                "mask": subject_below_low & total_between_low_mid,
                "label": f"单科未达{low_metric['name']}，总分{low_metric['name']}",
                "color": "#8B4513",  # 棕色
            },
            16: {  # 左下角：双低水平
                "mask": subject_below_low & total_below_low,
                "label": f"双未达{low_metric['name']}",
                "color": "#D3D3D3",  # 浅灰色
            },
        }

        self.quadrant_stats = {}
        zone_data = {}

        for region_id, info in regions.items():
            students = clean_df[info["mask"]]
            zone_data[region_id] = students

            # 计算统计信息
            stats = {
                "count": len(students),
                "percentage": safe_divide(len(students), len(clean_df)) * 100,
                "subject_mean": (
                    safe_mean(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "subject_std": (
                    safe_std(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "total_mean": (
                    students[self.total_column].mean() if len(students) > 0 else 0
                ),
                "total_std": (
                    students[self.total_column].std() if len(students) > 0 else 0
                ),
                "students": students,
                "label": info["label"],
                "color": info["color"],
            }

            self.quadrant_stats[region_id] = stats

        return self.quadrant_stats

    def _get_region_color(self, metric_name, quadrant):
        """
        获取区域颜色（根据指标名称和象限）

        Args:
            metric_name: str, 指标名称
            quadrant: int, 象限编号

        Returns:
            str: 颜色代码
        """
        # 根据指标名称生成基础颜色
        if "保底" in metric_name:
            base_colors = {
                1: "#2E8B57",
                2: "#32CD32",
                3: "#D3D3D3",
                4: "#87CEEB",
            }  # 绿色系
        elif "本科" in metric_name:
            base_colors = {
                1: "#006400",
                2: "#90EE90",
                3: "#D3D3D3",
                4: "#FFD700",
            }  # 深绿色系
        elif "重点" in metric_name:
            base_colors = {
                1: "#FF6347",
                2: "#FFA07A",
                3: "#D3D3D3",
                4: "#FF8C00",
            }  # 橙色系
        elif "特控" in metric_name:
            base_colors = {
                1: "#FF1493",
                2: "#FF69B4",
                3: "#D3D3D3",
                4: "#DDA0DD",
            }  # 粉色系
        else:
            # 默认颜色方案
            base_colors = {
                1: "#4169E1",
                2: "#1E90FF",
                3: "#D3D3D3",
                4: "#87CEEB",
            }  # 蓝色系

        return base_colors.get(quadrant, "#808080")

    def analyze_basic_quadrants(self):
        """
        基础四象限分析

        Returns:
            dict: 包含四个象限的统计信息
        """
        # 数据清理：移除NaN值
        clean_df = self.df.dropna(subset=[self.subject_column, self.total_column])

        # 计算相对值（相对于阈值）
        subject_diff = clean_df[self.subject_column] - self.subject_threshold
        total_diff = clean_df[self.total_column] - self.total_threshold

        # 分类学生到四个象限
        quadrant_mask = {
            1: (subject_diff > 0) & (total_diff > 0),  # 第一象限：单科和总分均达标
            2: (subject_diff <= 0) & (total_diff > 0),  # 第二象限：总分达标但单科未达标
            3: (subject_diff <= 0) & (total_diff <= 0),  # 第三象限：单科和总分均未达标
            4: (subject_diff > 0) & (total_diff <= 0),  # 第四象限：单科达标但总分未达标
        }

        quadrant_data = {}
        self.quadrant_stats = {}

        for quadrant, mask in quadrant_mask.items():
            students = clean_df[mask]
            quadrant_data[quadrant] = students

            # 计算统计信息
            stats = {
                "count": len(students),
                "percentage": safe_divide(len(students), len(clean_df)) * 100,
                "subject_mean": (
                    safe_mean(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "subject_std": (
                    safe_std(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "total_mean": (
                    students[self.total_column].mean() if len(students) > 0 else 0
                ),
                "total_std": (
                    students[self.total_column].std() if len(students) > 0 else 0
                ),
                "students": students,
            }

            self.quadrant_stats[quadrant] = stats

        return self.quadrant_stats

    def analyze_advanced_quadrants(self):
        """
        本科类和特控类四象限分析

        Returns:
            dict: 包含本科类和特控类的统计信息
        """
        if self.analysis_type != "advanced":
            return self.analyze_basic_quadrants()

        # 数据清理：移除NaN值
        clean_df = self.df.dropna(subset=[self.subject_column, self.total_column])

        # 定义9种组合分类：
        # 1. 单科达特控，总分达特控
        # 2. 单科达特控，总分达本科
        # 3. 单科达本科，总分达特控
        # 4. 单科达本科，总分达本科
        # 5. 单科不达本科，总分达特控
        # 6. 单科不达本科，总分达本科
        # 7. 单科不达本科，总分不达本科
        # 8. 单科达本科，总分不达本科
        # 9. 单科达特控，总分不达本科

        # 计算各区域掩码
        subject_above_undergraduate = (
            clean_df[self.subject_column] > self.subject_undergraduate
        )
        subject_above_special = (
            clean_df[self.subject_column] > self.subject_special_control
        )

        total_above_undergraduate = (
            clean_df[self.total_column] > self.total_undergraduate
        )
        total_above_special = clean_df[self.total_column] > self.total_special_control

        # 定义9个区域的掩码和标签
        zones_mask = {
            1: subject_above_special & total_above_special,  # 单科达特控，总分达特控
            2: subject_above_special
            & total_above_undergraduate
            & ~total_above_special,  # 单科达特控，总分达本科
            3: subject_above_undergraduate
            & ~subject_above_special
            & total_above_special,  # 单科达本科，总分达特控
            4: subject_above_undergraduate
            & total_above_undergraduate
            & ~subject_above_special
            & ~total_above_special,  # 单科达本科，总分达本科
            5: ~subject_above_undergraduate
            & total_above_special,  # 单科不达本科，总分达特控
            6: ~subject_above_undergraduate
            & total_above_undergraduate
            & ~total_above_special,  # 单科不达本科，总分达本科
            7: ~subject_above_undergraduate
            & ~total_above_undergraduate,  # 单科不达本科，总分不达本科
            8: subject_above_undergraduate
            & ~subject_above_special
            & ~total_above_undergraduate,  # 单科达本科，总分不达本科
            9: subject_above_special
            & ~total_above_undergraduate,  # 单科达特控，总分不达本科
        }

        zone_labels = {
            1: "单科达特控，总分达特控",
            2: "单科达特控，总分达本科",
            3: "单科达本科，总分达特控",
            4: "单科达本科，总分达本科",
            5: "单科不达本科，总分达特控",
            6: "单科不达本科，总分达本科",
            7: "单科不达本科，总分不达本科",
            8: "单科达本科，总分不达本科",
            9: "单科达特控，总分不达本科",
        }

        zone_colors = {
            1: "#FF1493",  # 深粉色 - 特控类最优
            2: "#FF69B4",  # 热粉色 - 单科特控
            3: "#FFA07A",  # 浅鲑鱼色 - 总分特控
            4: "#006400",  # 深绿色 - 本科达标
            5: "#32CD32",  # 绿色 - 总分特控但单科弱
            6: "#90EE90",  # 浅绿色 - 总分本科但单科弱
            7: "#D3D3D3",  # 浅灰色 - 双科未达本科
            8: "#87CEEB",  # 天蓝色 - 单科本科但总分弱
            9: "#DDA0DD",  # 梅红色 - 单科特控但总分弱
        }

        zone_data = {}
        self.quadrant_stats = {}
        self.advanced_stats = {}

        for zone, mask in zones_mask.items():
            students = clean_df[mask]
            zone_data[zone] = students

            # 计算统计信息
            stats = {
                "count": len(students),
                "percentage": safe_divide(len(students), len(clean_df)) * 100,
                "subject_mean": (
                    safe_mean(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "subject_std": (
                    safe_std(students[self.subject_column]) if len(students) > 0 else 0
                ),
                "total_mean": (
                    students[self.total_column].mean() if len(students) > 0 else 0
                ),
                "total_std": (
                    students[self.total_column].std() if len(students) > 0 else 0
                ),
                "students": students,
                "label": zone_labels[zone],
                "color": zone_colors[zone],
            }

            self.quadrant_stats[zone] = stats
            self.advanced_stats[zone] = {
                "label": zone_labels[zone],
                "color": zone_colors[zone],
                "stats": stats,
            }

        return self.quadrant_stats

    def create_quadrant_plot(self, show_names=True, max_labels=20):
        """
        创建四象限散点图

        Args:
            show_names: bool, 是否显示学生姓名
            max_labels: int, 最大标签数量

        Returns:
            plotly.graph_objects.Figure
        """
        if (
            self.df is None
            or not hasattr(self, "quadrant_stats")
            or not self.quadrant_stats
        ):
            return None

        if self.analysis_type == "custom" and self.custom_metrics:
            return self.create_custom_quadrant_plot(show_names, max_labels)
        elif self.analysis_type == "advanced":
            return self.create_advanced_quadrant_plot(show_names, max_labels)
        else:
            return self.create_basic_quadrant_plot(show_names, max_labels)

    def create_basic_quadrant_plot(self, show_names=True, max_labels=20):
        """创建基础四象限散点图"""
        fig = go.Figure()

        # 定义象限颜色和标签
        # Prefixed with underscore to indicate intentional unused mappings
        _quadrant_colors = {  # noqa: F841
            1: "#2E8B57",  # 绿色 - 均达标
            2: "#FFD700",  # 金色 - 总分达标
            3: "#DC143C",  # 红色 - 均未达标
            4: "#4169E1",  # 蓝色 - 单科达标
        }

        _quadrant_labels = {  # noqa: F841
            1: "第一象限：单科和总分均达标",
            2: "第二象限：总分达标但单科未达标",
            3: "第三象限：单科和总分均未达标",
            4: "第四象限：单科达标但总分未达标",
        }

        # 为每个象限添加散点
        for quadrant, stats in self.quadrant_stats.items():
            if stats["count"] == 0:
                continue

            students = stats["students"]

            # 准备散点数据
            if (
                self.subject_column not in students.columns
                or self.total_column not in students.columns
            ):
                print(
                    f"[DEBUG] 缺少数据列: {self.subject_column} 或 {self.total_column}"
                )
                continue

            x_values = students[self.subject_column]
            y_values = students[self.total_column]

            # 确保数据是数值类型
            x_values = pd.to_numeric(x_values, errors="coerce")
            y_values = pd.to_numeric(y_values, errors="coerce")

            # 移除转换后的NaN值
            valid_mask = ~(pd.isna(x_values) | pd.isna(y_values))
            x_values = x_values[valid_mask]
            y_values = y_values[valid_mask]
            students = students[valid_mask]

            # 转换为列表以确保兼容性
            x_values = list(x_values)
            y_values = list(y_values)

            print(
                f"[DEBUG] 准备添加散点: X数据点数={len(x_values)}, Y数据点数={len(y_values)}"
            )
            print(f"[DEBUG] X数据类型: {type(x_values)}, Y数据类型: {type(y_values)}")
            if len(x_values) > 0:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)
                print(
                    f"[DEBUG] X数据范围: [{x_min}, {x_max}], Y数据范围: [{y_min}, {y_max}]"
                )
                print(f"[DEBUG] 前5个数据点 - X: {x_values[:5]}, Y: {y_values[:5]}")
            else:
                print("[DEBUG] 数据为空，无法显示范围")

            # 准备悬停文本
            hover_texts = []
            for idx, student in students.iterrows():
                # 获取学校和班级信息
                school_name = ""
                class_name = ""

                # 查找学校列
                for col in self.df.columns:
                    if "学校" in col and col in student:
                        school_name = student[col]
                        break

                # 查找班级列
                for col in self.df.columns:
                    if "行政班" in col and col in student:
                        class_name = student[col]
                    elif "班级" in col and col in student and not class_name:
                        class_name = student[col]

                hover_text = f"学校：{school_name}<br>"
                hover_text += f"班级：{class_name}<br>"
                hover_text += f"学生: {student.get('姓名', idx)}<br>"
                hover_text += f"单科成绩: {student[self.subject_column]}<br>"
                hover_text += f"总分: {student[self.total_column]}"
                hover_texts.append(hover_text)

            # 检查数据有效性
            if len(students) == 0 or len(x_values) == 0 or len(y_values) == 0:
                continue

            # 确定是否显示标签
            text_values = None
            if show_names and len(students) <= max_labels:
                text_values = [
                    student.get("姓名", f"学生{idx}")
                    for idx, student in students.iterrows()
                ]

            # 添加散点

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers+text" if text_values else "markers",
                    text=text_values,
                    hovertext=hover_texts,
                    hovertemplate="%{hovertext}<extra></extra>",
                    name=stats["label"],
                    marker=dict(
                        color=stats["color"],
                        size=8,
                        opacity=0.7,
                        line=dict(width=1, color="white"),
                    ),
                    textposition="top center",
                    textfont=dict(size=8),
                )
            )

        # 添加分割线
        fig.add_hline(
            y=self.total_threshold,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text=f"总分线: {self.total_threshold}",
            annotation_position="bottom left",
        )

        fig.add_vline(
            x=self.subject_threshold,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text=f"单科线: {self.subject_threshold}",
            annotation_position="top left",
        )

        # 设置布局
        fig.update_layout(
            title="学生成绩四象限分布图",
            xaxis_title=f"{self.subject_column} 成绩",
            yaxis_title=f"{self.total_column} 成绩",
            width=800,
            height=600,
            plot_bgcolor="white",
            hovermode="closest",
            legend=dict(
                x=1.02,
                y=1,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="black",
                borderwidth=1,
            ),
        )

        # 设置网格
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

        print(f"[DEBUG] 散点图创建完成，总共包含 {len(fig.data)} 个轨迹")
        for i, trace in enumerate(fig.data):
            print(
                (
                    f"[DEBUG] 轨迹 {i}: {trace.name}, "
                    f"数据点数: {len(trace.x) if trace.x is not None else 0}"
                )
            )

        return fig

    def create_advanced_quadrant_plot(self, show_names=True, max_labels=20):
        """创建本科类和特控类四象限散点图"""
        fig = go.Figure()

        # 为每个区域添加散点
        for zone, stats in self.quadrant_stats.items():
            if stats["count"] == 0:
                continue

            students = stats["students"]

            # 准备散点数据
            if (
                self.subject_column not in students.columns
                or self.total_column not in students.columns
            ):
                print(
                    f"[DEBUG] 缺少数据列: {self.subject_column} 或 {self.total_column}"
                )
                continue

            x_values = students[self.subject_column]
            y_values = students[self.total_column]

            # 确保数据是数值类型
            x_values = pd.to_numeric(x_values, errors="coerce")
            y_values = pd.to_numeric(y_values, errors="coerce")

            # 移除转换后的NaN值
            valid_mask = ~(pd.isna(x_values) | pd.isna(y_values))
            x_values = x_values[valid_mask]
            y_values = y_values[valid_mask]
            students = students[valid_mask]

            # 转换为列表以确保兼容性
            x_values = list(x_values)
            y_values = list(y_values)

            print(
                f"[DEBUG] 准备添加散点: X数据点数={len(x_values)}, Y数据点数={len(y_values)}"
            )
            print(f"[DEBUG] X数据类型: {type(x_values)}, Y数据类型: {type(y_values)}")
            if len(x_values) > 0:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)
                print(
                    f"[DEBUG] X数据范围: [{x_min}, {x_max}], Y数据范围: [{y_min}, {y_max}]"
                )
                print(f"[DEBUG] 前5个数据点 - X: {x_values[:5]}, Y: {y_values[:5]}")
            else:
                print("[DEBUG] 数据为空，无法显示范围")

            # 准备悬停文本
            hover_texts = []
            for idx, student in students.iterrows():
                # 获取学校和班级信息
                school_name = ""
                class_name = ""

                # 查找学校列
                for col in self.df.columns:
                    if "学校" in col and col in student:
                        school_name = student[col]
                        break

                # 查找班级列
                for col in self.df.columns:
                    if "行政班" in col and col in student:
                        class_name = student[col]
                    elif "班级" in col and col in student and not class_name:
                        class_name = student[col]

                hover_text = f"学校：{school_name}<br>"
                hover_text += f"班级：{class_name}<br>"
                hover_text += f"学生: {student.get('姓名', idx)}<br>"
                hover_text += (
                    f"{self.subject_column}: {student[self.subject_column]:.1f}<br>"
                )
                hover_text += (
                    f"{self.total_column}: {student[self.total_column]:.1f}<br>"
                )
                hover_text += f"所属区域: {stats['label']}"
                hover_texts.append(hover_text)

            # 检查数据有效性
            if len(students) == 0 or len(x_values) == 0 or len(y_values) == 0:
                continue

            # 确定是否显示标签
            text_values = None
            if show_names and len(students) <= max_labels:
                text_values = [
                    student.get("姓名", f"学生{idx}")
                    for idx, student in students.iterrows()
                ]

            # 添加散点

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers+text" if text_values else "markers",
                    text=text_values,
                    hovertext=hover_texts,
                    hovertemplate="%{hovertext}<extra></extra>",
                    name=stats["label"],
                    marker=dict(
                        color=stats["color"],
                        size=8,
                        opacity=0.7,
                        line=dict(width=1, color="white"),
                    ),
                    textposition="top center",
                    textfont=dict(size=8),
                )
            )

        # 添加多级分割线
        # 特控类线（最粗）
        if (
            hasattr(self, "subject_special_control")
            and self.subject_special_control > 0
        ):
            fig.add_vline(
                x=self.subject_special_control,
                line_dash="dash",
                line_color="#FF1493",
                line_width=3,
                annotation_text=f"特控单科线: {self.subject_special_control}",
                annotation_position="top",
                annotation_font=dict(color="#FF1493", size=10),
            )

        if hasattr(self, "total_special_control") and self.total_special_control > 0:
            fig.add_hline(
                y=self.total_special_control,
                line_dash="dash",
                line_color="#FF1493",
                line_width=3,
                annotation_text=f"特控总分线: {self.total_special_control}",
                annotation_position="right",
                annotation_font=dict(color="#FF1493", size=10),
            )

        # 本科类线（中等粗细）
        if hasattr(self, "subject_undergraduate") and self.subject_undergraduate > 0:
            fig.add_vline(
                x=self.subject_undergraduate,
                line_dash="dash",
                line_color="#32CD32",
                line_width=2.5,
                annotation_text=f"本科单科线: {self.subject_undergraduate}",
                annotation_position="bottom",
                annotation_font=dict(color="#32CD32", size=10),
            )

        if hasattr(self, "total_undergraduate") and self.total_undergraduate > 0:
            fig.add_hline(
                y=self.total_undergraduate,
                line_dash="dash",
                line_color="#32CD32",
                line_width=2.5,
                annotation_text=f"本科总分线: {self.total_undergraduate}",
                annotation_position="left",
                annotation_font=dict(color="#32CD32", size=10),
            )

        # 设置布局
        fig.update_layout(
            title="学生成绩九组合分析分布图",
            xaxis_title=f"{self.subject_column} 成绩",
            yaxis_title=f"{self.total_column} 成绩",
            width=None,
            height=None,
            plot_bgcolor="white",
            hovermode="closest",
            legend=dict(
                x=1.02,
                y=1,
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="black",
                borderwidth=1,
                font=dict(size=9),
            ),
        )

        # 设置网格
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

        print(f"[DEBUG] 散点图创建完成，总共包含 {len(fig.data)} 个轨迹")
        for i, trace in enumerate(fig.data):
            print(
                (
                    f"[DEBUG] 轨迹 {i}: {trace.name}, "
                    f"数据点数: {len(trace.x) if trace.x is not None else 0}"
                )
            )

        return fig

    def create_custom_quadrant_plot(self, show_names=True, max_labels=20):
        """创建自定义多指标散点图（支持四象限和九宫格）"""
        fig = go.Figure()

        # 根据指标数量判断分析类型
        if len(self.custom_metrics) == 1:
            title = "学生成绩四象限分析分布图"
        elif len(self.custom_metrics) == 2:
            title = "学生成绩九宫格分析分布图"
        elif len(self.custom_metrics) == 3:
            title = "学生成绩16宫格分析分布图"
        else:
            # 对于4条及以上分数线，使用其中一条作为辅助线进行九宫格分析
            title = f"学生成绩{len(self.custom_metrics)}级分数线分层分析分布图"

        # 添加调试信息
        self.logger.info(f"开始创建散点图，象限统计数量: {len(self.quadrant_stats)}")
        print(f"[DEBUG] 开始创建散点图，象限统计数量: {len(self.quadrant_stats)}")

        # 检查数据是否存在
        if not self.quadrant_stats:
            self.logger.error("没有象限统计数据")
            print("[DEBUG] 没有象限统计数据")
            # 添加测试散点以确保图表可见
            fig.add_trace(
                go.Scatter(
                    x=[75],
                    y=[375],
                    mode="markers",
                    name="测试点",
                    marker=dict(color="red", size=20, symbol="x"),
                )
            )
            print("[DEBUG] 已添加测试点以验证图表功能")
            return fig

        # 为每个区域添加散点
        for region_key, stats in self.quadrant_stats.items():
            self.logger.info(f"处理区域: {region_key}, 学生数: {stats['count']}")
            print(f"[DEBUG] 处理区域: {region_key}, 学生数: {stats['count']}")
            if stats["count"] == 0:
                self.logger.info(f"跳过空区域: {region_key}")
                print(f"[DEBUG] 跳过空区域: {region_key}")
                continue

            students = stats["students"]
            self.logger.info(f"实际获取学生数据: {len(students)} 行")
            print(f"[DEBUG] 实际获取学生数据: {len(students)} 行")

            # 准备散点数据
            if (
                self.subject_column not in students.columns
                or self.total_column not in students.columns
            ):
                print(
                    f"[DEBUG] 缺少数据列: {self.subject_column} 或 {self.total_column}"
                )
                continue

            x_values = students[self.subject_column]
            y_values = students[self.total_column]

            # 确保数据是数值类型
            x_values = pd.to_numeric(x_values, errors="coerce")
            y_values = pd.to_numeric(y_values, errors="coerce")

            # 移除转换后的NaN值
            valid_mask = ~(pd.isna(x_values) | pd.isna(y_values))
            x_values = x_values[valid_mask]
            y_values = y_values[valid_mask]
            students = students[valid_mask]

            # 转换为列表以确保兼容性
            x_values = list(x_values)
            y_values = list(y_values)

            print(
                f"[DEBUG] 准备添加散点: X数据点数={len(x_values)}, Y数据点数={len(y_values)}"
            )
            print(f"[DEBUG] X数据类型: {type(x_values)}, Y数据类型: {type(y_values)}")
            if len(x_values) > 0:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)
                print(
                    f"[DEBUG] X数据范围: [{x_min}, {x_max}], Y数据范围: [{y_min}, {y_max}]"
                )
                print(f"[DEBUG] 前5个数据点 - X: {x_values[:5]}, Y: {y_values[:5]}")
            else:
                print("[DEBUG] 数据为空，无法显示范围")

            # 准备悬停文本
            hover_texts = []
            for idx, student in students.iterrows():
                # 获取学校和班级信息
                school_name = ""
                class_name = ""

                # 查找学校列
                for col in self.df.columns:
                    if "学校" in col and col in student:
                        school_name = student[col]
                        break

                # 查找班级列
                for col in self.df.columns:
                    if "行政班" in col and col in student:
                        class_name = student[col]
                    elif "班级" in col and col in student and not class_name:
                        class_name = student[col]

                hover_text = f"学校：{school_name}<br>"
                hover_text += f"班级：{class_name}<br>"
                hover_text += f"学生: {student.get('姓名', idx)}<br>"
                hover_text += (
                    f"{self.subject_column}: {student[self.subject_column]:.1f}<br>"
                )
                hover_text += (
                    f"{self.total_column}: {student[self.total_column]:.1f}<br>"
                )
                hover_text += f"所属区域: {stats['label']}"
                hover_texts.append(hover_text)

            # 检查数据有效性
            if len(students) == 0 or len(x_values) == 0 or len(y_values) == 0:
                print(f"[DEBUG] 区域 {region_key} 数据为空，跳过")
                continue

            # 确定是否显示标签
            text_values = None
            if show_names and len(students) <= max_labels:
                text_values = [
                    student.get("姓名", f"学生{idx}")
                    for idx, student in students.iterrows()
                ]

            # 添加散点
            print(f"[DEBUG] 开始添加区域 {region_key} 的散点轨迹")
            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers+text" if text_values else "markers",
                    text=text_values,
                    hovertext=hover_texts,
                    hovertemplate="%{hovertext}<extra></extra>",
                    name=stats["label"],
                    marker=dict(
                        color=stats["color"],
                        size=8,
                        opacity=0.7,
                        line=dict(width=1, color="white"),
                    ),
                    textposition="top center",
                    textfont=dict(size=8),
                )
            )
            print(
                f"[DEBUG] 已添加区域 {region_key} 的散点，包含 {len(students)} 个学生"
            )

        # 添加所有指标的分数线
        for i, metric in enumerate(self.custom_metrics):
            # 根据指标调整线条样式和可见性
            if len(self.custom_metrics) == 1:
                # 1条分数线
                line_style = "dash"
                line_width = 3
                opacity = 1.0
                show_annotation = True
            elif len(self.custom_metrics) == 2:
                # 2条分数线
                line_style = "dash"
                line_width = 3 if i == 0 else 2.5
                opacity = 1.0
                show_annotation = True
            elif len(self.custom_metrics) == 3:
                # 3条分数线：全部显示，用于16宫格分析
                line_style = "dash"
                line_width = 3 if i == 0 else (2.5 if i == 1 else 2)
                opacity = 1.0
                show_annotation = True
            else:
                # 4条及以上：只显示前两条主要的，其余作为辅助线
                if i < 2:
                    line_style = "dash"
                    line_width = 3 if i == 0 else 2.5
                    opacity = 1.0
                    show_annotation = True
                else:
                    line_style = "dot"  # 使用点线表示辅助线
                    line_width = 1
                    opacity = 0.6
                    show_annotation = False

            # 获取指标颜色
            metric_color = self._get_region_color(metric["name"], 1)

            # 添加单科线
            fig.add_vline(
                x=metric["subject_threshold"],
                line_dash=line_style,
                line_color=metric_color,
                line_width=line_width,
                opacity=opacity,
                annotation_text=(
                    f"{metric['name']}单科线: {metric['subject_threshold']}"
                    if show_annotation
                    else ""
                ),
                annotation_position="top" if i % 2 == 0 else "bottom",
                annotation_font=dict(color=metric_color, size=9),
            )

            # 添加总分线
            fig.add_hline(
                y=metric["total_threshold"],
                line_dash=line_style,
                line_color=metric_color,
                line_width=line_width,
                opacity=opacity,
                annotation_text=(
                    f"{metric['name']}总分线: {metric['total_threshold']}"
                    if show_annotation
                    else ""
                ),
                annotation_position="right" if i % 2 == 0 else "left",
                annotation_font=dict(color=metric_color, size=9),
            )

        # 设置布局
        fig.update_layout(
            title=title,
            xaxis_title=f"{self.subject_column} 成绩",
            yaxis_title=f"{self.total_column} 成绩",
            width=None,
            height=None,
            plot_bgcolor="white",
            hovermode="closest",
            legend=dict(
                x=1.02,
                y=1,
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="black",
                borderwidth=1,
                font=dict(size=9),
            ),
        )

        # 自动调整坐标轴范围以确保所有数据点可见
        if len(fig.data) > 0:
            all_x = []
            all_y = []
            for trace in fig.data:
                if hasattr(trace, "x") and trace.x is not None:
                    all_x.extend(trace.x)
                if hasattr(trace, "y") and trace.y is not None:
                    all_y.extend(trace.y)

            if all_x and all_y:
                x_min, x_max = min(all_x), max(all_x)
                y_min, y_max = min(all_y), max(all_y)

                # 添加边距
                x_margin = (x_max - x_min) * 0.05
                y_margin = (y_max - y_min) * 0.05

                print(
                    (
                        f"[DEBUG] 坐标轴范围 - X: [{x_min - x_margin}, {x_max + x_margin}], "
                        f"Y: [{y_min - y_margin}, {y_max + y_margin}]"
                    )
                )

                fig.update_xaxes(range=[x_min - x_margin, x_max + x_margin])
                fig.update_yaxes(range=[y_min - y_margin, y_max + y_margin])

        # 设置网格
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

        print(f"[DEBUG] 散点图创建完成，总共包含 {len(fig.data)} 个轨迹")
        for i, trace in enumerate(fig.data):
            print(
                (
                    f"[DEBUG] 轨迹 {i}: {trace.name}, "
                    f"数据点数: {len(trace.x) if trace.x is not None else 0}"
                )
            )

        return fig

    def get_quadrant_summary_table(self):
        """
        获取四象限统计摘要表

        Returns:
            pd.DataFrame
        """
        if not hasattr(self, "quadrant_stats") or not self.quadrant_stats:
            return None

        summary_data = []

        if self.analysis_type == "custom" and self.custom_metrics:
            # 自定义分析：根据指标数量决定表格结构
            if len(self.custom_metrics) == 1:
                # 单指标四象限
                for region_key, stats in self.quadrant_stats.items():
                    label = stats.get("label", region_key)

                    summary_data.append(
                        {
                            "区域": label,
                            "学生人数": stats["count"],
                            "占比(%)": f"{stats['percentage']:.1f}%",
                            f"{self.subject_column}平均分": f"{stats['subject_mean']:.1f}",
                            f"{self.subject_column}标准差": f"{stats['subject_std']:.1f}",
                            f"{self.total_column}平均分": f"{stats['total_mean']:.1f}",
                            f"{self.total_column}标准差": f"{stats['total_std']:.1f}",
                        }
                    )
            elif len(self.custom_metrics) == 2:
                # 双指标九宫格
                for region_key, stats in self.quadrant_stats.items():
                    label = stats.get("label", region_key)

                    summary_data.append(
                        {
                            "区域": label,
                            "学生人数": stats["count"],
                            "占比(%)": f"{stats['percentage']:.1f}%",
                            f"{self.subject_column}平均分": f"{stats['subject_mean']:.1f}",
                            f"{self.subject_column}标准差": f"{stats['subject_std']:.1f}",
                            f"{self.total_column}平均分": f"{stats['total_mean']:.1f}",
                            f"{self.total_column}标准差": f"{stats['total_std']:.1f}",
                        }
                    )
            else:
                # 多指标：每个指标的4个象限
                for region_key, stats in self.quadrant_stats.items():
                    label = stats.get("label", region_key)

                    summary_data.append(
                        {
                            "区域": label,
                            "学生人数": stats["count"],
                            "占比(%)": f"{stats['percentage']:.1f}%",
                            f"{self.subject_column}平均分": f"{stats['subject_mean']:.1f}",
                            f"{self.subject_column}标准差": f"{stats['subject_std']:.1f}",
                            f"{self.total_column}平均分": f"{stats['total_mean']:.1f}",
                            f"{self.total_column}标准差": f"{stats['total_std']:.1f}",
                        }
                    )
        elif self.analysis_type == "advanced":
            # 高级分析：9个区域
            for zone, stats in self.quadrant_stats.items():
                if "label" in stats:
                    label = stats["label"]
                else:
                    # 如果没有label，使用默认标签
                    zone_labels = {
                        1: "单科达特控，总分达特控",
                        2: "单科达特控，总分达本科",
                        3: "单科达本科，总分达特控",
                        4: "单科达本科，总分达本科",
                        5: "单科不达本科，总分达特控",
                        6: "单科不达本科，总分达本科",
                        7: "单科不达本科，总分不达本科",
                        8: "单科达本科，总分不达本科",
                        9: "单科达特控，总分不达本科",
                    }
                    label = zone_labels.get(zone, f"区域{zone}")

                summary_data.append(
                    {
                        "区域": label,
                        "学生人数": stats["count"],
                        "占比(%)": f"{stats['percentage']:.1f}%",
                        f"{self.subject_column}平均分": f"{stats['subject_mean']:.1f}",
                        f"{self.subject_column}标准差": f"{stats['subject_std']:.1f}",
                        f"{self.total_column}平均分": f"{stats['total_mean']:.1f}",
                        f"{self.total_column}标准差": f"{stats['total_std']:.1f}",
                    }
                )
        else:
            # 基础分析：4个象限
            quadrant_labels = {
                1: "第一象限",
                2: "第二象限",
                3: "第三象限",
                4: "第四象限",
            }

            for quadrant, stats in self.quadrant_stats.items():
                summary_data.append(
                    {
                        "象限": quadrant_labels[quadrant],
                        "学生人数": stats["count"],
                        "占比(%)": f"{stats['percentage']:.1f}%",
                        "单科平均分": f"{stats['subject_mean']:.1f}",
                        "单科标准差": f"{stats['subject_std']:.1f}",
                        "总分平均分": f"{stats['total_mean']:.1f}",
                        "总分标准差": f"{stats['total_std']:.1f}",
                    }
                )

        return pd.DataFrame(summary_data)

    def get_quadrant_students(self, quadrant):
        """
        获取指定象限的学生列表

        Args:
            quadrant: int, 象限编号 (1-4)

        Returns:
            pd.DataFrame
        """
        if not hasattr(self, "quadrant_stats") or quadrant not in self.quadrant_stats:
            return None

        return self.quadrant_stats[quadrant]["students"]

    def export_quadrant_data(self, filename_prefix="quadrant_analysis"):
        """
        导出四象限分析数据

        Args:
            filename_prefix: str, 文件名前缀
        """
        if not hasattr(self, "quadrant_stats") or not self.quadrant_stats:
            return False

        try:
            # 导出统计摘要
            summary_df = self.get_quadrant_summary_table()
            summary_df.to_excel(f"{filename_prefix}_summary.xlsx", index=False)

            # 根据分析类型选择不同的标签映射
            if self.analysis_type == "custom" and self.custom_metrics:
                # 自定义分析：使用区域键名作为文件名
                for region_key, stats in self.quadrant_stats.items():
                    if stats["count"] > 0:
                        students = stats["students"]
                        safe_filename = region_key.replace(" ", "_").replace("-", "_")
                        students.to_excel(
                            f"{filename_prefix}_{safe_filename}.xlsx",
                            index=False,
                        )
            elif self.analysis_type == "advanced":
                # 高级分析：9个区域的标签
                zone_labels = {
                    1: "zone1_both_special_passed",
                    2: "zone2_subject_special_total_undergraduate",
                    3: "zone3_total_special_subject_undergraduate",
                    4: "zone4_both_undergraduate_passed",
                    5: "zone5_total_special_subject_below_undergraduate",
                    6: "zone6_total_undergraduate_subject_below_undergraduate",
                    7: "zone7_both_below_undergraduate",
                    8: "zone8_subject_undergraduate_total_below_undergraduate",
                    9: "zone9_subject_special_total_below_undergraduate",
                }

                for zone, stats in self.quadrant_stats.items():
                    if stats["count"] > 0:
                        students = stats["students"]
                        students.to_excel(
                            f"{filename_prefix}_{zone_labels[zone]}.xlsx",
                            index=False,
                        )
            else:
                # 基础分析：4个象限的标签
                zone_labels = {
                    1: "quadrant1_both_passed",
                    2: "quadrant2_total_passed",
                    3: "quadrant3_both_failed",
                    4: "quadrant4_subject_passed",
                }

                for zone, stats in self.quadrant_stats.items():
                    if stats["count"] > 0:
                        students = stats["students"]
                        students.to_excel(
                            f"{filename_prefix}_{zone_labels[zone]}.xlsx",
                            index=False,
                        )

            return True
        except Exception as e:
            print(f"导出数据失败: {str(e)}")
            return False


def create_quadrant_control_panel():
    """
    创建四象限分析控制面板（本科类和特控类）

    Returns:
        dbc.Card: 控制面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader("📐 四象限分析设置"),
            dbc.CardBody(
                [
                    # 分析类型选择
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label("分析类型:"),
                                    # 分析类型控件（用于选择四象限的分析模式）
                                    dcc.RadioItems(
                                        id="quadrant_analysis_type",
                                        options=[
                                            {
                                                "label": "多层次分析（含本科类和特控类）",
                                                "value": "advanced",
                                            }
                                        ],
                                        value="advanced",
                                        inline=False,
                                    ),
                                ]
                            )
                        ],
                        className="mb-3",
                    ),
                    # 基础设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label("选择单科:"),
                                    dcc.Dropdown(
                                        id="quadrant-subject-dropdown",
                                        placeholder="选择用于四象限分析的单科成绩列",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.Label("选择总分:"),
                                    dcc.Dropdown(
                                        id="quadrant-total-dropdown",
                                        placeholder="选择用于四象限分析的总分列",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # 行政层级选择（三级联动）
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label("分析层级:"),
                                    dcc.RadioItems(
                                        id="quadrant_analysis_level_radio",
                                        options=[
                                            {
                                                "label": "全部数据",
                                                "value": "all",
                                            },
                                            {
                                                "label": "按区县",
                                                "value": "county",
                                            },
                                            {
                                                "label": "按学校",
                                                "value": "school",
                                            },
                                            {
                                                "label": "按行政班",
                                                "value": "class",
                                            },
                                        ],
                                        value="all",
                                        inline=True,
                                    ),
                                ]
                            )
                        ],
                        className="mb-3",
                    ),
                    # 三级联动菜单
                    html.Div(
                        id="cascade_filters_div",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("选择区县:"),
                                            dcc.Dropdown(
                                                id="quadrant_county_dropdown",
                                                placeholder="选择区县进行筛选（可多选）",
                                                multi=True,
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("选择学校:"),
                                            dcc.Dropdown(
                                                id="quadrant_school_dropdown",
                                                placeholder="选择学校进行筛选（可多选）",
                                                multi=True,
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("选择行政班:"),
                                            dcc.Dropdown(
                                                id="quadrant_class_dropdown",
                                                placeholder="选择行政班进行筛选（可多选）",
                                                multi=True,
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                        style={"display": "none"},
                    ),
                    # 自定义多指标设置
                    html.Div(
                        id="custom_thresholds_div",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(
                                                "📊 自定义分数线设置",
                                                className="text-primary mb-3",
                                            )
                                        ]
                                    )
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("指标名称:"),
                                            dbc.Input(
                                                id="new_metric_name",
                                                type="text",
                                                placeholder="自定义指标名称，例如：本科线",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("单科分数线:"),
                                            dbc.Input(
                                                id="new_metric_subject",
                                                type="number",
                                                placeholder="自定义单科分数线数值",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("总分分数线:"),
                                            dbc.Input(
                                                id="new_metric_total",
                                                type="number",
                                                placeholder="自定义总分分数线数值",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("操作:"),
                                            html.Div(
                                                [
                                                    dbc.Button(
                                                        "添加",
                                                        id="add_metric_btn",
                                                        color="success",
                                                        size="sm",
                                                        className="me-1",
                                                    ),
                                                    dbc.Button(
                                                        "重置",
                                                        id="reset_metrics_btn",
                                                        color="warning",
                                                        size="sm",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        width=2,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # 预设指标
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("快速添加预设指标:"),
                                            html.Div(
                                                [
                                                    dbc.Button(
                                                        "本科线",
                                                        id="add_undergraduate_btn",
                                                        color="info",
                                                        size="sm",
                                                        className="me-1 mb-1",
                                                    ),
                                                    dbc.Button(
                                                        "特控线",
                                                        id="add_special_btn",
                                                        color="danger",
                                                        size="sm",
                                                        className="me-1 mb-1",
                                                    ),
                                                    dbc.Button(
                                                        "重点线",
                                                        id="add_key_btn",
                                                        color="warning",
                                                        size="sm",
                                                        className="me-1 mb-1",
                                                    ),
                                                    dbc.Button(
                                                        "保底线",
                                                        id="add_basic_btn",
                                                        color="secondary",
                                                        size="sm",
                                                        className="mb-1",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3",
                            ),
                            # 已添加的指标列表
                            html.Div(
                                id="metrics_list",
                                children=[
                                    dbc.Alert(
                                        "暂无自定义指标，请添加或选择预设指标",
                                        color="light",
                                    )
                                ],
                            ),
                        ],
                    ),
                    # 分析选项
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Checklist(
                                        id="quadrant_options",
                                        options=[
                                            {
                                                "label": "显示学生姓名",
                                                "value": "show_names",
                                            },
                                            {
                                                "label": "显示统计表格",
                                                "value": "show_table",
                                            },
                                            {
                                                "label": "显示详细列表",
                                                "value": "show_details",
                                            },
                                        ],
                                        value=[
                                            "show_names",
                                            "show_table",
                                            "show_details",
                                        ],
                                        inline=True,
                                    )
                                ]
                            )
                        ],
                        className="mb-3",
                    ),
                    dbc.Button(
                        "开始分析",
                        id="run_quadrant_btn",
                        color="primary",
                        className="w-100",
                    ),
                ]
            ),
        ]
    )


def create_quadrant_results_panel():
    """
    创建四象限分析结果面板

    Returns:
        html.Div: 结果面板组件
    """
    return html.Div(
        [
            # 图表区域
            dbc.Card(
                [
                    dbc.CardHeader("📊 学生成绩分布图"),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="quadrant_loading",
                                children=[html.Div(id="quadrant_chart_visible")],
                            )
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # 统计摘要区域
            dbc.Card(
                [
                    dbc.CardHeader("📋 统计摘要"),
                    dbc.CardBody([html.Div(id="quadrant_summary_visible")]),
                ],
                className="mb-4",
            ),
            # 详细数据区域
            html.Div(id="quadrant_details_visible"),
            # 缓存存储组件已移除
        ]
    )


if __name__ == "__main__":
    # 测试代码
    # 创建示例数据
    np.random.seed(42)
    n_students = 200

    test_data = {
        "姓名": [f"学生{i}" for i in range(n_students)],
        "语文": np.random.normal(70, 15, n_students),
        "数学": np.random.normal(65, 18, n_students),
        "英语": np.random.normal(68, 12, n_students),
        "总分": np.random.normal(300, 50, n_students),
        "班级": np.random.choice(["一班", "二班", "三班"], n_students),
    }

    df = pd.DataFrame(test_data)

    # 创建分析器
    analyzer = QuadrantAnalyzer(df)
    analyzer.set_basic_thresholds("数学", "总分", 60, 300)
    analyzer.analyze_quadrants()

    # 创建图表
    fig = analyzer.create_quadrant_plot()

    # 显示统计摘要
    summary_df = analyzer.get_quadrant_summary_table()
    print("四象限分析结果:")
    print(summary_df.to_string(index=False))

    # 保存结果
    analyzer.export_quadrant_data("test_quadrant_analysis")

    print("\n测试完成！")


def register_quadrant_callbacks(app):
    """注册四象限分析的回调函数到Dash应用"""

    # 控制三级联动过滤器显示/隐藏的回调
    @app.callback(
        [
            Output("quadrant_county_dropdown", "style"),
            Output("quadrant_school_dropdown", "style"),
            Output("quadrant_class_dropdown", "style"),
        ],
        [
            Input("quadrant_analysis_level_radio", "value"),
        ],
        [
            State("data_store", "data"),
        ],
    )
    def update_quadrant_filter_display(analysis_level, data_json):
        """控制四象限分析三级联动过滤器的显示/隐藏"""
        if data_json is None:
            return {"display": "none"}, {"display": "none"}, {"display": "none"}

        # 根据分析层级决定显示哪些过滤器
        if analysis_level == "all":
            # 全部数据时显示所有过滤器，让用户可以进行筛选
            return {"display": "block"}, {"display": "block"}, {"display": "block"}
        elif analysis_level == "county":
            return {"display": "block"}, {"display": "none"}, {"display": "none"}
        elif analysis_level == "school":
            return {"display": "block"}, {"display": "block"}, {"display": "none"}
        elif analysis_level == "class":
            return {"display": "block"}, {"display": "block"}, {"display": "block"}
        else:
            return {"display": "block"}, {"display": "block"}, {"display": "block"}

    # 四象限分析的三级联动回调 - 合并所有联动逻辑
    @app.callback(
        [
            Output("quadrant_county_dropdown", "options"),
            Output("quadrant_county_dropdown", "value"),
            Output("quadrant_school_dropdown", "options"),
            Output("quadrant_school_dropdown", "value"),
            Output("quadrant_class_dropdown", "options"),
            Output("quadrant_class_dropdown", "value"),
        ],
        [
            Input("data_store", "data"),
            Input("quadrant_analysis_level_radio", "value"),
            Input("quadrant_county_dropdown", "value"),
            Input("quadrant_school_dropdown", "value"),
        ],
    )
    def update_quadrant_cascade_filters(data_json, analysis_level, selected_counties, selected_schools):
        """更新四象限分析的联动下拉框 - 统一处理所有联动逻辑"""
        from dash import callback_context
        
        if data_json is None:
            return [], None, [], None, [], None

        try:
            from io import StringIO
            df = pd.read_json(StringIO(data_json), orient="split")
            
            # 处理None值
            selected_counties = selected_counties or []
            selected_schools = selected_schools or []

            # 获取行政列
            admin_cols = {}
            for col in df.columns:
                col_str = str(col)
                if any(keyword in col_str for keyword in ["区县", "县区", "县", "区域", "district", "county"]):
                    admin_cols["county"] = col
                elif any(keyword in col_str for keyword in ["学校", "中学", "小学", "school"]):
                    admin_cols["school"] = col
                elif any(keyword in col_str for keyword in ["行政班", "班级", "班", "class"]):
                    admin_cols["class"] = col
            
            # 添加更详细的调试信息
            print(f"[DEBUG] 数据集列名: {list(df.columns)}")
            print(f"[DEBUG] 检测到的行政列: {admin_cols}")
            print(f"[DEBUG] 数据集形状: {df.shape}")

            # 获取触发源
            trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else None
            
            # 添加调试信息
            print(f"[DEBUG] 四象限三级联动触发源: {trigger_id}")
            print(f"[DEBUG] 选择的区县: {selected_counties}")
            print(f"[DEBUG] 选择的学校: {selected_schools}")
            
            # 初始化选项
            county_options = []
            school_options = []
            class_options = []
            
            # 获取基础选项
            if "county" in admin_cols:
                counties = sorted(df[admin_cols["county"]].dropna().unique())
                county_options = [{"label": str(c), "value": str(c)} for c in counties]
            
            print(f"[DEBUG] 行政列: {admin_cols}")

            # 根据触发源处理联动逻辑
            if trigger_id in ["data_store", "quadrant_analysis_level_radio"]:
                # 数据更新或层级变更时，重置所有选项
                print(f"[DEBUG] 数据加载/层级变更触发")
                if "school" in admin_cols:
                    schools = sorted(df[admin_cols["school"]].dropna().unique())
                    school_options = [{"label": str(s), "value": str(s)} for s in schools]
                    print(f"[DEBUG] 初始化学校选项: {[s['label'] for s in school_options]}")
                else:
                    print(f"[DEBUG] 警告: 未找到学校列，数据集中可能的列名: {[col for col in df.columns if '校' in str(col) or 'school' in str(col).lower()]}")
                
                if "class" in admin_cols:
                    classes = sorted(df[admin_cols["class"]].dropna().unique())
                    class_options = [{"label": str(c), "value": str(c)} for c in classes]
                else:
                    print(f"[DEBUG] 警告: 未找到班级列，数据集中可能的列名: {[col for col in df.columns if '班' in str(col) or 'class' in str(col).lower()]}")
                
                return county_options, None, school_options, None, class_options, None
                
            elif trigger_id == "quadrant_county_dropdown":
                # 区县选择变化时，更新学校和班级选项
                print(f"[DEBUG] 区县选择触发，选择的区县: {selected_counties}")
                if selected_counties and "county" in admin_cols and "school" in admin_cols:
                    county_col = admin_cols["county"]
                    school_col = admin_cols["school"]
                    
                    filtered_df = df[df[county_col].isin(selected_counties)]
                    schools = sorted(filtered_df[school_col].dropna().unique())
                    school_options = [{"label": str(s), "value": str(s)} for s in schools]
                    print(f"[DEBUG] 筛选后学校选项: {[s['label'] for s in school_options]}")
                    
                    # 获取对应区县的班级选项
                    if "class" in admin_cols:
                        classes = sorted(filtered_df[admin_cols["class"]].dropna().unique())
                        class_options = [{"label": str(c), "value": str(c)} for c in classes]
                    print(f"[DEBUG] 对应班级选项: {[c['label'] for c in class_options]}")
                    
                    return county_options, selected_counties, school_options, None, class_options, None
                else:
                    # 如果没有选择区县，返回所有学校和班级选项
                    if "school" in admin_cols:
                        schools = sorted(df[admin_cols["school"]].dropna().unique())
                        school_options = [{"label": str(s), "value": str(s)} for s in schools]
                    
                    if "class" in admin_cols:
                        classes = sorted(df[admin_cols["class"]].dropna().unique())
                        class_options = [{"label": str(c), "value": str(c)} for c in classes]
                    
                    return county_options, selected_counties, school_options, selected_schools, class_options, None
                
            elif trigger_id == "quadrant_school_dropdown":
                # 学校选择变化时，更新班级选项，同时保持学校选项
                print(f"[DEBUG] 学校选择触发，选择的学校: {selected_schools}")
                
                # 重新计算学校选项，确保选择后选项不会消失
                current_counties = selected_counties if selected_counties else []
                
                if current_counties and "county" in admin_cols and "school" in admin_cols:
                    # 有区县筛选时，重新获取该区县下的学校选项
                    county_col = admin_cols["county"]
                    school_col = admin_cols["school"]
                    filtered_df = df[df[county_col].isin(current_counties)]
                    schools = sorted(filtered_df[school_col].dropna().unique())
                    school_options = [{"label": str(s), "value": str(s)} for s in schools]
                    print(f"[DEBUG] 重新计算学校选项: {[s['label'] for s in school_options]}")
                elif "school" in admin_cols:
                    # 没有区县筛选时，获取所有学校选项
                    schools = sorted(df[admin_cols["school"]].dropna().unique())
                    school_options = [{"label": str(s), "value": str(s)} for s in schools]
                    print(f"[DEBUG] 获取所有学校选项: {[s['label'] for s in school_options]}")
                else:
                    school_options = []
                    print(f"[DEBUG] 未找到学校列")
                
                # 处理班级选项
                if selected_schools and "county" in admin_cols and "school" in admin_cols:
                    # 有学校选择时，筛选班级
                    filtered_df = df.copy()
                    
                    # 应用区县筛选
                    if current_counties:
                        county_col = admin_cols["county"]
                        filtered_df = filtered_df[filtered_df[county_col].isin(current_counties)]
                    
                    # 应用学校筛选
                    school_col = admin_cols["school"]
                    filtered_df = filtered_df[filtered_df[school_col].isin(selected_schools)]
                    
                    # 获取班级选项
                    if "class" in admin_cols:
                        class_col = admin_cols["class"]
                        classes = sorted(filtered_df[class_col].dropna().unique())
                        class_options = [{"label": str(c), "value": str(c)} for c in classes]
                        print(f"[DEBUG] 筛选后班级选项: {[c['label'] for c in class_options]}")
                else:
                    # 没有学校选择时，根据区县筛选班级或显示所有班级
                    filtered_df = df.copy()
                    if current_counties and "county" in admin_cols:
                        county_col = admin_cols["county"]
                        filtered_df = filtered_df[filtered_df[county_col].isin(current_counties)]
                    
                    if "class" in admin_cols:
                        class_col = admin_cols["class"]
                        classes = sorted(filtered_df[class_col].dropna().unique())
                        class_options = [{"label": str(c), "value": str(c)} for c in classes]
                        print(f"[DEBUG] 区县筛选后班级选项: {[c['label'] for c in class_options]}")
                
                return county_options, selected_counties, school_options, selected_schools, class_options, None

            # 默认返回
            print(f"[DEBUG] 默认返回")
            return county_options, selected_counties, school_options, selected_schools, class_options, None

        except Exception as e:
            print(f"更新四象限分析下拉框失败: {e}")
            return [], None, [], None, [], None

    @app.callback(
        [
            Output("quadrant_chart", "children"),
            Output("quadrant_summary", "children"),
            Output("quadrant_details", "children"),
        ],
        [Input("run_quadrant_btn", "n_clicks")],
        [
            State("quadrant_analysis_type", "value"),
            State("quadrant-subject-dropdown", "value"),
            State("quadrant-total-dropdown", "value"),
            State("custom_metrics_store", "data"),
            State("quadrant_options", "value"),
            State("quadrant_analysis_level_radio", "value"),
            State("quadrant_county_dropdown", "value"),
            State("quadrant_school_dropdown", "value"),
            State("quadrant_class_dropdown", "value"),
            State("data_store", "data"),
        ],
    )
    def update_quadrant_analysis(
        n_clicks,
        analysis_type,
        subject_col,
        total_col,
        custom_metrics,
        options,
        analysis_level,
        selected_counties,
        selected_schools,
        selected_classes,
        data_json,
    ):
        if n_clicks is None or not subject_col or not total_col or data_json is None:
            return None, None, None

        try:
            from io import StringIO

            df = pd.read_json(StringIO(data_json), orient="split")
            original_count = len(df)
            print(f"原始数据量: {original_count}")

            # 应用行政层级筛选（与综合分析器保持一致）
            if analysis_level != "all":
                admin_cols = {}
                for col in df.columns:
                    col_str = str(col)
                    # 扩展区县列的匹配规则
                    if any(
                        keyword in col_str
                        for keyword in [
                            "区县",
                            "县区", 
                            "县",
                            "区域",
                            "district",
                            "county",
                        ]
                    ):
                        admin_cols["county"] = col
                    # 扩展学校列的匹配规则
                    elif any(
                        keyword in col_str for keyword in ["学校", "中学", "小学", "school"]
                    ):
                        admin_cols["school"] = col
                    # 扩展班级列的匹配规则
                    elif any(
                        keyword in col_str for keyword in ["行政班", "班级", "班", "class"]
                    ):
                        admin_cols["class"] = col

                # 根据分析层级进行筛选（支持层级组合）
                if analysis_level == "county" and selected_counties and "county" in admin_cols:
                    county_col = admin_cols["county"]
                    print(f"区县筛选: {selected_counties}, 列名: {county_col}")
                    df = df[df[county_col].isin(selected_counties)]
                    
                elif analysis_level == "school" and selected_schools and "school" in admin_cols:
                    school_col = admin_cols["school"]
                    print(f"学校筛选: {selected_schools}, 列名: {school_col}")
                    df = df[df[school_col].isin(selected_schools)]
                    
                elif analysis_level == "class" and selected_classes and "class" in admin_cols:
                    class_col = admin_cols["class"]
                    print(f"班级筛选: {selected_classes}, 列名: {class_col}")
                    df = df[df[class_col].isin(selected_classes)]

            filtered_count = len(df)
            print(f"筛选后数据量: {filtered_count}, 筛选掉了 {original_count - filtered_count} 条数据")

            # 检查筛选后的数据是否为空
            if df.empty:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 筛选结果为空", className="alert-heading"),
                        html.P("根据所选的行政层级条件，没有找到符合条件的数据"),
                    ],
                    color="warning",
                )
                return error_alert, None, None

            # 检查数据列是否存在
            if subject_col not in df.columns or total_col not in df.columns:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 列不存在", className="alert-heading"),
                        html.P("请确保选择的数据列在数据中存在"),
                    ],
                    color="danger",
                )
                return error_alert, None, None

            # 创建分析器
            analyzer = QuadrantAnalyzer(df)

            # 检查自定义指标是否有效
            if not custom_metrics:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 自定义指标未设置", className="alert-heading"),
                        html.P("请至少添加一个自定义指标进行分析"),
                    ],
                    color="danger",
                )
                return error_alert, None, None

            # 处理 custom_metrics 的各种可能格式
            if isinstance(custom_metrics, str):
                try:
                    custom_metrics = json.loads(custom_metrics)
                except json.JSONDecodeError:
                    error_alert = dbc.Alert(
                        [
                            html.H5(
                                "❌ 自定义指标格式错误",
                                className="alert-heading",
                            ),
                            html.P("自定义指标字符串无法解析为有效格式"),
                        ],
                        color="danger",
                    )
                    return error_alert, None, None

            # 确保 custom_metrics 是列表格式
            if isinstance(custom_metrics, dict):
                custom_metrics_list = []
                for key, value in custom_metrics.items():
                    if isinstance(value, dict) and "threshold" in value:
                        custom_metrics_list.append(
                            {
                                "name": key,
                                "subject_threshold": value.get("threshold", 0),
                                "total_threshold": 0,
                            }
                        )
                    elif isinstance(value, dict) and "name" in value:
                        if "subject_threshold" in value and "total_threshold" in value:
                            custom_metrics_list.append(value)
                custom_metrics = custom_metrics_list
            elif not isinstance(custom_metrics, list):
                custom_metrics = []

            # 验证转换后的指标列表
            valid_metrics = []
            for metric in custom_metrics:
                if isinstance(metric, dict) and "name" in metric:
                    if "subject_threshold" not in metric:
                        metric["subject_threshold"] = 0
                    if "total_threshold" not in metric:
                        metric["total_threshold"] = 0
                    valid_metrics.append(metric)

            custom_metrics = valid_metrics

            if not custom_metrics:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 自定义指标格式错误", className="alert-heading"),
                        html.P("自定义指标格式不正确，请重新设置"),
                    ],
                    color="danger",
                )
                return error_alert, None, None

            # 设置分析参数
            analyzer.subject_column = subject_col
            analyzer.total_column = total_col

            # 设置自定义指标
            try:
                analyzer.set_custom_metrics(custom_metrics)
            except Exception as e:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 设置自定义指标失败", className="alert-heading"),
                        html.P(f"错误信息: {str(e)}"),
                    ],
                    color="danger",
                )
                return error_alert, None, None

            # 执行分析
            try:
                analyzer.analyze_quadrants()

                if (
                    not hasattr(analyzer, "quadrant_stats")
                    or not analyzer.quadrant_stats
                ):
                    error_alert = dbc.Alert(
                        [
                            html.H5("❌ 分析结果为空", className="alert-heading"),
                            html.P("四象限分析未产生有效结果，请检查数据设置"),
                        ],
                        color="warning",
                    )
                    return error_alert, None, None

            except Exception as e:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 四象限分析执行失败", className="alert-heading"),
                        html.P(f"错误信息: {str(e)}"),
                    ],
                    color="danger",
                )
                return error_alert, None, None

            # 创建图表
            show_names = "show_names" in (options or [])
            fig = analyzer.create_quadrant_plot(show_names=show_names)

            chart = dcc.Graph(
                figure=fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": ["pan2d", "lasso2d", "select2d"],
                },
                style={"width": "100%", "height": "700px"},
            )

            # 创建分析范围信息
            analysis_scope_info = []
            if analysis_level != "all":
                scope_text = "分析范围: "
                if analysis_level == "county" and selected_counties:
                    scope_text += f"区县 - {', '.join(selected_counties)}"
                elif analysis_level == "school" and selected_schools:
                    scope_text += f"学校 - {', '.join(selected_schools)}"
                elif analysis_level == "class" and selected_classes:
                    scope_text += f"行政班 - {', '.join(selected_classes)}"

                analysis_scope_info.append(
                    dbc.Alert(
                        [
                            html.H6("📍 " + scope_text, className="alert-heading"),
                            html.P(f"本次分析基于 {len(df)} 名学生数据（原始数据: {original_count} 条）"),
                        ],
                        color="info",
                        className="mb-3",
                    )
                )

            # 创建统计摘要
            summary = None
            if "show_table" in (options or []):
                summary_df = analyzer.get_quadrant_summary_table()
                if summary_df is not None and not summary_df.empty:
                    summary_elements = analysis_scope_info + [
                        dbc.Table.from_dataframe(
                            summary_df,
                            striped=True,
                            bordered=True,
                            hover=True,
                            size="sm",
                            className="mt-3",
                        )
                    ]
                    summary = html.Div(summary_elements)
                elif analysis_scope_info:
                    summary = html.Div(analysis_scope_info)

            # 创建详细数据
            details = None
            if "show_details" in (options or []):
                from dash import dash_table

                quadrant_tabs = []

                for region_key, stats in analyzer.quadrant_stats.items():
                    if stats["count"] > 0:
                        students_df = stats["students"]
                        stats_info = html.Div(
                            [
                                html.P(
                                    f"学生人数: {stats['count']} 人 ({stats['percentage']:.1f}%)",
                                    className="text-info",
                                ),
                                html.P(
                                    f"{subject_col}平均分: {stats['subject_mean']:.1f} ± {stats['subject_std']:.1f}",
                                    className="text-success",
                                ),
                                html.P(
                                    f"{total_col}平均分: {stats['total_mean']:.1f} ± {stats['total_std']:.1f}",
                                    className="text-primary",
                                ),
                            ],
                            className="mb-3",
                        )

                        display_columns = []
                        important_columns = ["姓名", subject_col, total_col]

                        for col in important_columns:
                            if col in students_df.columns:
                                display_columns.append({"name": col, "id": col})

                        for col in students_df.columns:
                            if col not in important_columns:
                                display_columns.append({"name": col, "id": col})

                        table = dash_table.DataTable(
                            data=students_df.to_dict("records"),
                            columns=display_columns,
                            style_table={
                                "overflowX": "auto",
                                "height": "400px",
                                "minHeight": "300px",
                            },
                            style_cell={
                                "textAlign": "left",
                                "padding": "8px",
                                "fontSize": "12px",
                                "minWidth": "100px",
                            },
                            style_header={
                                "backgroundColor": "rgb(230, 230, 230)",
                                "fontWeight": "bold",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "rgb(248, 248, 248)",
                                }
                            ],
                            page_size=15,
                            fixed_rows={"headers": True},
                            virtualization=False,
                        )

                        tab_content = html.Div([stats_info, table])

                        quadrant_tabs.append(
                            dbc.Tab(
                                label=stats["label"],
                                tab_id=f"region_{region_key}",
                                children=tab_content,
                            )
                        )

                if quadrant_tabs:
                    details = dbc.Card(
                        [
                            dbc.CardHeader("📝 各区域学生详细列表"),
                            dbc.CardBody([dbc.Tabs(quadrant_tabs)]),
                        ],
                        className="mt-3",
                    )

            return chart, summary, details

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 四象限分析失败", className="alert-heading"),
                    html.P(f"错误信息: {str(e)}"),
                    html.Details(
                        [
                            html.Summary("🔍 详细错误信息"),
                            html.Pre(
                                error_details,
                                style={
                                    "fontSize": "12px",
                                    "backgroundColor": "#f8f9fa",
                                    "padding": "10px",
                                    "borderRadius": "5px",
                                },
                            ),
                        ]
                    ),
                ],
                color="danger",
            )
            return error_alert, None, None
