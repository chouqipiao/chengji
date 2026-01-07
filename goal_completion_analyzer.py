#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分数线统计分析模块
统计达到各分数线的人数，按区县-学校-班级三个层级进行数据分析
支持本科线、特控线、高分线等多层级分数线统计
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go

# 数据库功能已移除


class GoalCompletionAnalyzer:
    """分数线统计分析器"""

    def __init__(self, df: pd.DataFrame = None):
        """
        初始化分数线分析器

        Args:
            df: DataFrame, 包含学生成绩数据
        """
        self.df = df
        self.raw_data_id = None
        self.db = None
        self.logger = logging.getLogger(__name__)

        # 分数线配置
        self.score_line_config = {
            "undergraduate": {"name": "本科线", "min_score": 450},
            "special_control": {"name": "特控线", "min_score": 520},
            "high_score": {"name": "高分线", "min_score": 600},
        }

        # 分析结果缓存
        self.analysis_results = {}

    def set_data(self, df: pd.DataFrame):
        """设置数据"""
        self.df = df

    def store_analysis_results(self, results: Dict[str, Any]):
        """
        存储分析结果
        
        Args:
            results: 分析结果字典
        """
        self.analysis_results.update(results)

    def set_score_line_config(self, config: Dict[str, Dict[str, Any]]):
        """
        设置分数线配置

        Args:
            config: 分数线配置字典
                {
                    'line_type': {'name': str, 'min_score': float},
                    ...
                }
        """
        self.score_line_config = config

    def get_default_score_lines(self) -> Dict[str, Dict[str, Any]]:
        """获取默认分数线配置"""
        return {
            "undergraduate": {"name": "本科线", "min_score": 450},
            "special_control": {"name": "特控线", "min_score": 520},
            "high_score": {"name": "高分线", "min_score": 600},
        }

    def find_total_score_column(self) -> Optional[str]:
        """查找总分列"""
        if self.df is None:
            return None

        # 优先查找明显的总分列
        total_keywords = ["总分", "总成绩", "total", "Total"]
        for col in self.df.columns:
            for keyword in total_keywords:
                if keyword in col:
                    return col

        # 查找数值列中最大可能的总分列
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            # 选择值域最大的列作为总分列
            col_ranges = {
                col: self.df[col].max() - self.df[col].min() for col in numeric_cols
            }
            total_col = max(col_ranges, key=col_ranges.get)
            return total_col

        return None

    def find_hierarchy_columns(self) -> Dict[str, str]:
        """查找层级分组列"""
        if self.df is None:
            return {}

        hierarchy_map = {}

        # 查找区县列
        for col in self.df.columns:
            if "区县" in col:
                hierarchy_map["county"] = col
                break

        # 查找学校列
        for col in self.df.columns:
            if "学校" in col:
                hierarchy_map["school"] = col
                break

        # 查找班级列
        for col in self.df.columns:
            if "行政班" in col:
                hierarchy_map["class"] = col
                break
            elif "班级" in col and "class" not in hierarchy_map:
                hierarchy_map["class"] = col

        return hierarchy_map

    def analyze_score_line_completion(
        self, line_type: str, target_column: str = None, analysis_levels: List[str] = None
    ) -> Dict[str, Any]:
        """
        分析指定分数线的达标情况

        Args:
            line_type: str, 分数线类型
            target_column: str, 目标列名（如总分列）
            analysis_levels: List[str], 分析层级列表 ["county", "school", "class"]

        Returns:
            dict: 分数线达标分析结果
        """
        if self.df is None:
            self.logger.error("未设置数据")
            return None

        if line_type not in self.score_line_config:
            self.logger.error(f"未知分数线类型: {line_type}")
            return None

        line_info = self.score_line_config[line_type]
        target_score = line_info["min_score"]

        # 查找目标列
        if target_column is None:
            target_column = self.find_total_score_column()

        if target_column is None:
            self.logger.error("未找到目标分析列")
            return None

        # 移除特控线强制使用总分的限制，特控线可以适用于任何科目成绩

        # 数据清洗
        clean_df = self.df.dropna(subset=[target_column])
        clean_df = clean_df[
            clean_df[target_column].apply(
                lambda x: pd.notnull(x) and isinstance(x, (int, float))
            )
        ]

        total_students = len(clean_df)
        if total_students == 0:
            self.logger.error("没有有效数据")
            return None

        # 计算目标完成情况
        completed_mask = clean_df[target_column] >= target_score
        completed_students = clean_df[completed_mask]
        completion_rate = len(completed_students) / total_students * 100

        # 基础统计
        basic_stats = {
            "line_type": line_type,
            "line_name": line_info["name"],
            "line_score": target_score,
            "target_column": target_column,
            "total_students": total_students,
            "reached_students": len(completed_students),
            "reach_rate": completion_rate,
            "avg_score": completed_students[target_column].mean() if len(completed_students) > 0 else 0,  # 达到分数线群体的平均分
            "max_score": completed_students[target_column].max() if len(completed_students) > 0 else 0,  # 达到分数线群体的最高分
            "min_score": completed_students[target_column].min() if len(completed_students) > 0 else 0,  # 达到分数线群体的最低分
            "std_score": completed_students[target_column].std() if len(completed_students) > 0 else 0,  # 达到分数线群体的标准差
            # 达线群体平均分相对于分数线的差距（正值表示平均分高于分数线，负值表示低于分数线）
            "score_gap_to_line": completed_students[target_column].mean() - target_score if len(completed_students) > 0 else 0,
            # 百分比差距（相对于分数线的百分比），当分数线为0时返回0以避免除零
            "score_gap_pct": (
                (completed_students[target_column].mean() - target_score)
                / target_score
                * 100
                if len(completed_students) > 0 and target_score != 0
                else 0
            ),
        }
        
        # 添加达到分数线的学生姓名列表
        if len(completed_students) > 0:
            name_col = None
            for col in ["姓名", "学生姓名", "学生", "name"]:
                if col in completed_students.columns:
                    name_col = col
                    break
            
            if name_col:
                # 获取达到分数线学生的姓名和分数信息
                reached_students_info = []
                for _, student in completed_students.iterrows():
                    reached_students_info.append({
                        "姓名": student[name_col],
                        "分数": student[target_column],
                        "学校": student.get("学校", ""),
                        "班级": student.get("行政班", student.get("班级", "")),
                    })
                basic_stats["reached_students_list"] = reached_students_info
            else:
                basic_stats["reached_students_list"] = []
        else:
            basic_stats["reached_students_list"] = []

        # 按层级分析（根据用户选择的层级）
        hierarchy_cols = self.find_hierarchy_columns()
        hierarchy_stats = {}
        
        # 如果没有指定分析层级，默认使用全区和学校层级
        if analysis_levels is None:
            analysis_levels = ["county", "school"]

        for level, col in hierarchy_cols.items():
            if level in analysis_levels and col in clean_df.columns:
                level_stats = (
                    clean_df.groupby(col)
                    .apply(
                        lambda group: self._calculate_group_line_stats(
                            group, target_column, target_score
                        )
                    )
                    .to_dict()
                )
                hierarchy_stats[level] = level_stats

        # 分布分析
        distribution_stats = self._analyze_score_distribution(
            clean_df, target_column, target_score
        )

        # 结果汇总
        result = {
            "basic_stats": basic_stats,
            "hierarchy_stats": hierarchy_stats,
            "distribution_stats": distribution_stats,
            "completed_students_data": (
                completed_students.to_dict("records")
                if len(completed_students) <= 100
                else None
            ),
            "uncompleted_students_data": (
                clean_df[~completed_mask].to_dict("records")
                if len(clean_df[~completed_mask]) <= 100
                else None
            ),
        }

        self.analysis_results[line_type] = result
        return result

    def _calculate_group_line_stats(
        self, group: pd.DataFrame, target_column: str, target_score: float
    ) -> Dict[str, Any]:
        """计算分组的分数线达标统计"""
        total_count = len(group)
        reached_count = (group[target_column] >= target_score).sum()
        reach_rate = reached_count / total_count * 100 if total_count > 0 else 0

        # 获取达到分数线的群体数据
        reached_group = group[group[target_column] >= target_score]
        
        # 计算达到分数线群体的统计指标
        if len(reached_group) > 0:
            reached_avg_score = reached_group[target_column].mean()
            reached_max_score = reached_group[target_column].max()
            reached_min_score = reached_group[target_column].min()
            score_gap_to_line = reached_avg_score - target_score
            score_gap_pct = (
                (reached_avg_score - target_score) / target_score * 100
                if target_score != 0
                else 0
            )
        else:
            # 如果没有达到分数线的学生，使用0值
            reached_avg_score = 0
            reached_max_score = 0
            reached_min_score = 0
            score_gap_to_line = -target_score  # 显示为负的分数线值
            score_gap_pct = -100  # 显示为-100%

        return {
            "total_count": total_count,
            "reached_count": reached_count,
            "reach_rate": reach_rate,
            "avg_score": reached_avg_score,  # 达到分数线群体的平均分
            "max_score": reached_max_score,  # 达到分数线群体的最高分
            "min_score": reached_min_score,  # 达到分数线群体的最低分
            # 达线群体平均分相对于分数线的差距
            "score_gap_to_line": score_gap_to_line,
            # 百分比差距（相对于分数线的百分比）
            "score_gap_pct": score_gap_pct,
        }

    def _analyze_score_distribution(
        self, df: pd.DataFrame, target_column: str, target_score: float
    ) -> Dict[str, Any]:
        """分析分数分布"""
        scores = df[target_column]

        # 创建分数区间
        min_score = int(scores.min())
        max_score = int(scores.max())

        # 计算分布区间
        if target_score - 50 < min_score:
            start = min_score
        else:
            start = target_score - 50

        end = max_score + 10
        step = 10

        score_ranges = list(range(start, end + step, step))

        # 计算各区间的学生数量
        distribution = {}
        for i in range(len(score_ranges) - 1):
            lower = score_ranges[i]
            upper = score_ranges[i + 1]
            mask = (scores >= lower) & (scores < upper)
            count = mask.sum()

            range_label = f"{lower}-{upper}"
            if target_score >= lower and target_score < upper:
                range_label += " (分数线)"

            distribution[range_label] = count

        return {
            "score_ranges": distribution,
            "target_position": target_score,
            "below_target": (scores < target_score).sum(),
            "above_target": (scores >= target_score).sum(),
            "distribution_details": {
                "quartiles": scores.quantile([0.25, 0.5, 0.75]).to_dict(),
                "mean": scores.mean(),
                "std": scores.std(),
            },
        }

    def compare_multiple_score_lines(
        self, line_types: List[str] = None, target_column: str = None, analysis_levels: List[str] = None
    ) -> Dict[str, Any]:
        """
        比较多个分数线的达标情况

        Args:
            line_types: List[str], 分数线类型列表
            target_column: str, 目标列名
            analysis_levels: List[str], 分析层级列表

        Returns:
            dict: 多分数线比较结果
        """
        if line_types is None:
            line_types = list(self.score_line_config.keys())

        comparison_results = {}

        for line_type in line_types:
            if line_type in self.score_line_config:
                result = self.analyze_score_line_completion(line_type, target_column, analysis_levels)
                if result:
                    comparison_results[line_type] = result["basic_stats"]

        # 计算分数线之间的对比数据
        if len(comparison_results) > 1:
            comparison_summary = {
                "highest_reach_rate": max(
                    stats["reach_rate"] for stats in comparison_results.values()
                ),
                "lowest_reach_rate": min(
                    stats["reach_rate"] for stats in comparison_results.values()
                ),
                "line_reach_trend": {
                    line_type: stats["reach_rate"]
                    for line_type, stats in comparison_results.items()
                },
                "score_lines_comparison": {
                    line_type: stats["target_score"]
                    for line_type, stats in comparison_results.items()
                },
            }
            comparison_results["comparison_summary"] = comparison_summary

        return comparison_results

    def analyze_subject_goal_completion(
        self, subject_goals: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        分析多科目目标完成情况

        Args:
            subject_goals: Dict[str, float], 科目目标分数字典
                {'科目名': 目标分数, ...}

        Returns:
            dict: 多科目目标完成分析结果
        """
        if self.df is None:
            self.logger.error("未设置数据")
            return None

        subject_results = {}

        for subject, target_score in subject_goals.items():
            if subject in self.df.columns:
                subject_data = self.df.dropna(subset=[subject])

                if len(subject_data) > 0:
                    reached_count = (subject_data[subject] >= target_score).sum()
                    reach_rate = reached_count / len(subject_data) * 100

                    subject_results[subject] = {
                        "line_score": target_score,
                        "total_students": len(subject_data),
                        "reached_students": reached_count,
                        "reach_rate": reach_rate,
                        "avg_score": subject_data[subject].mean(),
                        "std_score": subject_data[subject].std(),
                    }

        # 计算整体完成情况
        if subject_results:
            overall_stats = {
                "total_subjects": len(subject_results),
                "avg_reach_rate": np.mean(
                    [stats["reach_rate"] for stats in subject_results.values()]
                ),
                "highest_reach_rate": max(
                    [stats["reach_rate"] for stats in subject_results.values()]
                ),
                "lowest_reach_rate": min(
                    [stats["reach_rate"] for stats in subject_results.values()]
                ),
                "subject_ranking": sorted(
                    subject_results.items(),
                    key=lambda x: x[1]["reach_rate"],
                    reverse=True,
                ),
            }
            subject_results["overall_stats"] = overall_stats

        return subject_results

    def generate_goal_completion_report(self, goal_types: List[str] = None) -> str:
        """
        生成目标完成统计报告

        Args:
            goal_types: List[str], 目标类型列表

        Returns:
            str: 报告文本
        """
        if goal_types is None:
            goal_types = list(self.goal_config.keys())

        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("目标完成统计分析报告")
        report_lines.append("=" * 60)

        for goal_type in goal_types:
            if goal_type in self.goal_config:
                result = self.analyze_goal_completion(goal_type)
                if result:
                    basic = result["basic_stats"]
                    report_lines.append(f"\n【{basic['line_name']}】")
                    report_lines.append(f"分数线: {basic['line_score']}")
                    report_lines.append(f"总学生数: {basic['total_students']}")
                    report_lines.append(f"达标人数: {basic['reached_students']}")
                    report_lines.append(f"达标率: {basic['reach_rate']:.2f}%")
                    report_lines.append(f"平均分: {basic['avg_score']:.2f}")
                    report_lines.append(f"最高分: {basic['max_score']:.2f}")
                    report_lines.append(f"最低分: {basic['min_score']:.2f}")
                    report_lines.append(
                        f"与线差距: {basic['score_gap_to_line']:.2f}"
                    )

                    # 层级统计
                    if "hierarchy_stats" in result and result["hierarchy_stats"]:
                        report_lines.append("\n分层统计:")
                        for level, stats in result["hierarchy_stats"].items():
                            report_lines.append(f"  {level}:")
                            for group, group_stats in stats.items():
                                report_lines.append(
                                    (
                                        f"    {group}: {group_stats['reach_rate']:.2f}% ("
                                        f"{group_stats['reached_count']}/{group_stats['total_count']})"
                                    )
                                )

        report_lines.append("\n" + "=" * 60)
        return "\n".join(report_lines)

    # 数据库存储功能已移除

    def create_reach_rate_chart(
        self, results: Dict[str, Any], chart_type: str = "bar"
    ) -> go.Figure:
        """
        创建达标率可视化图表

        Args:
            results: dict, 分析结果
            chart_type: str, 图表类型 ('bar', 'pie', 'funnel')

        Returns:
            plotly.graph_objects.Figure
        """
        if "basic_stats" not in results:
            return None

        basic = results["basic_stats"]

        if chart_type == "bar":
            fig = go.Figure()

            # 添加达标率柱状图
            fig.add_trace(
                go.Bar(
                    x=["达标情况"],
                    y=[basic["reach_rate"]],
                    name=f"{basic['line_name']}达标率",
                    text=[f"{basic['reach_rate']:.1f}%"],
                    textposition="auto",
                    marker_color=[
                        "#10b981" if basic["reach_rate"] >= 50 else "#ef4444"
                    ],
                )
            )

            # 添加基准线
            fig.add_hline(
                y=50,
                line_dash="dash",
                line_color="red",
                annotation_text="基准达标率 50%",
            )

            fig.update_layout(
                title=f"{basic['line_name']}达标率分析",
                yaxis_title="达标率 (%)",
                height=400,
                showlegend=False,
            )

        elif chart_type == "pie":
            reached = basic["reached_students"]
            unreached = basic["total_students"] - reached

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["达标", "未达标"],
                        values=[reached, unreached],
                        hole=0.3,
                        marker_colors=["#10b981", "#ef4444"],
                        textinfo="label+percent+value",
                        textfont_size=12,
                    )
                ]
            )

            fig.update_layout(title=f"{basic['line_name']}达标情况分布", height=400)

        elif chart_type == "funnel":
            fig = go.Figure(
                go.Funnel(
                    y=["总人数", "达标人数", "未达标人数"],
                    x=[
                        basic["total_students"],
                        basic["reached_students"],
                        basic["total_students"] - basic["reached_students"],
                    ],
                    textinfo="value+percent initial",
                    marker_color=["#6366f1", "#10b981", "#ef4444"],
                )
            )

            fig.update_layout(title=f"{basic['line_name']}达标漏斗图", height=400)

        return fig

    # NOTE: A single, full implementation of `create_multiple_goals_comparison_chart`
    # and `create_hierarchy_comparison_chart_for_multiple_goals` exists later in
    # this file. Earlier placeholder/duplicate definitions were removed to
    # avoid redefinition errors.

    def create_hierarchy_comparison_chart(self, results: Dict[str, Any]) -> go.Figure:
        """
        创建层级对比图表

        Args:
            results: dict, 分析结果

        Returns:
            plotly.graph_objects.Figure
        """
        if "hierarchy_stats" not in results or not results["hierarchy_stats"]:
            return None

        fig = go.Figure()

        colors = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"]
        color_idx = 0

        for level, groups in results["hierarchy_stats"].items():
            if groups:
                group_names = list(groups.keys())
                reach_rates = [
                    groups[name]["reach_rate"] for name in group_names
                ]

                fig.add_trace(
                    go.Bar(
                        x=group_names,
                        y=reach_rates,
                        name=f"{level}层级",
                        marker_color=colors[color_idx % len(colors)],
                        text=[f"{rate:.1f}%" for rate in reach_rates],
                        textposition="auto",
                    )
                )

                color_idx += 1

        fig.update_layout(
            title="各层级分数线达标率对比",
            xaxis_title="分组",
            yaxis_title="达标率 (%)",
            barmode="group",
            height=500,
            xaxis=dict(
                tickangle=-45,
                automargin=True,
                title_font=dict(size=12),
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                title_font=dict(size=12),
                tickfont=dict(size=10),
            ),
            margin=dict(b=120),  # 增加底部边距
        )

        return fig

    def create_multiple_score_lines_comparison_chart(
        self, all_results: Dict[str, Dict[str, Any]], chart_type: str = "bar"
    ) -> go.Figure:
        """
        创建多分数线达标率对比图表

        Args:
            all_results: dict, 所有分数线的分析结果
            chart_type: str, 图表类型

        Returns:
            plotly.graph_objects.Figure
        """
        if not all_results:
            return go.Figure()

        line_names = []
        reach_rates = []
        reached_students = []

        for line_type, results in all_results.items():
            if "basic_stats" in results:
                basic = results["basic_stats"]
                line_names.append(basic.get("line_name", line_type))
                reach_rates.append(basic.get("reach_rate", 0))
                reached_students.append(basic.get("reached_students", 0))

        if chart_type == "bar":
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=line_names,
                        y=reach_rates,
                        text=[f"{rate:.1f}%" for rate in reach_rates],
                        textposition="auto",
                        marker_color=["#10b981", "#3b82f6", "#f59e0b"][
                            : len(line_names)
                        ],
                    )
                ]
            )

        elif chart_type == "pie":
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=line_names,
                        values=reach_rates,
                        textinfo="label+percent",
                        hole=0.3,
                    )
                ]
            )

        elif chart_type == "funnel":
            fig = go.Figure(
                data=go.Funnel(
                    y=line_names,
                    x=reach_rates,
                    textinfo="value+percent initial",
                )
            )

        elif chart_type == "line":
            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=line_names,
                        y=reach_rates,
                        mode="lines+markers",
                        line=dict(width=3),
                        marker=dict(size=10),
                    )
                ]
            )
        else:
            # 默认柱状图
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=line_names,
                        y=reach_rates,
                        text=[f"{rate:.1f}%" for rate in reach_rates],
                        textposition="auto",
                        marker_color=["#10b981", "#3b82f6", "#f59e0b"][
                            : len(line_names)
                        ],
                    )
                ]
            )

        fig.update_layout(
            title="各分数线达标率对比",
            yaxis_title="达标率 (%)" if chart_type != "pie" else "",
            height=400,
        )

        return fig

    def create_hierarchy_comparison_chart_for_multiple_score_lines(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> go.Figure:
        """
        为多分数线创建层级对比图表

        Args:
            all_results: dict, 所有分数线的分析结果

        Returns:
            plotly.graph_objects.Figure
        """
        if not all_results:
            return go.Figure()

        fig = go.Figure()
        colors = ["#10b981", "#3b82f6", "#f59e0b"]
        color_idx = 0

        for line_type, results in all_results.items():
            if "hierarchy_stats" in results:
                hierarchy_stats = results["hierarchy_stats"]
                line_name = results.get("basic_stats", {}).get("line_name", line_type)

                # 显示区县级别的对比
                if "county" in hierarchy_stats:
                    county_data = hierarchy_stats["county"]
                    if county_data:
                        group_names = list(county_data.keys())
                        reach_rates = [
                            county_data[name]["reach_rate"] for name in group_names
                        ]

                        fig.add_trace(
                            go.Bar(
                                x=group_names,
                                y=reach_rates,
                                name=f"{line_name}",
                                marker_color=colors[color_idx % len(colors)],
                                text=[f"{rate:.1f}%" for rate in reach_rates],
                                textposition="auto",
                            )
                        )

                        color_idx += 1

        fig.update_layout(
            title="各分数线在不同区县的达标率对比",
            xaxis_title="区县",
            yaxis_title="达标率 (%)",
            barmode="group",
            height=500,
            xaxis_tickangle=-45,
            xaxis=dict(
                tickangle=-45,
                automargin=True,
                title_font=dict(size=12),
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                title_font=dict(size=12),
                tickfont=dict(size=10),
            ),
            margin=dict(b=120),  # 增加底部边距
        )

        return fig
