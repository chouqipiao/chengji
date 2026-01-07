#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三级联动统计分析模块
实现区县-学校-行政班三级联动菜单和类别选择的统计分析功能
"""

import dash
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, dash_table
from typing import Dict, List
import logging
from io import StringIO

# 数据库功能已移除
DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


class CascadeStatisticsAnalyzer:
    """三级联动统计分析器"""

    def __init__(self, data: pd.DataFrame):
        """
        初始化三级联动统计分析器

        Args:
            data: DataFrame, 包含学生成绩数据
        """
        self.data = data.copy()
        self.raw_data_id = None
        self.logger = logging.getLogger(__name__)

        # 数据库功能已移除
        self.db = None

        # 清理列名中的换行符和空白字符
        self.data.columns = [
            str(col).strip().replace("\n", "").replace("\r", "")
            for col in self.data.columns
        ]

        # 识别行政层级列
        self.admin_columns = self._get_administrative_columns()

        # 识别学科列
        self.subject_columns = self._detect_subject_columns()

        # 定义所有可能的类别 - 兼容多种列名格式
        self.all_categories = [
            # 基础科目
            "语文",
            "语文分数",
            "数学",
            "数学分数",
            "英语",
            "英语分数",
            "日语",
            "日语分数",
            "俄语",
            "俄语分数",
            "法语",
            "法语分数",
            "德语",
            "德语分数",
            # 理科科目
            "物理",
            "物理分数",
            "化学",
            "化学原分",
            "化学等级",
            "化学赋分",
            "化学分数",
            "生物",
            "生物原分",
            "生物等级",
            "生物赋分",
            "生物分数",
            # 文科科目
            "政治",
            "政治原分",
            "政治等级",
            "政治赋分",
            "政治分数",
            "地理",
            "地理原分",
            "地理等级",
            "地理赋分",
            "地理分数",
            "历史",
            "历史分数",
            # 总分科目
            "新高考原始总分",
            "新高考原始总分分数",
            "新高考语数英总分",
            "新高考语数英总分分数",
            "新高考3+1总分",
            "新高考3+1总分分数",
            "新高考总分",
            "新高考总分分数",
        ]

        # 筛选实际存在的类别
        self.available_categories = self._get_available_categories()

        self.logger.info(f"数据形状: {self.data.shape}")
        self.logger.info(f"检测到行政列: {self.admin_columns}")
        self.logger.info(f"检测到学科列: {self.subject_columns}")
        self.logger.info(f"可用类别: {self.available_categories}")

    def _get_administrative_columns(self) -> Dict[str, str]:
        """
        获取行政层级列名
        返回格式：{'county': '区县列名', 'school': '学校列名', 'class': '行政班列名'}
        """
        admin_columns = {}

        # 定义精确匹配的列名，优先级从高到低
        priority_columns = {
            "county": ["区县"],
            "school": ["学校"],
            "class": ["行政班"],
        }

        # 首先尝试精确匹配
        for admin_type, possible_names in priority_columns.items():
            for name in possible_names:
                if name in self.data.columns:
                    admin_columns[admin_type] = name
                    break

        # 如果没有精确匹配，再进行模糊匹配
        if len(admin_columns) < 3:
            for col in self.data.columns:
                col_str = str(col).strip()  # 清理空白字符

                # 区县列的模糊匹配（排除包含其他关键词的列）
                if "county" not in admin_columns and "区县" in col_str:
                    # 排除明显不是区县列的情况
                    exclude_keywords = ["排", "名", "组合", "统计", "分析"]
                    if not any(keyword in col_str for keyword in exclude_keywords):
                        admin_columns["county"] = col

                # 学校列的模糊匹配
                elif (
                    "school" not in admin_columns
                    and "学校" in col_str
                    and "行政班" not in col_str
                ):
                    admin_columns["school"] = col

                # 行政班列的模糊匹配
                elif "class" not in admin_columns and "行政班" in col_str:
                    admin_columns["class"] = col

        return admin_columns

    def _detect_subject_columns(self) -> List[str]:
        """检测学科列"""
        subject_keywords = [
            # 基础科目
            "语文",
            "数学",
            "英语",
            "日语",
            "俄语",
            "法语",
            "德语",
            # 理科科目
            "物理",
            "化学",
            "生物",
            # 文科科目
            "政治",
            "地理",
            "历史",
            # 总分科目
            "新高考",
        ]

        subject_columns = []
        for col in self.data.columns:
            col_str = str(col)
            # 排除包含排名信息的列和行政列
            if (
                any(keyword in col_str for keyword in subject_keywords)
                and "班排" not in col_str
                and "区县排" not in col_str
                and "市排" not in col_str
                and "省排" not in col_str
                and "区县" not in col_str
                and "学校" not in col_str
                and "行政班" not in col_str
                and "姓名" not in col_str
                and "选科组合" not in col_str
            ):
                subject_columns.append(col)

        return subject_columns

    def _get_available_categories(self) -> List[str]:
        """获取实际存在的类别 - 只保留分数列，排除排名和等级列"""
        available = []

        # 直接遍历数据中的所有列，筛选符合条件的分数列
        for col in self.data.columns:
            col_str = str(col)

            # 只保留包含"分数"或"原分"或"赋分"的列，或者基础科目名称
            # 排除所有包含"排"、"等级"的列
            if (
                "分数" in col_str or "原分" in col_str or "赋分" in col_str
            ) or col_str in [
                "语文",
                "数学",
                "英语",
                "日语",
                "俄语",
                "法语",
                "德语",
                "物理",
                "化学",
                "生物",
                "政治",
                "地理",
                "历史",
                "新高考总分",
            ]:
                # 排除包含排名、等级和行政信息的列
                exclude_patterns = [
                    "排",
                    "等级",
                    "区县",
                    "学校",
                    "行政班",
                    "姓名",
                    "选科组合",
                    "班排",
                    "级排",
                    "市排",
                    "省排",
                ]
                if not any(pattern in col_str for pattern in exclude_patterns):
                    available.append(col_str)

        # 按照标准顺序排序
        category_order = {
            "语文分数": 1,
            "语文": 1,
            "数学分数": 2,
            "数学": 2,
            "英语分数": 3,
            "英语": 3,
            "日语分数": 4,
            "日语": 4,
            "俄语分数": 5,
            "俄语": 5,
            "法语分数": 6,
            "法语": 6,
            "德语分数": 7,
            "德语": 7,
            "物理分数": 8,
            "物理": 8,
            "化学原分": 9,
            "化学分数": 9,
            "化学赋分": 10,
            "生物原分": 11,
            "生物分数": 11,
            "生物赋分": 12,
            "政治原分": 13,
            "政治分数": 13,
            "政治赋分": 14,
            "地理原分": 15,
            "地理分数": 15,
            "地理赋分": 16,
            "历史分数": 17,
            "历史": 17,
            "新高考原始总分分数": 18,
            "新高考原始总分": 18,
            "新高考语数英总分分数": 19,
            "新高考语数英总分": 19,
            "新高考3+1总分分数": 20,
            "新高考3+1总分": 20,
            "新高考总分分数": 21,
            "新高考总分": 21,
        }

        def sort_key(col_name):
            # 尝试找到匹配的排序键
            for key, order in category_order.items():
                if key in col_name:
                    return order
            return 999  # 未知的类别排在最后

        available.sort(key=sort_key)
        return available

    def calculate_county_statistics(self, categories: List[str] = None) -> pd.DataFrame:
        """
        计算各区县统计数据

        Args:
            categories: 类别列表

        Returns:
            DataFrame: 区县统计数据
        """
        if not categories:
            return pd.DataFrame()

        # 过滤数据
        filtered_data = self.data.copy()

        if "county" not in self.admin_columns:
            self.logger.warning("未找到区县列")
            return pd.DataFrame()

        county_col = self.admin_columns["county"]

        results = []

        for category in categories:
            if category not in self.data.columns:
                self.logger.warning(f"类别 '{category}' 不存在于数据中")
                continue

            # 数据类型验证和清洗
            category_data = filtered_data[[county_col, category]].copy()
            if not pd.api.types.is_numeric_dtype(category_data[category]):
                category_data[category] = pd.to_numeric(
                    category_data[category], errors="coerce"
                )

            # 移除缺失值和无穷大值
            category_data = category_data[category_data[category].notna()]
            category_data = category_data[np.isfinite(category_data[category])]

            if category_data.empty:
                self.logger.warning(f"类别 '{category}' 没有有效数据")
                continue

            # 按区县分组计算统计指标
            county_stats = (
                category_data.groupby(county_col)[category]
                .agg(["mean", "std", "min", "max", "count"])
                .round(2)
            )

            # 计算排名（按均值降序）
            county_stats["均值排名"] = (
                county_stats["mean"].rank(ascending=False, method="min").astype(int)
            )

            # 计算离均率（使用清洗后的数据计算整体均值）
            overall_mean = category_data[category].mean()
            if (
                overall_mean != 0
                and pd.notna(overall_mean)
                and np.isfinite(overall_mean)
            ):
                county_stats["离均率"] = (
                    (county_stats["mean"] - overall_mean) / overall_mean * 100
                ).round(2)
            else:
                county_stats["离均率"] = 0.0

            # 重命名列
            county_stats = county_stats.rename(
                columns={
                    "mean": "均值",
                    "std": "标准差",
                    "min": "最小值",
                    "max": "最大值",
                    "count": "样本数",
                }
            )

            # 重置索引，将区县名作为列
            county_stats = county_stats.reset_index()
            county_stats = county_stats.rename(columns={county_col: "区县"})

            # 添加类别列
            county_stats["类别"] = category

            # 调整列顺序
            county_stats = county_stats[
                [
                    "类别",
                    "区县",
                    "均值",
                    "均值排名",
                    "离均率",
                    "标准差",
                    "最大值",
                    "最小值",
                    "样本数",
                ]
            ]

            results.append(county_stats)

        if results:
            final_df = pd.concat(results, ignore_index=True)

            # 保存到数据库
            if self.db and self.raw_data_id and not final_df.empty:
                try:
                    # 为每个类别保存统计结果
                    for category in categories:
                        category_data = final_df[final_df["类别"] == category].to_dict(
                            "records"
                        )
                        if category_data:
                            self.db.store_cascade_statistics(
                                raw_data_id=self.raw_data_id,
                                analysis_level="county",
                                county_filter=None,
                                category=category,
                                metric_type="basic_statistics",
                                statistics={
                                    "data": category_data,
                                    "summary": final_df.describe().to_dict(),
                                },
                            )

                    self.logger.info("区县统计结果已保存到数据库")
                except Exception as e:
                    self.logger.error(f"保存区县统计结果到数据库失败: {e}")

            return final_df
        else:
            return pd.DataFrame()

    def calculate_school_statistics(
        self, county: str = None, categories: List[str] = None
    ) -> pd.DataFrame:
        """
        计算区县内各学校统计数据

        Args:
            county: 区县名称，如果为None则计算所有区县
            categories: 类别列表

        Returns:
            DataFrame: 学校统计数据
        """
        if not categories:
            return pd.DataFrame()

        # 过滤数据
        filtered_data = self.data.copy()

        if county and "county" in self.admin_columns:
            county_col = self.admin_columns["county"]
            filtered_data = filtered_data[filtered_data[county_col] == county]

        if "school" not in self.admin_columns:
            self.logger.warning("未找到学校列")
            return pd.DataFrame()

        school_col = self.admin_columns["school"]

        results = []

        for category in categories:
            if category not in self.data.columns:
                self.logger.warning(f"类别 '{category}' 不存在于数据中")
                continue

            # 数据类型验证和清洗
            category_data = filtered_data[[school_col, category]].copy()
            if not pd.api.types.is_numeric_dtype(category_data[category]):
                category_data[category] = pd.to_numeric(
                    category_data[category], errors="coerce"
                )

            # 移除缺失值和无穷大值
            category_data = category_data[category_data[category].notna()]
            category_data = category_data[np.isfinite(category_data[category])]

            if category_data.empty:
                self.logger.warning(f"类别 '{category}' 没有有效数据")
                continue

            # 按学校分组计算统计指标
            school_stats = (
                category_data.groupby(school_col)[category]
                .agg(["mean", "std", "min", "max", "count"])
                .round(2)
            )

            # 计算排名（按均值降序）
            school_stats["均值排名"] = (
                school_stats["mean"].rank(ascending=False, method="min").astype(int)
            )

            # 计算离均率（使用清洗后的数据计算整体均值）
            overall_mean = category_data[category].mean()
            if (
                overall_mean != 0
                and pd.notna(overall_mean)
                and np.isfinite(overall_mean)
            ):
                school_stats["离均率"] = (
                    (school_stats["mean"] - overall_mean) / overall_mean * 100
                ).round(2)
            else:
                school_stats["离均率"] = 0.0

            # 重命名列
            school_stats = school_stats.rename(
                columns={
                    "mean": "均值",
                    "std": "标准差",
                    "min": "最小值",
                    "max": "最大值",
                    "count": "样本数",
                }
            )

            # 重置索引，将学校名作为列
            school_stats = school_stats.reset_index()
            school_stats = school_stats.rename(columns={school_col: "学校"})

            # 添加类别列
            school_stats["类别"] = category

            # 调整列顺序
            school_stats = school_stats[
                [
                    "类别",
                    "学校",
                    "均值",
                    "均值排名",
                    "离均率",
                    "标准差",
                    "最大值",
                    "最小值",
                    "样本数",
                ]
            ]

            results.append(school_stats)

        if results:
            final_df = pd.concat(results, ignore_index=True)

            # 保存到数据库
            if self.db and self.raw_data_id and not final_df.empty:
                try:
                    # 为每个类别保存统计结果
                    for category in categories:
                        category_data = final_df[final_df["类别"] == category].to_dict(
                            "records"
                        )
                        if category_data:
                            self.db.store_cascade_statistics(
                                raw_data_id=self.raw_data_id,
                                analysis_level="county",
                                county_filter=None,
                                category=category,
                                metric_type="basic_statistics",
                                statistics={
                                    "data": category_data,
                                    "summary": final_df.describe().to_dict(),
                                },
                            )

                    self.logger.info("区县统计结果已保存到数据库")
                except Exception as e:
                    self.logger.error(f"保存区县统计结果到数据库失败: {e}")

            return final_df
        else:
            return pd.DataFrame()

    def determine_subject_combination(self, row: pd.Series) -> str:
        """
        根据学生成绩确定选科组合
        按照新高考"3+1+2"模式识别选科组合

        Args:
            row: 学生成绩数据行

        Returns:
            str: 选科组合（如"物化生"、"历地政"等）
        """
        # 定义科目映射 - 兼容多种列名格式
        subject_mapping = {
            "物": ["物理", "物理分数"],  # 物理 - 首选科目
            "历": ["历史", "历史分数"],  # 历史 - 首选科目（如果存在）
            "化": [
                "化学",
                "化学分数",
                "化学原分",
                "化学等级",
                "化学赋分",
            ],  # 化学 - 再选科目
            "生": [
                "生物",
                "生物分数",
                "生物原分",
                "生物等级",
                "生物赋分",
            ],  # 生物 - 再选科目
            "政": [
                "政治",
                "政治分数",
                "政治原分",
                "政治等级",
                "政治赋分",
            ],  # 政治 - 再选科目
            "地": [
                "地理",
                "地理分数",
                "地理原分",
                "地理等级",
                "地理赋分",
            ],  # 地理 - 再选科目
        }

        selected_subjects = []
        first_choice = None  # 物理或历史（"1"的选择）
        second_choices = []  # 再选科目（"2"的选择，化学、生物、政治、地理中选2门）

        for subject_code, columns in subject_mapping.items():
            # 检查该科目是否有有效成绩
            has_subject = False
            for col in columns:
                if col in row.index:
                    score = row[col]
                    if pd.notna(score) and score > 0:
                        has_subject = True
                        break

            if has_subject:
                selected_subjects.append(subject_code)

                # 判断是首选科目还是再选科目
                if subject_code in ["物", "历"]:
                    if first_choice is None:
                        first_choice = subject_code
                    else:
                        # 如果有两个首选科目，取分数较高的
                        first_score = 0
                        second_score = 0

                        for col in subject_mapping[first_choice]:
                            if col in row.index and pd.notna(row[col]):
                                score = row[col]
                                # 过滤异常值（超过100分，通常这是单科分数）
                                if 0 <= score <= 100:
                                    first_score = max(first_score, score)

                        for col in columns:
                            if col in row.index and pd.notna(row[col]):
                                score = row[col]
                                # 过滤异常值（超过100分，通常这是单科分数）
                                if 0 <= score <= 100:
                                    second_score = max(second_score, score)

                        if second_score > first_score:
                            first_choice = subject_code
                else:
                    # 再选科目
                    second_choices.append(subject_code)

        # 按照新高考规则处理选科组合
        if first_choice is None:
            return "未确定"

        # 确保再选科目正好2门 - 如果不足2门，从缺失的科目中补充
        all_second_subjects = ["化", "生", "政", "地"]

        # 如果再选科目少于2门，补充缺失的科目
        if len(second_choices) < 2:
            for subject_code in all_second_subjects:
                if subject_code not in second_choices:
                    second_choices.append(subject_code)
                    if len(second_choices) >= 2:
                        break

        # 确保再选科目正好2门
        if len(second_choices) >= 2:
            # 按照标准顺序排序组合
            standard_order = {
                "物": 0,
                "历": 1,
                "化": 2,
                "生": 3,
                "政": 4,
                "地": 5,
            }
            combination = [first_choice] + second_choices[:2]
            combination.sort(key=lambda x: standard_order.get(x, 99))
            return "".join(combination)
        else:
            return "未确定"

    def calculate_class_statistics(
        self, school: str = None, categories: List[str] = None
    ) -> pd.DataFrame:
        """
        计算学校内各行政班统计数据

        Args:
            school: 学校名称，如果为None则计算所有学校
            categories: 类别列表

        Returns:
            DataFrame: 行政班统计数据
        """
        if not categories:
            return pd.DataFrame()

        # 过滤数据
        filtered_data = self.data.copy()

        if school and "school" in self.admin_columns:
            school_col = self.admin_columns["school"]
            filtered_data = filtered_data[filtered_data[school_col] == school]

        if "class" not in self.admin_columns:
            self.logger.warning("未找到行政班列")
            return pd.DataFrame()

        class_col = self.admin_columns["class"]

        results = []

        for category in categories:
            if category not in self.data.columns:
                self.logger.warning(f"类别 '{category}' 不存在于数据中")
                continue

            # 数据类型验证和清洗
            category_data = filtered_data[[class_col, category]].copy()
            if not pd.api.types.is_numeric_dtype(category_data[category]):
                category_data[category] = pd.to_numeric(
                    category_data[category], errors="coerce"
                )

            # 移除缺失值和无穷大值
            category_data = category_data[category_data[category].notna()]
            category_data = category_data[np.isfinite(category_data[category])]

            if category_data.empty:
                self.logger.warning(f"类别 '{category}' 没有有效数据")
                continue

            # 按行政班分组计算统计指标
            class_stats = (
                category_data.groupby(class_col)[category]
                .agg(["mean", "std", "min", "max", "count"])
                .round(2)
            )

            # 计算排名（按均值降序）
            class_stats["均值排名"] = (
                class_stats["mean"].rank(ascending=False, method="min").astype(int)
            )

            # 计算离均率（使用清洗后的数据计算整体均值）
            overall_mean = category_data[category].mean()
            if (
                overall_mean != 0
                and pd.notna(overall_mean)
                and np.isfinite(overall_mean)
            ):
                class_stats["离均率"] = (
                    (class_stats["mean"] - overall_mean) / overall_mean * 100
                ).round(2)
            else:
                class_stats["离均率"] = 0.0

            # 重命名列
            class_stats = class_stats.rename(
                columns={
                    "mean": "均值",
                    "std": "标准差",
                    "min": "最小值",
                    "max": "最大值",
                    "count": "样本数",
                }
            )

            # 重置索引，将行政班名作为列
            class_stats = class_stats.reset_index()
            class_stats = class_stats.rename(columns={class_col: "行政班"})

            # 添加类别列
            class_stats["类别"] = category

            # 调整列顺序
            class_stats = class_stats[
                [
                    "类别",
                    "行政班",
                    "均值",
                    "均值排名",
                    "离均率",
                    "标准差",
                    "最大值",
                    "最小值",
                    "样本数",
                ]
            ]

            results.append(class_stats)

        if results:
            final_df = pd.concat(results, ignore_index=True)

            # 保存到数据库
            if self.db and self.raw_data_id and not final_df.empty:
                try:
                    # 为每个类别保存统计结果
                    for category in categories:
                        category_data = final_df[final_df["类别"] == category].to_dict(
                            "records"
                        )
                        if category_data:
                            self.db.store_cascade_statistics(
                                raw_data_id=self.raw_data_id,
                                analysis_level="county",
                                county_filter=None,
                                category=category,
                                metric_type="basic_statistics",
                                statistics={
                                    "data": category_data,
                                    "summary": final_df.describe().to_dict(),
                                },
                            )

                    self.logger.info("区县统计结果已保存到数据库")
                except Exception as e:
                    self.logger.error(f"保存区县统计结果到数据库失败: {e}")

            return final_df
        else:
            return pd.DataFrame()

    def calculate_subject_combination_statistics(
        self,
        county: str = None,
        school: str = None,
        categories: List[str] = None,
    ) -> pd.DataFrame:
        """
        计算选科组合统计数据

        Args:
            county: 区县名称，如果为None则计算所有区县
            school: 学校名称，如果为None则计算所有学校
            categories: 类别列表

        Returns:
            DataFrame: 选科组合统计数据
        """
        if not categories:
            return pd.DataFrame()

        # 过滤数据
        filtered_data = self.data.copy()

        if county and "county" in self.admin_columns:
            county_col = self.admin_columns["county"]
            filtered_data = filtered_data[filtered_data[county_col] == county]

        if school and "school" in self.admin_columns:
            school_col = self.admin_columns["school"]
            filtered_data = filtered_data[filtered_data[school_col] == school]

        if filtered_data.empty:
            self.logger.warning("过滤后数据为空")
            return pd.DataFrame()

        # 检查数据中是否有"选科组合"字段
        if "选科组合" in filtered_data.columns:
            # 直接使用已有的选科组合字段
            combination_data = filtered_data.copy()

            # 处理空值：将空值替换为"未确定"
            combination_data["选科组合"] = combination_data["选科组合"].fillna("未确定")
            combination_data["选科组合"] = combination_data["选科组合"].replace(
                "", "未确定"
            )

            self.logger.info(
                f"使用已有选科组合字段，发现 {len(combination_data)} 条记录"
            )

        else:
            # 如果没有选科组合字段，则通过成绩计算
            self.logger.info("未发现选科组合字段，通过成绩计算选科组合")
            combination_data = filtered_data.copy()
            combination_data["选科组合"] = combination_data.apply(
                self.determine_subject_combination, axis=1
            )

        if combination_data.empty:
            self.logger.warning("没有找到有效的选科组合数据")
            return pd.DataFrame()

        results = []

        for category in categories:
            if category not in self.data.columns:
                self.logger.warning(f"类别 '{category}' 不存在于数据中")
                continue

            # 数据类型验证和清洗
            category_data = combination_data[["选科组合", category]].copy()

            # 确保选科组合列存在
            if "选科组合" not in category_data.columns:
                self.logger.warning("选科组合列不存在")
                continue
            if not pd.api.types.is_numeric_dtype(category_data[category]):
                category_data[category] = pd.to_numeric(
                    category_data[category], errors="coerce"
                )

            # 移除缺失值和无穷大值
            category_data = category_data[category_data[category].notna()]
            category_data = category_data[np.isfinite(category_data[category])]

            if category_data.empty:
                self.logger.warning(f"类别 '{category}' 没有有效数据")
                continue

            # 按选科组合分组计算统计指标
            combination_stats = (
                category_data.groupby("选科组合")[category]
                .agg(["mean", "std", "min", "max", "count"])
                .round(2)
            )

            # 计算排名（按均值降序）
            combination_stats["均值排名"] = (
                combination_stats["mean"]
                .rank(ascending=False, method="min")
                .astype(int)
            )

            # 计算离均率
            overall_mean = category_data[category].mean()
            if (
                overall_mean != 0
                and pd.notna(overall_mean)
                and np.isfinite(overall_mean)
            ):
                combination_stats["离均率"] = (
                    (combination_stats["mean"] - overall_mean) / overall_mean * 100
                ).round(2)
            else:
                combination_stats["离均率"] = 0.0

            # 计算选科比例
            total_students = len(combination_data)
            combination_stats["选科人数"] = combination_stats["count"]
            combination_stats["选科比例(%)"] = (
                combination_stats["count"] / total_students * 100
            ).round(2)

            # 重命名列
            combination_stats = combination_stats.rename(
                columns={
                    "mean": "均值",
                    "std": "标准差",
                    "min": "最小值",
                    "max": "最大值",
                    "count": "样本数",
                }
            )

            # 重置索引，将选科组合作为列
            combination_stats = combination_stats.reset_index()

            # 添加类别列
            combination_stats["类别"] = category

            # 调整列顺序
            combination_stats = combination_stats[
                [
                    "类别",
                    "选科组合",
                    "选科人数",
                    "选科比例(%)",
                    "均值",
                    "均值排名",
                    "离均率",
                    "标准差",
                    "最大值",
                    "最小值",
                    "样本数",
                ]
            ]

            results.append(combination_stats)

        if results:
            final_df = pd.concat(results, ignore_index=True)

            # 保存到数据库
            if self.db and self.raw_data_id and not final_df.empty:
                try:
                    # 为每个类别保存统计结果
                    for category in categories:
                        category_data = final_df[final_df["类别"] == category].to_dict(
                            "records"
                        )
                        if category_data:
                            self.db.store_cascade_statistics(
                                raw_data_id=self.raw_data_id,
                                analysis_level="county",
                                county_filter=None,
                                category=category,
                                metric_type="basic_statistics",
                                statistics={
                                    "data": category_data,
                                    "summary": final_df.describe().to_dict(),
                                },
                            )

                    self.logger.info("区县统计结果已保存到数据库")
                except Exception as e:
                    self.logger.error(f"保存区县统计结果到数据库失败: {e}")

            return final_df
        else:
            return pd.DataFrame()

    def get_county_options(self) -> List[Dict[str, str]]:
        """获取区县选项"""
        if "county" not in self.admin_columns:
            return []

        county_col = self.admin_columns["county"]
        counties = sorted(self.data[county_col].dropna().unique())

        return [{"label": str(county), "value": str(county)} for county in counties]

    def get_school_options(self, county: str = None) -> List[Dict[str, str]]:
        """获取学校选项"""
        if "school" not in self.admin_columns:
            return []

        school_col = self.admin_columns["school"]
        filtered_data = self.data.copy()

        if county and "county" in self.admin_columns:
            county_col = self.admin_columns["county"]
            filtered_data = filtered_data[filtered_data[county_col] == county]

        schools = sorted(filtered_data[school_col].dropna().unique())
        return [{"label": str(school), "value": str(school)} for school in schools]

    def get_class_options(
        self, school: str = None, county: str = None
    ) -> List[Dict[str, str]]:
        """获取行政班选项"""
        if "class" not in self.admin_columns:
            return []

        class_col = self.admin_columns["class"]
        filtered_data = self.data.copy()

        if county and "county" in self.admin_columns:
            county_col = self.admin_columns["county"]
            filtered_data = filtered_data[filtered_data[county_col] == county]

        if school and "school" in self.admin_columns:
            school_col = self.admin_columns["school"]
            filtered_data = filtered_data[filtered_data[school_col] == school]

        classes = sorted(filtered_data[class_col].dropna().unique())
        return [{"label": str(cls), "value": str(cls)} for cls in classes]

    def get_category_options(self) -> List[Dict[str, str]]:
        """获取类别选项"""
        return [
            {"label": category, "value": category}
            for category in self.available_categories
        ]


def create_cascade_control_panel():
    """创建三级联动统计控制面板"""
    return dbc.Card(
        [
            dbc.CardHeader("📊 三级联动统计"),
            dbc.CardBody(
                [
                    # 数据状态调试信息
                    html.Div(id="cascade_data_status_debug", className="mb-3"),
                    # 区县选择
                    dbc.Label("选择区县：", className="form-label"),
                    dcc.Dropdown(
                        id="cascade_county_dropdown",
                        placeholder="请选择区县（可选）",
                        multi=False,
                        className="mb-3",
                    ),
                    # 学校选择
                    dbc.Label("选择学校：", className="form-label"),
                    dcc.Dropdown(
                        id="cascade_school_dropdown",
                        placeholder="请选择学校（可选）",
                        multi=False,
                        className="mb-3",
                    ),
                    # 行政班选择
                    dbc.Label("选择行政班：", className="form-label"),
                    dcc.Dropdown(
                        id="cascade_class_dropdown",
                        placeholder="请选择行政班（可选）",
                        multi=False,
                        className="mb-3",
                    ),
                    html.Hr(),
                    # 类别选择
                    dbc.Label("选择统计类别：", className="form-label"),
                    dcc.Dropdown(
                        id="cascade_category_dropdown",
                        placeholder="请选择要统计的类别（支持多选）",
                        multi=True,
                        className="mb-3",
                    ),
                    # 分析按钮
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "生成区县统计表",
                                        id="generate_county_stats_btn",
                                        color="warning",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "生成学校统计表",
                                        id="generate_school_stats_btn",
                                        color="primary",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "生成班级统计表",
                                        id="generate_class_stats_btn",
                                        color="success",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "生成选科统计表",
                                        id="generate_combination_stats_btn",
                                        color="info",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=3,
                            ),
                        ]
                    ),
                    html.Hr(),
                    # 快速选择预设
                    dbc.Label("快速选择：", className="form-label"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "主要科目",
                                        id="select_main_subjects_btn",
                                        color="outline-primary",
                                        size="sm",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "新高考总分",
                                        id="select_total_scores_btn",
                                        color="outline-success",
                                        size="sm",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=6,
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "理科科目",
                                        id="select_science_subjects_btn",
                                        color="outline-info",
                                        size="sm",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "文科科目",
                                        id="select_arts_subjects_btn",
                                        color="outline-warning",
                                        size="sm",
                                        className="w-100 mb-2",
                                    )
                                ],
                                width=6,
                            ),
                        ]
                    ),
                    # 清除选择按钮
                    dbc.Button(
                        "清除所有选择",
                        id="clear_cascade_selection_btn",
                        color="outline-danger",
                        size="sm",
                        className="w-100 mt-2",
                    ),
                ]
            ),
        ],
        className="mb-4",
    )


def create_cascade_results_panel():
    """创建三级联动统计结果面板"""
    return dbc.Card(
        [
            dbc.CardHeader("📈 统计结果"),
            dbc.CardBody(
                [
                    # 区县统计表格
                    html.Div(
                        [
                            html.H5("区县统计表", className="mb-3"),
                            html.Div(id="county_stats_table_container"),
                        ],
                        className="mb-4",
                    ),
                    html.Hr(),
                    # 学校统计表格
                    html.Div(
                        [
                            html.H5("学校统计表", className="mb-3"),
                            html.Div(id="school_stats_table_container"),
                        ],
                        className="mb-4",
                    ),
                    html.Hr(),
                    # 班级统计表格
                    html.Div(
                        [
                            html.H5("班级统计表", className="mb-3"),
                            html.Div(id="class_stats_table_container"),
                        ],
                        className="mb-4",
                    ),
                    html.Hr(),
                    # 选科统计表格
                    html.Div(
                        [
                            html.H5("选科统计表", className="mb-3"),
                            html.Div(id="combination_stats_table_container"),
                        ]
                    ),
                ]
            ),
        ]
    )


def register_cascade_callbacks(app):
    """注册三级联动统计回调函数"""

    # 添加数据状态调试信息回调
    @app.callback(
        Output("cascade_data_status_debug", "children"),
        [Input("data_store", "data")],
    )
    def update_cascade_data_status_debug(data_json):
        """更新数据状态调试信息"""
        if data_json is None:
            return dbc.Alert("未上传数据", color="warning", className="small")

        try:
            from io import StringIO

            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            # 创建状态信息
            status_items = [
                f"📊 数据行数: {len(df)}",
                f"📋 数据列数: {len(df.columns)}",
                f"🏢 区县列: {analyzer.admin_columns.get('county', '未找到')}",
                f"🏫 学校列: {analyzer.admin_columns.get('school', '未找到')}",
                f"👥 班级列: {analyzer.admin_columns.get('class', '未找到')}",
            ]

            if analyzer.admin_columns:
                return dbc.Alert(
                    [
                        html.H6("✅ 数据状态正常", className="alert-heading"),
                        html.Br(),
                        *[html.P(item, className="mb-1") for item in status_items],
                    ],
                    color="success",
                    className="small",
                )
            else:
                return dbc.Alert(
                    [
                        html.H6("⚠️ 可能缺少行政信息列", className="alert-heading"),
                        html.Br(),
                        *[html.P(item, className="mb-1") for item in status_items],
                    ],
                    color="info",
                    className="small",
                )

        except Exception as e:
            return dbc.Alert(
                f"❌ 数据解析错误: {str(e)}", color="danger", className="small"
            )

    @app.callback(
        [
            Output("cascade_county_dropdown", "options"),
            Output("cascade_school_dropdown", "options"),
            Output("cascade_class_dropdown", "options"),
            Output("cascade_category_dropdown", "options"),
        ],
        [Input("data_store", "data")],
    )
    def update_cascade_dropdowns(data_json):
        """更新三级联动下拉选项"""
        if data_json is None:
            return [], [], [], []

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            county_options = analyzer.get_county_options()
            school_options = analyzer.get_school_options()
            class_options = analyzer.get_class_options()
            category_options = analyzer.get_category_options()

            return (
                county_options,
                school_options,
                class_options,
                category_options,
            )

        except Exception as e:
            logger.error(f"更新三级联动下拉选项失败: {e}")
            return [], [], [], []

    @app.callback(
        [
            Output("cascade_school_dropdown", "options", allow_duplicate=True),
            Output("cascade_school_dropdown", "value", allow_duplicate=True),
        ],
        [Input("cascade_county_dropdown", "value")],
        [State("data_store", "data")],
        prevent_initial_call=True,
    )
    def update_school_options(selected_county, data_json):
        """根据选择的区县更新学校选项"""
        if data_json is None:
            return [], None

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            school_options = analyzer.get_school_options(selected_county)
            return school_options, None  # 清空学校选择

        except Exception as e:
            logger.error(f"更新学校选项失败: {e}")
            return [], None

    @app.callback(
        [
            Output("cascade_class_dropdown", "options", allow_duplicate=True),
            Output("cascade_class_dropdown", "value", allow_duplicate=True),
        ],
        [
            Input("cascade_county_dropdown", "value"),
            Input("cascade_school_dropdown", "value"),
        ],
        [State("data_store", "data")],
        prevent_initial_call=True,
    )
    def update_class_options(selected_county, selected_school, data_json):
        """根据选择的区县和学校更新行政班选项"""
        if data_json is None:
            return [], None

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            class_options = analyzer.get_class_options(selected_school, selected_county)
            return class_options, None  # 清空行政班选择

        except Exception as e:
            logger.error(f"更新行政班选项失败: {e}")
            return [], None

    @app.callback(
        Output("cascade_category_dropdown", "value", allow_duplicate=True),
        [Input("select_main_subjects_btn", "n_clicks")],
        [State("cascade_category_dropdown", "options")],
        prevent_initial_call=True,
    )
    def select_main_subjects(n_clicks, category_options):
        """选择主要科目"""
        if n_clicks and category_options:
            main_subjects = ["语文", "数学", "英语", "日语"]
            # 只选择实际存在的类别
            available_main = [
                opt["value"]
                for opt in category_options
                if any(subject in opt["value"] for subject in main_subjects)
            ]
            return available_main if available_main else None
        return None

    @app.callback(
        Output("cascade_category_dropdown", "value", allow_duplicate=True),
        [Input("select_total_scores_btn", "n_clicks")],
        [State("cascade_category_dropdown", "options")],
        prevent_initial_call=True,
    )
    def select_total_scores(n_clicks, category_options):
        """选择新高考总分相关"""
        if n_clicks and category_options:
            total_scores = [
                "新高考总分",
                "新高考语数英总分",
                "新高考3+1总分",
                "新高考原始总分",
            ]
            # 只选择实际存在的类别
            available_total = [
                opt["value"]
                for opt in category_options
                if any(total in opt["value"] for total in total_scores)
            ]
            return available_total if available_total else None
        return None

    @app.callback(
        Output("cascade_category_dropdown", "value", allow_duplicate=True),
        [Input("select_science_subjects_btn", "n_clicks")],
        [State("cascade_category_dropdown", "options")],
        prevent_initial_call=True,
    )
    def select_science_subjects(n_clicks, category_options):
        """选择理科科目"""
        if n_clicks and category_options:
            science_subjects = ["物理", "化学", "生物"]
            # 只选择实际存在的类别
            available_science = [
                opt["value"]
                for opt in category_options
                if any(science in opt["value"] for science in science_subjects)
            ]
            return available_science if available_science else None
        return None

    @app.callback(
        Output("cascade_category_dropdown", "value", allow_duplicate=True),
        [Input("select_arts_subjects_btn", "n_clicks")],
        [State("cascade_category_dropdown", "options")],
        prevent_initial_call=True,
    )
    def select_arts_subjects(n_clicks, category_options):
        """选择文科科目"""
        if n_clicks and category_options:
            arts_subjects = ["政治", "地理", "历史"]
            # 只选择实际存在的类别
            available_arts = [
                opt["value"]
                for opt in category_options
                if any(arts in opt["value"] for arts in arts_subjects)
            ]
            return available_arts if available_arts else None
        return None

    @app.callback(
        [
            Output("cascade_county_dropdown", "value", allow_duplicate=True),
            Output("cascade_school_dropdown", "value", allow_duplicate=True),
            Output("cascade_class_dropdown", "value", allow_duplicate=True),
            Output("cascade_category_dropdown", "value", allow_duplicate=True),
        ],
        [Input("clear_cascade_selection_btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def clear_all_selections(n_clicks):
        """清除所有选择"""
        if n_clicks:
            return None, None, None, []
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    @app.callback(
        Output("county_stats_table_container", "children"),
        [Input("generate_county_stats_btn", "n_clicks")],
        [
            State("data_store", "data"),
            State("cascade_category_dropdown", "value"),
        ],
    )
    def generate_county_statistics(n_clicks, data_json, selected_categories):
        """生成区县统计表格"""
        if n_clicks is None or data_json is None or not selected_categories:
            return html.Div(
                "请选择要统计的类别并点击生成按钮",
                className="text-muted text-center",
            )

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            # 计算区县统计数据
            county_stats = analyzer.calculate_county_statistics(selected_categories)

            if county_stats.empty:
                return html.Div(
                    "未生成统计数据，请检查选择条件",
                    className="text-warning text-center",
                )

            # 创建表格标题
            if len(selected_categories) == 1:
                title = f"各县区{selected_categories[0]}的均分及排名情况"
            else:
                title = "各县区多个类别的均分及排名情况"

            # 创建数据表格
            table = dash_table.DataTable(
                data=county_stats.to_dict("records"),
                columns=[{"name": col, "id": col} for col in county_stats.columns],
                style_cell={
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "14px",
                },
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)",
                    },
                    {
                        "if": {"filter_query": "{离均率} > 0"},
                        "color": "green",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {"filter_query": "{离均率} < 0"},
                        "color": "red",
                        "fontWeight": "bold",
                    },
                ],
                page_size=20,
                sort_action="native",
                filter_action="native",
            )

            return html.Div(
                [
                    html.H5(title, className="text-primary mb-3"),
                    table,
                    html.Div(
                        [
                            html.Small(
                                f"共统计 {len(county_stats)} 条记录",
                                className="text-muted",
                            )
                        ],
                        className="mt-2",
                    ),
                ]
            )

        except Exception as e:
            logger.error(f"生成区县统计表格失败: {e}")
            return html.Div(
                f"生成统计表格时出错: {str(e)}",
                className="text-danger text-center",
            )

    @app.callback(
        Output("school_stats_table_container", "children"),
        [Input("generate_school_stats_btn", "n_clicks")],
        [
            State("data_store", "data"),
            State("cascade_county_dropdown", "value"),
            State("cascade_category_dropdown", "value"),
        ],
    )
    def generate_school_statistics(
        n_clicks, data_json, selected_county, selected_categories
    ):
        """生成学校统计表格"""
        if n_clicks is None or data_json is None or not selected_categories:
            return html.Div(
                "请选择要统计的类别并点击生成按钮",
                className="text-muted text-center",
            )

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            # 计算学校统计数据
            school_stats = analyzer.calculate_school_statistics(
                selected_county, selected_categories
            )

            if school_stats.empty:
                return html.Div(
                    "未生成统计数据，请检查选择条件",
                    className="text-warning text-center",
                )

            # 创建表格标题
            if selected_county:
                title = f"{selected_county}各学校"
            else:
                title = "全区县各学校"

            if len(selected_categories) == 1:
                title += f"{selected_categories[0]}的均分及排名情况"
            else:
                title += "多个类别的均分及排名情况"

            # 创建数据表格
            table = dash_table.DataTable(
                data=school_stats.to_dict("records"),
                columns=[{"name": col, "id": col} for col in school_stats.columns],
                style_cell={
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "14px",
                },
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)",
                    },
                    {
                        "if": {"filter_query": "{离均率} > 0"},
                        "color": "green",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {"filter_query": "{离均率} < 0"},
                        "color": "red",
                        "fontWeight": "bold",
                    },
                ],
                page_size=20,
                sort_action="native",
                filter_action="native",
            )

            return html.Div(
                [
                    html.H5(title, className="text-primary mb-3"),
                    table,
                    html.Div(
                        [
                            html.Small(
                                f"共统计 {len(school_stats)} 条记录",
                                className="text-muted",
                            )
                        ],
                        className="mt-2",
                    ),
                ]
            )

        except Exception as e:
            logger.error(f"生成学校统计表格失败: {e}")
            return html.Div(
                f"生成统计表格时出错: {str(e)}",
                className="text-danger text-center",
            )

    @app.callback(
        Output("class_stats_table_container", "children"),
        [Input("generate_class_stats_btn", "n_clicks")],
        [
            State("data_store", "data"),
            State("cascade_school_dropdown", "value"),
            State("cascade_category_dropdown", "value"),
        ],
    )
    def generate_class_statistics(
        n_clicks, data_json, selected_school, selected_categories
    ):
        """生成班级统计表格"""
        if n_clicks is None or data_json is None or not selected_categories:
            return html.Div(
                "请选择要统计的类别并点击生成按钮",
                className="text-muted text-center",
            )

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            # 计算班级统计数据
            class_stats = analyzer.calculate_class_statistics(
                selected_school, selected_categories
            )

            if class_stats.empty:
                return html.Div(
                    "未生成统计数据，请检查选择条件",
                    className="text-warning text-center",
                )

            # 创建表格标题
            if selected_school:
                title = f"{selected_school}各班"
            else:
                title = "所有学校各班"

            if len(selected_categories) == 1:
                title += f"{selected_categories[0]}的均分及排名情况"
            else:
                title += "多个类别的均分及排名情况"

            # 创建数据表格
            table = dash_table.DataTable(
                data=class_stats.to_dict("records"),
                columns=[{"name": col, "id": col} for col in class_stats.columns],
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "14px",
                },
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)",
                    },
                    {
                        "if": {"filter_query": "{离均率} > 0"},
                        "color": "green",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {"filter_query": "{离均率} < 0"},
                        "color": "red",
                        "fontWeight": "bold",
                    },
                ],
                page_size=20,
                sort_action="native",
                filter_action="native",
            )

            return html.Div(
                [
                    html.H5(title, className="text-primary mb-3"),
                    table,
                    html.Div(
                        [
                            html.Small(
                                f"共统计 {len(class_stats)} 条记录",
                                className="text-muted",
                            )
                        ],
                        className="mt-2",
                    ),
                ]
            )

        except Exception as e:
            logger.error(f"生成班级统计表格失败: {e}")
            return html.Div(
                f"生成统计表格时出错: {str(e)}",
                className="text-danger text-center",
            )

    @app.callback(
        Output("combination_stats_table_container", "children"),
        [Input("generate_combination_stats_btn", "n_clicks")],
        [
            State("data_store", "data"),
            State("cascade_county_dropdown", "value"),
            State("cascade_school_dropdown", "value"),
            State("cascade_category_dropdown", "value"),
        ],
    )
    def generate_combination_statistics(
        n_clicks,
        data_json,
        selected_county,
        selected_school,
        selected_categories,
    ):
        """生成选科统计表格"""
        if n_clicks is None or data_json is None or not selected_categories:
            return html.Div(
                "请选择要统计的类别并点击生成按钮",
                className="text-muted text-center",
            )

        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = CascadeStatisticsAnalyzer(df)

            # 计算选科统计数据
            combination_stats = analyzer.calculate_subject_combination_statistics(
                selected_county, selected_school, selected_categories
            )

            if combination_stats.empty:
                return html.Div(
                    "未生成统计数据，请检查选择条件或数据中是否包含选科信息",
                    className="text-warning text-center",
                )

            # 创建表格标题
            title_parts = []
            if selected_county:
                title_parts.append(f"{selected_county}")
            if selected_school:
                title_parts.append(f"{selected_school}")
            if not title_parts:
                title_parts.append("全区县")

            if len(selected_categories) == 1:
                title_parts.append(f"{selected_categories[0]}")
            else:
                title_parts.append("多个类别")

            title_parts.append("选科统计")

            title = "".join(title_parts)

            # 创建数据表格
            table = dash_table.DataTable(
                data=combination_stats.to_dict("records"),
                columns=[{"name": col, "id": col} for col in combination_stats.columns],
                style_cell={
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "14px",
                },
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)",
                    },
                    {
                        "if": {"filter_query": "{离均率} > 0"},
                        "color": "green",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {"filter_query": "{离均率} < 0"},
                        "color": "red",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {"column_id": "选科组合"},
                        "fontWeight": "bold",
                        "color": "blue",
                    },
                    {"if": {"column_id": "选科比例(%)"}, "fontWeight": "bold"},
                ],
                page_size=20,
                sort_action="native",
                filter_action="native",
            )

            # 添加统计摘要 (汇总值未被直接使用于当前返回结构)

            return html.Div(
                [
                    html.H5(title, className="text-primary mb-3"),
                    table,
                    html.Div(
                        [
                            html.Small(
                                f"共统计 {len(combination_stats)} 条记录",
                                className="text-muted",
                            )
                        ],
                        className="mt-2",
                    ),
                ]
            )

        except Exception as e:
            logger.error(f"生成选科统计表格失败: {e}")
            return html.Div(
                f"生成统计表格时出错: {str(e)}",
                className="text-danger text-center",
            )
