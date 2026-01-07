#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有效群体统计分析模块
基于自定义分数线对学生群体进行统计分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging
from datetime import datetime

# 数据库功能已移除
DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


class EffectiveGroupAnalyzer:
    """有效群体统计分析器"""

    def __init__(self, data: pd.DataFrame = None):
        """
        初始化分析器

        Args:
            data: 原始成绩数据
        """
        self.data = data
        self.raw_data_id = None
        self.results = {}
        self.score_thresholds = {
            "本科线": 450,  # 默认本科分数线
            "特控线": 520,  # 默认特控分数线
        }

    def set_data(self, data: pd.DataFrame):
        """设置分析数据"""
        self.data = self._preprocess_data(data)
        self.results = {}

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理数据，处理数据类型转换

        Args:
            data: 原始数据

        Returns:
            pd.DataFrame: 预处理后的数据
        """
        processed_data = data.copy()

        # 转换数值列：将category类型和object类型的数值列转换为float
        for col in processed_data.columns:
            # 跳过明显的非数值列
            if col in [
                "区县",
                "学校",
                "行政班",
                "姓名",
                "学号",
                "班级",
                "考号",
                "考生号",
                "排名",
                "选科组合",
                "准考证",
                "考生类型",
                "等级",
                "准考证号",
            ] or col.endswith("等级"):
                continue

            # 尝试转换数值列
            if processed_data[col].dtype == "category":
                try:
                    # 对于category类型，先转换为字符串，再尝试转换为数值
                    processed_data[col] = processed_data[col].astype(str)
                    processed_data[col] = pd.to_numeric(
                        processed_data[col], errors="coerce"
                    )
                except Exception as e:
                    logger.warning(f"无法转换列 {col} 为数值类型: {e}")
            elif processed_data[col].dtype == "object":
                try:
                    processed_data[col] = pd.to_numeric(
                        processed_data[col], errors="coerce"
                    )
                except Exception as e:
                    logger.warning(f"无法转换列 {col} 为数值类型: {e}")

        # 填充NaN值为0（针对转换失败的数值）
        numeric_columns = processed_data.select_dtypes(include=[np.number]).columns
        processed_data[numeric_columns] = processed_data[numeric_columns].fillna(0)

        logger.info("数据预处理完成")
        return processed_data

    def set_score_thresholds(self, thresholds: Dict[str, float]):
        """
        设置自定义分数线

        Args:
            thresholds: 分数线字典，格式: {'本科线': 450, '特控线': 520}
        """
        self.score_thresholds.update(thresholds)
        logger.info(f"分数线已更新: {self.score_thresholds}")

    def identify_effective_groups(self, total_column: str) -> Dict[str, pd.DataFrame]:
        """
        识别各分数线对应的有效群体

        Args:
            total_column: 总分列名

        Returns:
            Dict: 各分数线对应的学生群体数据
        """
        if self.data is None or total_column not in self.data.columns:
            raise ValueError(f"数据或总分列 '{total_column}' 不存在")

        groups = {}
        for threshold_name, threshold_score in self.score_thresholds.items():
            # 筛选达到分数线的学生
            group_data = self.data[self.data[total_column] >= threshold_score].copy()
            groups[threshold_name] = group_data

            logger.info(f"{threshold_name}群体识别完成: {len(group_data)}人")

        return groups

    def calculate_subject_averages(
        self, group_data: pd.DataFrame, subject_columns: List[str]
    ) -> Dict[str, float]:
        """
        计算各学科平均分

        Args:
            group_data: 群体数据
            subject_columns: 学科列名列表

        Returns:
            Dict: 各学科平均分
        """
        averages = {}
        for subject in subject_columns:
            if subject in group_data.columns:
                # 确保数据是数值类型
                try:
                    # 转换为数值，如果失败则用0
                    numeric_values = pd.to_numeric(group_data[subject], errors="coerce")
                    # 过滤掉NaN值后计算平均值
                    valid_values = numeric_values.dropna()
                    if len(valid_values) > 0:
                        avg_score = valid_values.mean()
                    else:
                        avg_score = 0.0
                    averages[subject] = round(float(avg_score), 2)
                except Exception as e:
                    logger.warning(f"计算学科 '{subject}' 平均分失败: {e}")
                    averages[subject] = 0.0
            else:
                logger.warning(f"学科列 '{subject}' 不存在")
                averages[subject] = 0.0

        return averages

    def calculate_deviation_rates(
        self, group_data: pd.DataFrame, subject_columns: List[str]
    ) -> Dict[str, float]:
        """
        计算离均率 (各学科平均分与所有学科平均分的相对差距)

        Args:
            group_data: 群体数据
            subject_columns: 学科列名列表

        Returns:
            Dict: 各学科离均率
        """
        deviation_rates = {}

        # 先计算每个学生的总分（只包括有效的学科列）
        valid_subject_columns = [
            col for col in subject_columns if col in group_data.columns
        ]

        if not valid_subject_columns:
            logger.warning("没有有效的学科列用于计算离均率")
            return {subject: 0.0 for subject in subject_columns}

        try:
            # 转换学科数据为数值类型
            subject_data = pd.DataFrame()
            for col in valid_subject_columns:
                subject_data[col] = pd.to_numeric(
                    group_data[col], errors="coerce"
                ).fillna(0)

            # 计算所有学科的平均分（每个学生的各学科平均分，然后所有学生平均）
            student_subject_averages = subject_data.mean(
                axis=1
            )  # 每个学生的各学科平均分
            overall_subject_avg = (
                student_subject_averages.mean()
            )  # 所有学生的各学科平均分的平均

            for subject in subject_columns:
                if subject in valid_subject_columns:
                    subject_avg = subject_data[subject].mean()

                    # 计算离均率：(学科平均分 - 所有学科平均分) / 所有学科平均分 * 100
                    if overall_subject_avg > 0:
                        deviation_rate = (
                            (subject_avg - overall_subject_avg) / overall_subject_avg
                        ) * 100
                    else:
                        deviation_rate = 0.0

                    deviation_rates[subject] = round(float(deviation_rate), 2)
                else:
                    deviation_rates[subject] = 0.0

        except Exception as e:
            logger.error(f"计算离均率失败: {e}")
            return {subject: 0.0 for subject in subject_columns}

        return deviation_rates

    def calculate_school_subject_analysis(
        self, group_data: pd.DataFrame, subject_columns: List[str]
    ) -> Dict[str, Any]:
        """
        从学校层面分析各学科的均分和离均率

        Args:
            group_data: 群体数据
            subject_columns: 学科列名列表

        Returns:
            Dict: 学校学科分析结果
        """
        if "学校" not in group_data.columns:
            logger.warning("数据中缺少'学校'列")
            return None

        # 计算群体各学科平均分
        group_averages = {}
        for subject in subject_columns:
            if subject in group_data.columns:
                try:
                    numeric_values = pd.to_numeric(
                        group_data[subject], errors="coerce"
                    ).dropna()
                    if len(numeric_values) > 0:
                        group_averages[subject] = numeric_values.mean()
                    else:
                        group_averages[subject] = 0.0
                except Exception as e:
                    logger.warning(f"计算群体学科 '{subject}' 平均分失败: {e}")
                    group_averages[subject] = 0.0

        school_analysis = {}

        # 按学校分组分析
        for school_name, school_data in group_data.groupby("学校"):
            school_subject_stats = {}

            for subject in subject_columns:
                if subject in school_data.columns and subject in group_averages:
                    try:
                        # 计算学校学科平均分
                        school_numeric_values = pd.to_numeric(
                            school_data[subject], errors="coerce"
                        ).dropna()
                        if len(school_numeric_values) > 0:
                            school_subject_avg = school_numeric_values.mean()
                        else:
                            school_subject_avg = 0.0

                        group_subject_avg = group_averages[subject]

                        # 计算离均率：(学校学科均分 - 群体学科均分) / 群体学科均分 * 100
                        if group_subject_avg > 0:
                            deviation_rate = (
                                (school_subject_avg - group_subject_avg)
                                / group_subject_avg
                            ) * 100
                        else:
                            deviation_rate = 0.0

                        school_subject_stats[subject] = {
                            "学校学科均分": round(float(school_subject_avg), 2),
                            "群体学科均分": round(float(group_subject_avg), 2),
                            "离均率": round(float(deviation_rate), 2),
                            "学校人数": len(school_data),
                        }
                    except Exception as e:
                        logger.warning(
                            f"计算学校 '{school_name}' 学科 '{subject}' 统计失败: {e}"
                        )
                        school_subject_stats[subject] = {
                            "学校学科均分": 0.0,
                            "群体学科均分": 0.0,
                            "离均率": 0.0,
                            "学校人数": len(school_data),
                        }

            school_analysis[school_name] = {
                "学科统计": school_subject_stats,
                "学校总人数": len(school_data),
            }

        # 生成各学科的学校排名
        subject_rankings = {}
        for subject in subject_columns:
            subject_rankings[subject] = self._generate_school_subject_ranking(
                school_analysis, subject
            )

        return {"学校分析": school_analysis, "学科排名": subject_rankings}

    def _generate_school_subject_ranking(
        self, school_analysis: Dict, subject: str
    ) -> List[Dict]:
        """
        生成特定学科的学校排名

        Args:
            school_analysis: 学校分析数据
            subject: 学科名称

        Returns:
            List: 排名后的学校学科统计
        """
        ranking_data = []

        for school_name, school_data in school_analysis.items():
            if subject in school_data["学科统计"]:
                subject_stats = school_data["学科统计"][subject]
                ranking_data.append(
                    {
                        "学校": school_name,
                        "学科": subject,
                        "学校均分": subject_stats["学校学科均分"],
                        "群体均分": subject_stats["群体学科均分"],
                        "离均率(%)": subject_stats["离均率"],
                        "学校人数": subject_stats["学校人数"],
                    }
                )

        # 按学校均分降序排序
        ranking_data.sort(key=lambda x: x["学校均分"], reverse=True)

        # 添加排名
        for i, data in enumerate(ranking_data, 1):
            data["排名"] = i

        return ranking_data

    def generate_subject_rankings(
        self, group_data: pd.DataFrame, subject_columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        生成学科排名

        Args:
            group_data: 群体数据
            subject_columns: 学科列名列表

        Returns:
            List: 排序后的学科统计信息
        """
        subject_stats = []

        # 先计算每个学生的总分（只包括有效的学科列）
        valid_subject_columns = [
            col for col in subject_columns if col in group_data.columns
        ]

        if not valid_subject_columns:
            logger.warning("没有有效的学科列用于生成排名")
            return []

        try:
            # 转换学科数据为数值类型
            subject_data = pd.DataFrame()
            for col in valid_subject_columns:
                subject_data[col] = pd.to_numeric(
                    group_data[col], errors="coerce"
                ).fillna(0)

            # 计算所有学科的平均分（每个学生的各学科平均分，然后所有学生平均）
            student_subject_averages = subject_data.mean(
                axis=1
            )  # 每个学生的各学科平均分
            overall_subject_avg = (
                student_subject_averages.mean()
            )  # 所有学生的各学科平均分的平均

            for subject in subject_columns:
                if subject in valid_subject_columns:
                    try:
                        # 计算统计信息
                        numeric_values = subject_data[subject]
                        avg_score = numeric_values.mean()
                        std_score = numeric_values.std()
                        max_score = numeric_values.max()
                        min_score = numeric_values.min()

                        # 计算离均率：(学科平均分 - 所有学科平均分) / 所有学科平均分 * 100
                        if overall_subject_avg > 0:
                            deviation_rate = (
                                (avg_score - overall_subject_avg) / overall_subject_avg
                            ) * 100
                        else:
                            deviation_rate = 0.0

                        subject_stats.append(
                            {
                                "学科": subject,
                                "平均分": round(float(avg_score), 2),
                                "标准差": round(float(std_score), 2),
                                "最高分": round(float(max_score), 2),
                                "最低分": round(float(min_score), 2),
                                "离均率(%)": round(float(deviation_rate), 2),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"生成学科 '{subject}' 排名失败: {e}")
                        subject_stats.append(
                            {
                                "学科": subject,
                                "平均分": 0.0,
                                "标准差": 0.0,
                                "最高分": 0.0,
                                "最低分": 0.0,
                                "离均率(%)": 0.0,
                            }
                        )
        except Exception as e:
            logger.error(f"生成学科排名失败: {e}")
            return []

        # 按平均分降序排序
        subject_stats.sort(key=lambda x: x["平均分"], reverse=True)

        # 添加排名
        for i, stat in enumerate(subject_stats, 1):
            stat["排名"] = i

        return subject_stats

    def analyze_group_hierarchy(
        self,
        group_data: pd.DataFrame,
        group_columns: List[str],
        subject_columns: List[str],
    ) -> Dict[str, Any]:
        """
        按层级结构分析群体

        Args:
            group_data: 群体数据
            group_columns: 分组列 ['区县', '学校', '行政班']
            subject_columns: 学科列名列表

        Returns:
            Dict: 层级分析结果
        """
        hierarchy_results = {}

        for i, level in enumerate(group_columns):
            if level in group_data.columns:
                level_stats = {}

                # 按当前层级分组
                grouped = group_data.groupby(level)

                for group_name, group_df in grouped:
                    # 计算该组的基本统计
                    stats = {
                        "人数": len(group_df),
                        "各学科平均分": self.calculate_subject_averages(
                            group_df, subject_columns
                        ),
                        "各学科离均率": self.calculate_deviation_rates(
                            group_df, subject_columns
                        ),
                        "学科排名": self.generate_subject_rankings(
                            group_df, subject_columns
                        ),
                    }

                    level_stats[str(group_name)] = stats

                hierarchy_results[level] = level_stats

        return hierarchy_results

    def perform_comprehensive_analysis(
        self, total_column: str, subject_columns: List[str]
    ) -> Dict[str, Any]:
        """
        执行完整的有效群体统计分析

        Args:
            total_column: 总分列名
            subject_columns: 学科列名列表
            group_columns: 分组列，默认为 ['区县', '学校', '行政班']

        Returns:
            Dict: 完整分析结果
        """
        logger.info("开始执行有效群体统计分析...")

        # 识别有效群体
        effective_groups = self.identify_effective_groups(total_column)

        comprehensive_results = {}

        for threshold_name, group_data in effective_groups.items():
            if len(group_data) == 0:
                logger.warning(f"{threshold_name}群体无数据")
                continue

            logger.info(f"分析{threshold_name}群体...")

            # 基础统计
            group_stats = {
                "群体名称": threshold_name,
                "分数线": self.score_thresholds[threshold_name],
                "群体人数": len(group_data),
                "总分平均分": round(group_data[total_column].mean(), 2),
                "总分最高分": round(group_data[total_column].max(), 2),
                "总分最低分": round(group_data[total_column].min(), 2),
                "总分标准差": round(group_data[total_column].std(), 2),
            }

            # 学科分析
            subject_averages = self.calculate_subject_averages(
                group_data, subject_columns
            )
            deviation_rates = self.calculate_deviation_rates(
                group_data, subject_columns
            )
            subject_rankings = self.generate_subject_rankings(
                group_data, subject_columns
            )

            # 学校学科分析
            school_subject_analysis = self.calculate_school_subject_analysis(
                group_data, subject_columns
            )

            # 整合结果
            comprehensive_results[threshold_name] = {
                **group_stats,
                "学科平均分": subject_averages,
                "学科离均率": deviation_rates,
                "学科排名": subject_rankings,
                "学校学科分析": school_subject_analysis,
                "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        self.results = comprehensive_results

        logger.info("有效群体统计分析完成")
        return comprehensive_results

    # 数据库保存功能已移除

    def generate_statistics_tables(self) -> Dict[str, pd.DataFrame]:
        """
        生成统计表格

        Returns:
            Dict: 表格名称到DataFrame的映射
        """
        tables = {}

        for threshold_name, result in self.results.items():
            # 创建群体情况统计表
            table_data = []

            # 基础信息
            basic_info = {
                "指标": "基础信息",
                "项目": "群体人数",
                "数值": result["群体人数"],
                "备注": f"达到{result['分数线']}分以上",
            }
            table_data.append(basic_info)

            # 总分统计
            total_stats = [
                {
                    "指标": "总分统计",
                    "项目": "总分平均分",
                    "数值": result["总分平均分"],
                    "备注": "",
                },
                {
                    "指标": "总分统计",
                    "项目": "总分最高分",
                    "数值": result["总分最高分"],
                    "备注": "",
                },
                {
                    "指标": "总分统计",
                    "项目": "总分最低分",
                    "数值": result["总分最低分"],
                    "备注": "",
                },
                {
                    "指标": "总分统计",
                    "项目": "总分标准差",
                    "数值": result["总分标准差"],
                    "备注": "",
                },
            ]
            table_data.extend(total_stats)

            # 学科平均分
            for subject, avg_score in result["学科平均分"].items():
                table_data.append(
                    {
                        "指标": "学科平均分",
                        "项目": subject,
                        "数值": avg_score,
                        "备注": "",
                    }
                )

            # 学科离均率
            for subject, rate in result["学科离均率"].items():
                table_data.append(
                    {
                        "指标": "学科离均率(%)",
                        "项目": subject,
                        "数值": rate,
                        "备注": "",
                    }
                )

            # 学科排名
            for rank_info in result["学科排名"]:
                table_data.append(
                    {
                        "指标": f"学科排名(第{rank_info['排名']}名)",
                        "项目": rank_info["学科"],
                        "数值": rank_info["平均分"],
                        "备注": f"离均率:{rank_info['离均率(%)']}%",
                    }
                )

            # 创建DataFrame
            table_title = f"{threshold_name}群体情况统计"
            tables[table_title] = pd.DataFrame(table_data)

        return tables

    def export_to_excel(self, output_path: str) -> bool:
        """
        导出分析结果到Excel文件

        Args:
            output_path: 输出文件路径

        Returns:
            bool: 导出是否成功
        """
        try:
            tables = self.generate_statistics_tables()

            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                for table_name, df in tables.items():
                    df.to_excel(
                        writer, sheet_name=table_name[:31], index=False
                    )  # Excel工作表名称最大31字符

            logger.info(f"有效群体分析结果已导出到: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出Excel失败: {e}")
            return False

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        获取分析摘要统计

        Returns:
            Dict: 摘要统计信息
        """
        if not self.results:
            return None

        summary = {
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "分数线设置": self.score_thresholds,
            "分析群体数量": len(self.results),
            "各群体人数": {},
        }

        for threshold_name, result in self.results.items():
            summary["各群体人数"][threshold_name] = result["群体人数"]

        return summary
