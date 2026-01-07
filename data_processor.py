#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理模块
基于Pandas和NumPy实现数据清洗、转换和计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging


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


class DataProcessor:
    """数据处理器类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data = None
        self.original_data = None

    def load_data(self, file_path: str) -> pd.DataFrame:
        """加载Excel或CSV文件"""
        try:
            if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                self.data = pd.read_excel(file_path)
            elif file_path.endswith(".csv"):
                # 尝试多种编码格式，优先UTF-8，然后尝试GBK
                encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig"]
                for encoding in encodings:
                    try:
                        self.data = pd.read_csv(file_path, encoding=encoding)
                        self.logger.info(f"使用 {encoding} 编码成功加载CSV文件")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("无法使用常见编码格式读取CSV文件，请检查文件编码")
            else:
                raise ValueError("不支持的文件格式")

            self.original_data = self.data.copy()
            self.logger.info(f"成功加载数据，形状: {self.data.shape}")
            return self.data

        except Exception as e:
            self.logger.error(f"数据加载失败: {str(e)}")
            raise

    def clean_data(
        self,
        remove_duplicates: bool = True,
        handle_missing: str = "drop",
        outlier_method: str = "iqr",
    ) -> pd.DataFrame:
        """数据清洗"""
        if self.data is None:
            raise ValueError("请先加载数据")

        df = self.data.copy()

        # 转换文本数字为数字类型
        df = self._convert_text_to_numbers(df)

        # 删除重复行
        if remove_duplicates:
            before_count = len(df)
            df = df.drop_duplicates()
            after_count = len(df)
            self.logger.info(f"删除重复行: {before_count - after_count} 行")

        # 处理缺失值
        if handle_missing == "drop":
            df = df.dropna()
        elif handle_missing == "fill_mean":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        elif handle_missing == "fill_median":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
        elif handle_missing == "fill_mode":
            for col in df.columns:
                df[col] = df[col].fillna(
                    df[col].mode().iloc[0] if not df[col].mode().empty else 0
                )
        elif handle_missing == "keep":
            # 不处理缺失值，保持原样
            pass

        # 处理异常值
        if outlier_method == "iqr":
            df = self._remove_outliers_iqr(df)
        elif outlier_method == "zscore":
            df = self._remove_outliers_zscore(df)

        self.data = df
        self.logger.info(f"数据清洗完成，最终形状: {df.shape}")
        return df

    def _convert_text_to_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """将文本数字转换为浮点数格式（如生物赋分的82.0格式）"""
        converted_cols = []

        for col in df.columns:
            # 跳过已经是数字类型的列
            if pd.api.types.is_numeric_dtype(df[col]):
                # 确保现有数字列也是浮点数格式
                if pd.api.types.is_integer_dtype(df[col]):
                    df[col] = df[col].astype(float)
                continue

            # 尝试转换为浮点数类型
            try:
                # 先尝试直接转换为浮点数
                converted = pd.to_numeric(df[col], errors="coerce", downcast="float")

                # 如果转换后有有效值且不是全为NaN，则应用转换
                if not converted.isna().all():
                    df[col] = converted
                    converted_cols.append(col)
                    self.logger.info(f"列 '{col}' 已转换为浮点数格式")
                else:
                    # 如果全为NaN，尝试去除空白字符后再转换
                    stripped = df[col].astype(str).str.strip()
                    converted = pd.to_numeric(
                        stripped, errors="coerce", downcast="float"
                    )

                    if not converted.isna().all():
                        df[col] = converted
                        converted_cols.append(col)
                        self.logger.info(f"列 '{col}' 去除空白字符后已转换为浮点数格式")

            except Exception as e:
                self.logger.warning(f"列 '{col}' 转换失败: {str(e)}")
                continue

        if converted_cols:
            self.logger.info(
                f"成功转换 {len(converted_cols)} 列为浮点数格式: {converted_cols}"
            )

        return df

    def _remove_outliers_iqr(self, df: pd.DataFrame) -> pd.DataFrame:
        """使用IQR方法删除异常值"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            before_count = len(df)
            df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
            after_count = len(df)

            if before_count != after_count:
                self.logger.info(
                    f"列 {col} 删除异常值: {before_count - after_count} 行"
                )

        return df

    def _remove_outliers_zscore(
        self, df: pd.DataFrame, threshold: float = 3.0
    ) -> pd.DataFrame:
        """使用Z-score方法删除异常值"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            # 安全计算Z-score，避免除零错误
            col_mean = safe_mean(df[col])
            col_std = safe_std(df[col])

            if col_std == 0:
                # 如果标准差为0，跳过此列
                continue

            z_scores = np.abs((df[col] - col_mean) / col_std)
            before_count = len(df)
            df = df[z_scores < threshold]
            after_count = len(df)

            if before_count != after_count:
                self.logger.info(
                    f"列 {col} 删除异常值: {before_count - after_count} 行"
                )

        return df

    def standardize_data(
        self, method: str = "zscore", columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """数据标准化"""
        if self.data is None:
            raise ValueError("请先加载数据")

        df = self.data.copy()
        numeric_cols = columns or df.select_dtypes(include=[np.number]).columns

        if method == "zscore":
            for col in numeric_cols:
                df[col] = (df[col] - df[col].mean()) / df[col].std()
        elif method == "minmax":
            for col in numeric_cols:
                df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        elif method == "robust":
            for col in numeric_cols:
                median = df[col].median()
                iqr = df[col].quantile(0.75) - df[col].quantile(0.25)
                df[col] = (df[col] - median) / iqr

        self.logger.info(f"数据标准化完成，方法: {method}")
        return df

    def create_features(self, feature_config: Dict[str, Any]) -> pd.DataFrame:
        """特征工程"""
        if self.data is None:
            raise ValueError("请先加载数据")

        df = self.data.copy()

        # 创建成绩等级特征
        if "grade_levels" in feature_config and "score_column" in feature_config:
            score_col = feature_config["score_column"]
            levels = feature_config["grade_levels"]

            df["grade_level"] = pd.cut(
                df[score_col],
                bins=[-np.inf] + levels + [np.inf],
                labels=["F", "D", "C", "B", "A"],
            )

        # 创建排名特征
        if "ranking" in feature_config and "score_column" in feature_config:
            score_col = feature_config["score_column"]
            if "group_column" in feature_config:
                group_col = feature_config["group_column"]
                df["rank_in_group"] = df.groupby(group_col)[score_col].rank(
                    ascending=False
                )
            else:
                df["overall_rank"] = df[score_col].rank(ascending=False)

        # 创建统计特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if f"{col}_percentile" not in df.columns:
                df[f"{col}_percentile"] = df[col].rank(pct=True) * 100

        self.data = df
        self.logger.info("特征工程完成")
        return df

    def calculate_total_score(
        self, df: pd.DataFrame = None, exam_mode: str = "new_gaokao"
    ) -> pd.DataFrame:
        """计算学生总分

        Args:
            df: 数据框，如果为None则使用self.data
            exam_mode: 考试模式，'new_gaokao'为新高考3+1+2模式，'traditional'为传统模式

        Returns:
            pd.DataFrame: 包含总分列的数据框
        """
        if df is None:
            df = self.data.copy()
        else:
            df = df.copy()

        if df is None or df.empty:
            raise ValueError("数据为空，无法计算总分")

        # 定义科目列关键词
        subject_keywords = [
            "语文",
            "数学",
            "英语",
            "物理",
            "化学",
            "生物",
            "政治",
            "历史",
            "地理",
        ]

        # 找到所有科目列
        subject_columns = []
        for col in df.columns:
            if any(keyword in str(col) for keyword in subject_keywords):
                subject_columns.append(col)

        if not subject_columns:
            self.logger.warning("未找到科目列，无法计算总分")
            return df

        self.logger.info(f"找到科目列: {subject_columns}")

        # 检查科目列是否为数值类型
        numeric_subject_columns = []
        for col in subject_columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                numeric_subject_columns.append(col)
            else:
                # 尝试转换为数值类型
                try:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    if not df[col].isna().all():
                        numeric_subject_columns.append(col)
                        self.logger.info(f"列 '{col}' 已转换为数值类型")
                except Exception as e:
                    self.logger.warning(f"列 '{col}' 无法转换为数值类型，跳过: {e}")

        if not numeric_subject_columns:
            self.logger.error("没有找到可用的数值类型科目列，无法计算总分")
            return df

        if exam_mode == "new_gaokao":
            # 新高考"3+1+2"模式总分计算
            total_scores = []
            for idx, row in df.iterrows():
                score = 0
                valid_count = 0

                # 必考科目：语文、数学、外语（各150分）
                for subject in ["语文", "数学", "英语"]:
                    if any(subject in col for col in numeric_subject_columns):
                        col_name = next(
                            col for col in numeric_subject_columns if subject in col
                        )
                        if pd.notna(row[col_name]):
                            score += row[col_name]
                            valid_count += 1

                # 第一选择科目：物理或历史（各100分）
                first_choice = None
                for subject in ["物理", "历史"]:
                    if any(subject in col for col in numeric_subject_columns):
                        col_name = next(
                            col for col in numeric_subject_columns if subject in col
                        )
                        if pd.notna(row[col_name]):
                            if first_choice is None or row[col_name] > first_choice[1]:
                                first_choice = (col_name, row[col_name])

                if first_choice:
                    score += first_choice[1]
                    valid_count += 1

                # 第二选择科目：化学、生物、政治、地理中选2门（各100分）
                second_choices = []
                for subject in ["化学", "生物", "政治", "地理"]:
                    if any(subject in col for col in numeric_subject_columns):
                        col_name = next(
                            col for col in numeric_subject_columns if subject in col
                        )
                        if pd.notna(row[col_name]):
                            second_choices.append((col_name, row[col_name]))

                # 选择分数最高的2门
                second_choices.sort(key=lambda x: x[1], reverse=True)
                for col_name, col_score in second_choices[:2]:
                    score += col_score
                    valid_count += 1

                # 只有当有效科目数量足够时才计算总分
                if valid_count >= 6:  # 3门必考+1门首选+2门再选
                    total_scores.append(score)
                else:
                    total_scores.append(np.nan)

            df["新高考总分"] = total_scores
            self.logger.info("使用新高考3+1+2模式计算新高考总分")

        else:
            # 传统模式：所有科目相加
            df["新高考总分"] = df[numeric_subject_columns].sum(axis=1, skipna=False)
            self.logger.info("使用传统模式计算新高考总分")

        # 统计信息
        valid_total_scores = df["新高考总分"].notna().sum()
        self.logger.info(
            f"成功计算新高考总分，共 {valid_total_scores} 名学生的总分有效"
        )
        self.logger.info(
            f"新高考总分统计: 最小值={df['新高考总分'].min()}, 最大值={df['新高考总分'].max()}, 平均值={df['新高考总分'].mean():.2f}"
        )

        return df

    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据摘要信息"""
        if self.data is None:
            raise ValueError("请先加载数据")

        summary = {
            "shape": self.data.shape,
            "columns": list(self.data.columns),
            "dtypes": self.data.dtypes.to_dict(),
            "missing_values": self.data.isnull().sum().to_dict(),
            "numeric_summary": self.data.describe().to_dict(),
            "memory_usage": self.data.memory_usage(deep=True).sum(),
        }

        return summary

    def export_data(self, file_path: str, format: str = "csv"):
        """导出处理后的数据"""
        if self.data is None:
            raise ValueError("请先加载数据")

        try:
            if format.lower() == "csv":
                self.data.to_csv(file_path, index=False, encoding="utf-8")
            elif format.lower() == "excel":
                self.data.to_excel(file_path, index=False)
            else:
                raise ValueError("不支持的导出格式")

            self.logger.info(f"数据导出成功: {file_path}")

        except Exception as e:
            self.logger.error(f"数据导出失败: {str(e)}")
            raise
