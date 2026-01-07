#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版综合数据分析模块
实现全局数据集多维度统计分析、数据聚合、趋势分析、异常检测和可视化
支持大规模数据处理和高性能计算
整合版本：包含分析器、UI组件和回调函数
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
import logging
import importlib.util
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback_context
from io import StringIO
import warnings


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


warnings.filterwarnings("ignore")

# 数据库功能已移除
DATABASE_AVAILABLE = False

# 尝试检测可选依赖（不在此处导入具体符号以避免命名冲突）
SCIPY_AVAILABLE = importlib.util.find_spec("scipy") is not None
SKLEARN_AVAILABLE = importlib.util.find_spec("sklearn") is not None

# 设置日志
logger = logging.getLogger(__name__)


class ComprehensiveAnalyzer:
    """增强版综合数据分析器"""

    def __init__(
        self,
        data: pd.DataFrame,
        config: Optional[Dict] = None,
    ):
        self.data = data
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        self.raw_data_id = None

        # 数据库功能已移除
        self.db = None

        # 性能优化：数据类型优化
        self._optimize_dtypes()

        # 识别学科列
        self.subject_columns = self._detect_subject_columns()
        self.logger.info(f"检测到学科列: {self.subject_columns}")
        self.logger.info(
            f"数据列总数: {len(self.data.columns)}, 列名: {list(self.data.columns)}"
        )

        # 缓存机制已移除

    def _default_config(self) -> Dict:
        """默认配置参数"""
        return {
            # 统计参数
            "trend_window": 3,  # 趋势分析窗口
            "confidence_level": 0.95,  # 置信水平
            # 性能参数
            "chunk_size": 10000,  # 分块处理大小
            "use_parallel": True,  # 是否使用并行计算
            "cache_enabled": False,  # 是否启用缓存
            # 可视化参数
            "chart_colors": [
                "#1f77b4",
                "#ff7f0e",
                "#2ca02c",
                "#d62728",
                "#9467bd",
            ],
            "figure_height": 600,
            "figure_width": 1000,
        }

    def _optimize_dtypes(self):
        """优化数据类型以提高性能"""
        try:
            for col in self.data.columns:
                if self.data[col].dtype == "object":
                    # 尝试转换为category以节省内存
                    if len(self.data[col].unique()) / len(self.data) < 0.5:
                        self.data[col] = self.data[col].astype("category")
                elif self.data[col].dtype in ["int64", "float64"]:
                    # 对于数值列，尝试使用更小的数据类型
                    if self.data[col].dtype == "int64":
                        if self.data[col].min() >= 0 and self.data[col].max() <= 255:
                            self.data[col] = self.data[col].astype("uint8")
                        elif (
                            self.data[col].min() >= -128 and self.data[col].max() <= 127
                        ):
                            self.data[col] = self.data[col].astype("int8")
                        elif (
                            self.data[col].min() >= 0 and self.data[col].max() <= 65535
                        ):
                            self.data[col] = self.data[col].astype("uint16")
                        elif (
                            self.data[col].min() >= -32768
                            and self.data[col].max() <= 32767
                        ):
                            self.data[col] = self.data[col].astype("int16")
                    elif self.data[col].dtype == "float64":
                        self.data[col] = self.data[col].astype("float32")

            self.logger.info("数据类型优化完成")
        except Exception as e:
            self.logger.warning(f"数据类型优化失败: {e}")

    def _detect_subject_columns(self) -> List[str]:
        """动态检测科目列"""
        # 排除明显的非成绩列
        exclude_keywords = [
            "姓名",
            "学号",
            "考生号",
            "班级",
            "学校",
            "区县",
            "选科",
            "准考证号",
            "考生类型",
            "等级",
            "总分",
            "新高考总分",
            "排名",
            "成绩",
            "考试",
            "时间",
            "日期",
            "学期",
            "学年",
            "行政班",
        ]

        subject_columns = []
        for col in self.data.columns:
            if not any(keyword in str(col) for keyword in exclude_keywords):
                # 检查是否包含数字数据
                try:
                    if pd.api.types.is_numeric_dtype(self.data[col]):
                        valid_scores = self.data[col].dropna()
                        if len(valid_scores) > 0:
                            min_score = valid_scores.min()
                            max_score = valid_scores.max()
                            # 改进的分数范围检查：0-300分，至少30分以上
                            if 0 <= min_score and max_score <= 300 and max_score >= 30:
                                # 检查数据量（至少3个有效数据点，适应小数据集）
                                if len(valid_scores) >= 3:  # 至少3个有效数据点
                                    subject_columns.append(col)
                except Exception as e:
                    self.logger.warning(f"检查列 '{col}' 时出错: {e}")
                    continue

        return sorted(subject_columns)

    def get_administrative_columns(self) -> Dict[str, str]:
        """获取行政层级列名"""
        admin_columns = {}
        for col in self.data.columns:
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
                admin_columns["county"] = col
            # 扩展学校列的匹配规则
            elif any(
                keyword in col_str for keyword in ["学校", "中学", "小学", "school"]
            ):
                admin_columns["school"] = col
            # 扩展班级列的匹配规则
            elif any(
                keyword in col_str for keyword in ["行政班", "班级", "班", "class"]
            ):
                admin_columns["class"] = col

        # 添加调试信息
        self.logger.info(f"检测到的数据列: {list(self.data.columns)}")
        self.logger.info(f"识别的行政列: {admin_columns}")

        return admin_columns

    def get_cascade_options(
        self,
        level: str = None,
        selected_counties: List[str] = None,
        selected_schools: List[str] = None,
    ) -> Dict[str, List]:
        """获取三级联动选项"""
        admin_cols = self.get_administrative_columns()
        options = {"county": [], "school": [], "class": []}

        # 调试信息
        self.logger.info(f"数据列名: {list(self.data.columns)}")
        self.logger.info(f"行政列: {admin_cols}")
        self.logger.info(f"数据形状: {self.data.shape}")

        try:
            # 如果没有找到任何行政列，尝试从数据中智能推断
            if not admin_cols:
                self.logger.warning("未找到明显的行政列，尝试智能推断...")
                for col in self.data.columns:
                    col_data = self.data[col].dropna()

                    # 检查是否为区县列（唯一值较少，且包含县区名）
                    if len(col_data.unique()) <= 20 and len(col_data.unique()) >= 2:
                        unique_vals = [
                            str(v).lower() for v in col_data.unique() if pd.notna(v)
                        ]
                        if any(
                            keyword in val
                            for val in unique_vals
                            for keyword in ["县", "区", "district"]
                        ):
                            admin_cols["county"] = col
                            self.logger.info(f"推断区县列: {col}")
                            break

                    # 检查是否为学校列
                    if len(col_data.unique()) <= 100 and len(col_data.unique()) >= 2:
                        unique_vals = [
                            str(v).lower() for v in col_data.unique() if pd.notna(v)
                        ]
                        if any(
                            keyword in val
                            for val in unique_vals
                            for keyword in ["中学", "小学", "school"]
                        ):
                            admin_cols["school"] = col
                            self.logger.info(f"推断学校列: {col}")

                # 检查是否为班级列（通常包含数字）
                for col in self.data.columns:
                    if col not in admin_cols.values():
                        col_data = self.data[col].dropna()
                        if (
                            len(col_data.unique()) <= 200
                            and len(col_data.unique()) >= 5
                        ):
                            unique_vals = [
                                str(v) for v in col_data.unique() if pd.notna(v)
                            ]
                            # 如果包含"班"字或者数字+班的模式
                            if any(
                                "班" in val or any(char.isdigit() for char in val)
                                for val in unique_vals[:10]
                            ):
                                admin_cols["class"] = col
                                self.logger.info(f"推断班级列: {col}")
                                break

            # 获取区县选项
            if "county" in admin_cols:
                county_col = admin_cols["county"]
                counties_data = self.data[county_col].dropna()
                counties = sorted(
                    [str(c) for c in counties_data.unique() if str(c).strip()]
                )
                options["county"] = [
                    {"label": str(c), "value": str(c)} for c in counties
                ]
                self.logger.info(
                    f"找到区县选项: {len(options['county'])}个 - {counties[:5]}..."
                )  # 显示前5个
            else:
                self.logger.warning("未找到区县列，可能数据中不包含区县信息")

            # 获取学校选项
            if "school" in admin_cols:
                school_col = admin_cols["school"]
                if selected_counties and "county" in admin_cols and selected_counties:
                    county_col = admin_cols["county"]
                    # 确保选择的区县存在于数据中
                    valid_counties = [
                        c
                        for c in selected_counties
                        if c in self.data[county_col].values
                    ]
                    if valid_counties:
                        filtered_df = self.data[
                            self.data[county_col].isin(valid_counties)
                        ]
                        schools_data = filtered_df[school_col].dropna()
                    else:
                        schools_data = self.data[school_col].dropna()
                        self.logger.warning("选择的区县在数据中不存在，显示所有学校")
                else:
                    schools_data = self.data[school_col].dropna()

                schools = sorted(
                    [str(s) for s in schools_data.unique() if str(s).strip()]
                )
                options["school"] = [
                    {"label": str(s), "value": str(s)} for s in schools
                ]
                self.logger.info(f"找到学校选项: {len(options['school'])}个")
            else:
                self.logger.warning("未找到学校列")

            # 获取班级选项
            if "class" in admin_cols:
                class_col = admin_cols["class"]
                if selected_schools and "school" in admin_cols and selected_schools:
                    school_col = admin_cols["school"]
                    valid_schools = [
                        s for s in selected_schools if s in self.data[school_col].values
                    ]
                    if valid_schools:
                        filtered_df = self.data[
                            self.data[school_col].isin(valid_schools)
                        ]
                        classes_data = filtered_df[class_col].dropna()
                    else:
                        classes_data = self.data[class_col].dropna()
                        self.logger.warning("选择的学校在数据中不存在，显示所有班级")
                elif selected_counties and "county" in admin_cols and selected_counties:
                    county_col = admin_cols["county"]
                    valid_counties = [
                        c
                        for c in selected_counties
                        if c in self.data[county_col].values
                    ]
                    if valid_counties:
                        filtered_df = self.data[
                            self.data[county_col].isin(valid_counties)
                        ]
                        classes_data = filtered_df[class_col].dropna()
                    else:
                        classes_data = self.data[class_col].dropna()
                        self.logger.warning("选择的区县在数据中不存在，显示所有班级")
                else:
                    classes_data = self.data[class_col].dropna()

                classes = sorted(
                    [str(c) for c in classes_data.unique() if str(c).strip()]
                )
                options["class"] = [{"label": str(c), "value": str(c)} for c in classes]
                self.logger.info(f"找到班级选项: {len(options['class'])}个")
            else:
                self.logger.warning("未找到班级列")

        except Exception as e:
            self.logger.error(f"获取联动选项失败: {e}")
            import traceback

            self.logger.error(f"详细错误: {traceback.format_exc()}")

        return options

    def filter_data_by_selection(
        self,
        selected_counties: List[str] = None,
        selected_schools: List[str] = None,
        selected_classes: List[str] = None,
    ) -> pd.DataFrame:
        """根据选择筛选数据"""
        filtered_df = self.data.copy()
        admin_cols = self.get_administrative_columns()

        try:
            if selected_counties and "county" in admin_cols:
                county_col = admin_cols["county"]
                filtered_df = filtered_df[
                    filtered_df[county_col].isin(selected_counties)
                ]

            if selected_schools and "school" in admin_cols:
                school_col = admin_cols["school"]
                filtered_df = filtered_df[
                    filtered_df[school_col].isin(selected_schools)
                ]

            if selected_classes and "class" in admin_cols:
                class_col = admin_cols["class"]
                filtered_df = filtered_df[filtered_df[class_col].isin(selected_classes)]

        except Exception as e:
            self.logger.error(f"数据筛选失败: {e}")

        return filtered_df

    def calculate_performance_analysis(self) -> Dict[str, Any]:
        """计算单次考试成绩的有意义分析

        Returns:
            包含成绩分布、难度分析等的字典
        """
        performance_results = {}

        try:
            for col in self.subject_columns:
                if col not in self.data.columns:
                    continue

                col_data = self.data[col].dropna()
                if len(col_data) < 10:
                    continue

                # 计算成绩分布指标
                stats = {
                    "count": len(col_data),
                    "mean": col_data.mean(),
                    "median": col_data.median(),
                    "std": col_data.std(),
                    "min": col_data.min(),
                    "max": col_data.max(),
                    "range": col_data.max() - col_data.min(),
                    "q25": col_data.quantile(0.25),
                    "q75": col_data.quantile(0.75),
                    "iqr": col_data.quantile(0.75) - col_data.quantile(0.25),
                    "skewness": col_data.skew(),
                    "kurtosis": col_data.kurtosis(),
                }

                # 成绩等级分布
                def get_grade_level(score, max_score=100):
                    """根据分数确定等级"""
                    ratio = score / max_score
                    if ratio >= 0.9:
                        return "A(优秀)"
                    elif ratio >= 0.8:
                        return "B(良好)"
                    elif ratio >= 0.7:
                        return "C(中等)"
                    elif ratio >= 0.6:
                        return "D(及格)"
                    else:
                        return "E(不及格)"

                grade_dist = {}
                max_score = stats["max"]
                for score in col_data:
                    grade = get_grade_level(score, max_score)
                    grade_dist[grade] = grade_dist.get(grade, 0) + 1

                # 获取标准满分
                standard_full_score = self.get_standard_full_score(col)

                # 计算难度系数（难度 = 1 - 平均分/标准满分）
                difficulty = (
                    1 - (stats["mean"] / standard_full_score)
                    if standard_full_score > 0
                    else 0
                )

                # 计算区分度（简化版，使用标准差/标准满分）
                discrimination = (
                    stats["std"] / standard_full_score if standard_full_score > 0 else 0
                )

                performance_results[col] = {
                    **stats,
                    "grade_distribution": grade_dist,
                    "difficulty": difficulty,
                    "discrimination": discrimination,
                    "max_score": max_score,
                }

            self.logger.info(f"成绩分析完成，分析了{len(performance_results)}个科目")

            # 保存到数据库
            if self.db and self.raw_data_id and performance_results:
                try:
                    self.db.store_comprehensive_analysis(
                        raw_data_id=self.raw_data_id,
                        analysis_type="performance_analysis",
                        results=performance_results,
                    )
                    self.logger.info("性能分析结果已保存到数据库")
                except Exception as e:
                    self.logger.error(f"保存性能分析结果到数据库失败: {e}")

            return performance_results

        except Exception as e:
            self.logger.error(f"成绩分析失败: {e}")

        return performance_results

    def merge_performance_results(self):
        """合并成绩分析结果 - 按科目分组显示图表和指标"""
        try:
            # 获取成绩分析结果
            performance_results = self.calculate_performance_analysis()
            performance_figs = self.generate_visualization_dashboard("performance")

            self.logger.info(
                (
                    f"performance_results数量: "
                    f"{len(performance_results) if performance_results else 0}"
                )
            )
            self.logger.info(
                (
                    f"performance_figs数量: "
                    f"{len(performance_figs) if performance_figs else 0}"
                )
            )

            if not performance_results:
                return html.Div("暂无成绩分析数据")

            # 按科目分组显示
            subject_rows = []

            # 按科目分组图表
            subject_figs = {}
            if performance_figs:
                for key, fig in performance_figs.items():
                    self.logger.info(f"处理图表键: {key}")
                    if "_performance" in key:
                        subject = key.replace("_performance", "")
                        subject_figs.setdefault(subject, {})["histogram"] = fig
                    elif "_grade_distribution" in key:
                        subject = key.replace("_grade_distribution", "")
                        subject_figs.setdefault(subject, {})["grade_pie"] = fig

            self.logger.info(f"分组后的科目数量: {len(subject_figs)}")

            # 如果没有图表，只显示关键指标
            if not subject_figs:
                for subject, analysis in performance_results.items():
                    metrics_content = dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H6(
                                            f"{subject}关键指标",
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                f"平均分: {analysis['mean']:.1f}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"中位数: {analysis['median']:.1f}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"难度系数: {analysis['difficulty']:.2f}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"区分度: {analysis['discrimination']:.2f}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"标准差: {analysis['std']:.2f}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"满分: {analysis['max_score']}",
                                                className="mb-0",
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=12,
                    )

                    subject_rows.append(dbc.Row([metrics_content], className="mb-4"))
            else:
                # 为每个科目创建一行
                for subject, figs in subject_figs.items():
                    # 左侧：等级分布饼图
                    grade_chart = None
                    if "grade_pie" in figs:
                        grade_chart = dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                f"{subject}等级分布",
                                                className="mb-0",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    figure=figs["grade_pie"],
                                                    config={"displayModeBar": False},
                                                    style={"height": "auto"},
                                                )
                                            ]
                                        ),
                                    ]
                                )
                            ],
                            width=6,
                        )

                    # 右侧：关键指标
                    metrics_content = None
                    if subject in performance_results:
                        analysis = performance_results[subject]
                        difficulty_level = (
                            "容易"
                            if analysis["difficulty"] > 0.8
                            else ("中等" if analysis["difficulty"] > 0.6 else "困难")
                        )
                        discrimination_level = (
                            "优秀"
                            if analysis["discrimination"] > 0.4
                            else (
                                "良好"
                                if analysis["discrimination"] > 0.3
                                else (
                                    "一般"
                                    if analysis["discrimination"] > 0.2
                                    else "较差"
                                )
                            )
                        )

                        metrics_content = dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                f"{subject}关键指标",
                                                className="mb-0",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.P(
                                                    f"平均分: {analysis['mean']:.1f}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"中位数: {analysis['median']:.1f}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"难度系数: {analysis['difficulty']:.2f} ({difficulty_level})",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"区分度: {analysis['discrimination']:.2f} ({discrimination_level})",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"标准差: {analysis['std']:.2f}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"满分: {analysis['max_score']}",
                                                    className="mb-0",
                                                ),
                                            ]
                                        ),
                                    ]
                                )
                            ],
                            width=6,
                        )

                    # 如果缺少某个组件，让存在的组件占据整行
                    if grade_chart and metrics_content:
                        row_content = [grade_chart, metrics_content]
                    elif grade_chart:
                        grade_chart.props.width = 12
                        row_content = [grade_chart]
                    elif metrics_content:
                        metrics_content.props.width = 12
                        row_content = [metrics_content]
                    else:
                        continue

                    subject_rows.append(dbc.Row(row_content, className="mb-4"))

            return (
                html.Div(subject_rows) if subject_rows else html.Div("暂无成绩分析数据")
            )

        except Exception as e:
            self.logger.error(f"合并成绩分析结果失败: {e}")
            return html.Div(f"成绩分析失败: {str(e)}")

    def aggregate_global_data(
        self,
        groupby_columns: List[str] = None,
        agg_functions: Dict[str, List[str]] = None,
    ) -> pd.DataFrame:
        """全局数据聚合与汇总计算"""

        try:
            if groupby_columns is None:
                groupby_columns = []

            if agg_functions is None:
                # 默认聚合配置
                agg_functions = {}
                for col in self.subject_columns:
                    agg_functions[col] = ["mean", "std", "min", "max", "count"]
                if "新高考总分" in self.data.columns:
                    agg_functions["新高考总分"] = [
                        "mean",
                        "std",
                        "min",
                        "max",
                        "count",
                    ]

            # 过滤存在的列
            valid_groupby = [col for col in groupby_columns if col in self.data.columns]
            valid_agg = {
                col: funcs
                for col, funcs in agg_functions.items()
                if col in self.data.columns
            }

            if not valid_agg:
                self.logger.warning("没有找到有效的数值列进行聚合")
                return pd.DataFrame()

            # 执行聚合计算
            if valid_groupby:
                result = self.data.groupby(valid_groupby, observed=True).agg(valid_agg)
            else:
                result = self.data.agg(valid_agg)

            # 扁平化多级列名
            if isinstance(result.columns, pd.MultiIndex):
                result.columns = [f"{col[0]}_{col[1]}" for col in result.columns]

            # 缓存机制已移除

            self.logger.info(f"数据聚合完成，结果形状: {result.shape}")
            return result

        except Exception as e:
            self.logger.error(f"数据聚合失败: {e}")
            return pd.DataFrame()

    def generate_visualization_dashboard(
        self, analysis_type: str = "all"
    ) -> Dict[str, go.Figure]:
        """生成可视化图表面板

        Args:
            analysis_type: 分析类型 ('performance', 'outlier', 'all')

        Returns:
            图表字典
        """
        figures = {}

        try:
            if analysis_type in ["performance", "all"]:
                # 成绩分布直方图
                for col in self.subject_columns:
                    if col in self.data.columns:
                        col_data = self.data[col].dropna()
                        if len(col_data) >= 10:
                            fig = go.Figure()
                            fig.add_trace(
                                go.Histogram(
                                    x=col_data,
                                    name=f"{col}成绩分布",
                                    nbinsx=20,
                                    opacity=0.7,
                                )
                            )

                            fig.update_layout(
                                title=f"{col}成绩分布分析",
                                xaxis_title="分数",
                                yaxis_title="人数",
                                height=400,
                            )

                            figures[f"{col}_performance"] = fig

                            # 成绩等级分布饼图
                            performance_results = self.calculate_performance_analysis()
                            if col in performance_results:
                                grade_dist = performance_results[col][
                                    "grade_distribution"
                                ]
                                if grade_dist:
                                    fig_pie = go.Figure()
                                    fig_pie.add_trace(
                                        go.Pie(
                                            labels=list(grade_dist.keys()),
                                            values=list(grade_dist.values()),
                                            name="等级分布",
                                            hole=0.3,
                                        )
                                    )
                                    fig_pie.update_layout(
                                        title=f"{col}等级分布", height=300
                                    )
                                    figures[f"{col}_grade_distribution"] = fig_pie

        except Exception as e:
            self.logger.error(f"生成可视化图表失败: {e}")

        return figures





    def create_admission_rate_analysis(self, custom_standards=None):
        """创建上线率分析图表"""
        try:
            # 使用自定义分数线或默认分数线
            if custom_standards:
                standards = custom_standards
            else:
                # 默认分数线（如果用户没有设置）
                standards = {
                    "本科线": 375,
                    "特控线": 475,
                    "重点线": 425,
                    "保底线": 300,
                }

            if "新高考总分" not in self.data.columns:
                return html.Div(
                    "数据中缺少总分列，无法进行上线率分析",
                    className="text-muted",
                )

            total_scores = self.data["新高考总分"].dropna()

            # 计算各线上线人数
            admission_data = []
            for name, threshold in standards.items():
                count = (total_scores >= threshold).sum()
                rate = count / len(total_scores) * 100
                admission_data.append(
                    {"分数线": name, "人数": count, "上线率": f"{rate:.1f}%"}
                )

            # 创建上线率柱状图
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=[d["分数线"] for d in admission_data],
                    y=[d["人数"] for d in admission_data],
                    text=[d["上线率"] for d in admission_data],
                    textposition="auto",
                    name="上线人数",
                )
            )

            fig.update_layout(
                title="各分数线上线情况分析",
                xaxis_title="分数线类型",
                yaxis_title="人数",
                height=400,
            )

            return dbc.Col(
                [dcc.Graph(figure=fig, config={"displayModeBar": False})],
                width=12,
            )

        except Exception as e:
            self.logger.error(f"上线率分析失败: {e}")
            return html.Div(f"上线率分析失败: {str(e)}", className="text-danger")

    def create_admission_stats(self, custom_standards=None):
        """创建上线率统计表"""
        try:
            # 使用自定义分数线或默认分数线
            if custom_standards:
                standards = custom_standards
            else:
                # 默认分数线（如果用户没有设置）
                standards = {
                    "本科线": 375,
                    "特控线": 475,
                    "重点线": 425,
                    "保底线": 300,
                }

            if "新高考总分" not in self.data.columns:
                return html.Div("数据中缺少总分列", className="text-muted")

            total_scores = self.data["新高考总分"].dropna()

            stats_data = []
            for name, threshold in standards.items():
                qualified = total_scores[total_scores >= threshold]
                count = len(qualified)
                rate = count / len(total_scores) * 100
                avg_score = qualified.mean() if len(qualified) > 0 else 0
                max_score = qualified.max() if len(qualified) > 0 else 0
                min_score = qualified.min() if len(qualified) > 0 else 0

                stats_data.append(
                    {
                        "分数线": name,
                        "分数线标准": threshold,
                        "上线人数": count,
                        "上线率": f"{rate:.1f}%",
                        "平均分": f"{avg_score:.1f}" if avg_score > 0 else "-",
                        "最高分": f"{max_score:.1f}" if max_score > 0 else "-",
                        "最低分": f"{min_score:.1f}" if min_score > 0 else "-",
                    }
                )

            return dbc.Card(
                [
                    dbc.CardHeader("📊 上线率统计详情"),
                    dbc.CardBody(
                        [
                            dbc.Table.from_dataframe(
                                pd.DataFrame(stats_data),
                                striped=True,
                                bordered=True,
                                hover=True,
                                size="sm",
                            )
                        ]
                    ),
                ]
            )

        except Exception as e:
            self.logger.error(f"上线率统计失败: {e}")
            return html.Div(f"上线率统计失败: {str(e)}", className="text-danger")

    def get_standard_full_score(self, subject):
        """获取各科目的标准满分"""
        # 主科：150分
        main_subjects = [
            "语文",
            "数学",
            "英语",
            "日语",
            "俄语",
            "德语",
            "法语",
            "西班牙语",
        ]
        # 其他科目：100分
        other_subjects = [
            "物理",
            "化学",
            "生物",
            "政治",
            "历史",
            "地理",
            "音乐",
            "美术",
            "体育",
            "信息技术",
            "通用技术",
        ]

        if subject in main_subjects:
            return 150
        elif subject in other_subjects:
            return 100
        else:
            # 对于不在列表中的科目，根据实际最高分推断
            actual_max = self.data[subject].max()
            if actual_max > 130:  # 超过130分，可能是150分制
                return 150
            else:  # 其他情况默认100分制
                return 100

    def create_subject_indicators_table(self):
        """创建学科指标表 - 根据选定班级的实际选科动态分析"""
        try:
            performance_results = self.calculate_performance_analysis()

            indicators_data = []
            for subject, stats in performance_results.items():
                # 检查该科目在当前筛选数据中是否有有效的学生数据
                subject_data = self.data[subject].dropna()
                if len(subject_data) == 0:
                    # 如果没有学生选择此科目，跳过显示
                    continue

                difficulty_level = (
                    "容易"
                    if stats["difficulty"] > 0.8
                    else ("中等" if stats["difficulty"] > 0.6 else "困难")
                )
                discrimination_level = (
                    "优秀"
                    if stats["discrimination"] > 0.4
                    else (
                        "良好"
                        if stats["discrimination"] > 0.3
                        else ("一般" if stats["discrimination"] > 0.2 else "较差")
                    )
                )

                # 计算优秀率和及格率（使用标准满分）
                standard_full_score = self.get_standard_full_score(subject)
                excellent_count = sum(
                    1 for score in subject_data if score >= standard_full_score * 0.9
                )
                pass_count = sum(
                    1 for score in subject_data if score >= standard_full_score * 0.6
                )
                total_count = len(subject_data)

                excellent_rate = (
                    excellent_count / total_count * 100 if total_count > 0 else 0
                )
                pass_rate = pass_count / total_count * 100 if total_count > 0 else 0

                indicators_data.append(
                    {
                        "科目": subject,
                        "平均分": f"{stats['mean']:.1f}",
                        "中位数": f"{stats['median']:.1f}",
                        "标准差": f"{stats['std']:.2f}",
                        "难度系数": f"{stats['difficulty']:.2f} ({difficulty_level})",
                        "区分度": f"{stats['discrimination']:.2f} ({discrimination_level})",
                        "优秀率": f"{excellent_rate:.1f}%",
                        "及格率": f"{pass_rate:.1f}%",
                        "满分": f"{standard_full_score}分",
                        "选科人数": total_count,  # 新增：显示实际选科人数
                    }
                )

            if indicators_data:
                # 按选科人数降序排列，选科人数多的科目排在前面
                indicators_df = pd.DataFrame(indicators_data)
                indicators_df = indicators_df.sort_values("选科人数", ascending=False)

                return dbc.Card(
                    [
                        dbc.CardHeader("📊 学科关键指标分析表（根据选定班级实际选科）"),
                        dbc.CardBody(
                            [
                                html.P(
                                    f"显示科目：{len(indicators_data)} 个，总计学生：{len(self.data)} 人",
                                    className="text-muted mb-3",
                                ),
                                dbc.Table.from_dataframe(
                                    indicators_df,
                                    striped=True,
                                    bordered=True,
                                    hover=True,
                                    size="sm",
                                ),
                            ]
                        ),
                    ]
                )
            else:
                return html.Div(
                    "选定的班级/学校中没有找到有效的选科数据",
                    className="text-muted",
                )

        except Exception as e:
            self.logger.error(f"学科指标表创建失败: {e}")
            return html.Div(f"学科指标表创建失败: {str(e)}", className="text-danger")

    def create_class_radar_chart(self):
        """创建班级雷达图（分150分和100分两个雷达图）"""
        try:
            self.logger.info("开始创建班级雷达图")
            admin_cols = self.get_administrative_columns()
            self.logger.info(f"行政列: {admin_cols}")

            if "class" not in admin_cols:
                return html.Div(
                    "数据中缺少班级信息，无法生成雷达图",
                    className="text-muted",
                )

            class_col = admin_cols["class"]
            classes = self.data[class_col].dropna().unique()

            if len(classes) == 0:
                return html.Div("没有找到有效的班级数据", className="text-muted")

            # 限制显示前10个班级
            if len(classes) > 10:
                classes = classes[:10]

            # 分类科目：150分科目和100分科目
            subject_150 = []  # 150分科目
            subject_100 = []  # 100分科目

            for subject in self.subject_columns:
                subject_lower = str(subject).lower()
                # 150分科目：语文、数学、英语、日语、俄语、德语等
                if any(
                    keyword in subject_lower
                    for keyword in [
                        "语文",
                        "数学",
                        "英语",
                        "外语",
                        "日语",
                        "俄语",
                        "德语",
                        "法语",
                        "西班牙语",
                    ]
                ):
                    subject_150.append(subject)
                else:
                    # 其他科目默认为100分
                    subject_100.append(subject)

            self.logger.info(f"150分科目: {subject_150}")
            self.logger.info(f"100分科目: {subject_100}")

            # 如果没有找到相应类别的科目，则返回提示信息
            if not subject_150 and not subject_100:
                return html.Div("没有找到可用的科目数据", className="text-muted")

            # 计算各班级各科目的平均分
            def calculate_class_averages(subjects):
                class_averages = {}
                for cls in classes:
                    class_data = self.data[self.data[class_col] == cls]
                    averages = {}
                    for subject in subjects:
                        if subject in class_data.columns:
                            avg = class_data[subject].mean()
                            averages[subject] = avg if not pd.isna(avg) else 0
                    class_averages[cls] = averages
                return class_averages

            class_averages_150 = (
                calculate_class_averages(subject_150) if subject_150 else {}
            )
            class_averages_100 = (
                calculate_class_averages(subject_100) if subject_100 else {}
            )

            # 创建雷达图的辅助函数
            def create_single_radar_chart(class_averages, title, max_score):
                """创建单个雷达图"""
                if not class_averages:
                    return None

                fig = go.Figure()
                colors = px.colors.qualitative.Set1

                for i, (cls, averages) in enumerate(class_averages.items()):
                    if averages:
                        subjects = list(averages.keys())
                        values = list(averages.values())

                        # 闭合雷达图
                        subjects.append(subjects[0])
                        values.append(values[0])

                        fig.add_trace(
                            go.Scatterpolar(
                                r=values,
                                theta=subjects,
                                fill="toself",
                                name=str(cls),
                                line_color=colors[i % len(colors)],
                            )
                        )

                # 计算所有科目的最大值来设置雷达图范围
                all_values = []
                for averages in class_averages.values():
                    all_values.extend(averages.values())

                max_range = max(all_values) if all_values else max_score
                # 为雷达图设置合理的上限，至少为最大值的1.2倍，但不超过满分
                radar_max = min(max_range * 1.2, max_score)

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, radar_max])),
                    title=title,
                    height=600,
                    showlegend=True,
                )

                return fig

            # 创建两个雷达图
            charts = []

            # 150分科目雷达图
            if subject_150 and class_averages_150:
                fig_150 = create_single_radar_chart(
                    class_averages_150,
                    "班级150分科目平均分雷达图（满分150分）",
                    150,
                )
                if fig_150:
                    charts.append(
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader("📊 150分科目雷达图"),
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    figure=fig_150,
                                                    config={"displayModeBar": True},
                                                )
                                            ]
                                        ),
                                    ]
                                )
                            ],
                            width=12,
                        )
                    )

            # 100分科目雷达图
            if subject_100 and class_averages_100:
                fig_100 = create_single_radar_chart(
                    class_averages_100,
                    "班级100分科目平均分雷达图（满分100分）",
                    100,
                )
                if fig_100:
                    charts.append(
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader("📊 100分科目雷达图"),
                                        dbc.CardBody(
                                            [
                                                dcc.Graph(
                                                    figure=fig_100,
                                                    config={"displayModeBar": True},
                                                )
                                            ]
                                        ),
                                    ]
                                )
                            ],
                            width=12,
                        )
                    )

            if not charts:
                return html.Div(
                    "没有可用的科目数据来生成雷达图", className="text-muted"
                )

            # 如果有两个图表，分两行显示；否则单行显示
            if len(charts) == 2:
                return html.Div(
                    [
                        dbc.Row([charts[0]], className="mb-4"),
                        dbc.Row([charts[1]]),
                    ]
                )
            else:
                return dbc.Row(charts)

        except Exception as e:
            self.logger.error(f"班级雷达图创建失败: {e}")
            return html.Div(f"班级雷达图创建失败: {str(e)}", className="text-danger")

    def create_comparison_chart(self):
        """创建关键指标对比图表"""
        try:
            self.logger.info("开始创建关键指标对比图表")
            performance_results = self.calculate_performance_analysis()

            self.logger.info(
                f"性能分析结果: {list(performance_results.keys()) if performance_results else '无'}"
            )

            if not performance_results:
                return html.Div("暂无数据可供对比", className="text-muted")

            # 准备对比数据
            subjects = list(performance_results.keys())
            means = [performance_results[subj]["mean"] for subj in subjects]
            stds = [performance_results[subj]["std"] for subj in subjects]
            difficulties = [
                performance_results[subj]["difficulty"] for subj in subjects
            ]
            discriminations = [
                performance_results[subj]["discrimination"] for subj in subjects
            ]

            # 创建对比图表
            fig = make_subplots(
                rows=2,
                cols=2,
                subplot_titles=(
                    "平均分对比",
                    "难度系数对比",
                    "区分度对比",
                    "标准差对比",
                ),
                specs=[
                    [{"type": "bar"}, {"type": "bar"}],
                    [{"type": "bar"}, {"type": "bar"}],
                ],
            )

            # 平均分对比
            fig.add_trace(
                go.Bar(
                    x=subjects,
                    y=means,
                    name="平均分",
                    marker_color="lightblue",
                ),
                row=1,
                col=1,
            )

            # 难度系数对比
            fig.add_trace(
                go.Bar(
                    x=subjects,
                    y=difficulties,
                    name="难度系数",
                    marker_color="lightcoral",
                ),
                row=1,
                col=2,
            )

            # 区分度对比
            fig.add_trace(
                go.Bar(
                    x=subjects,
                    y=discriminations,
                    name="区分度",
                    marker_color="lightgreen",
                ),
                row=2,
                col=1,
            )

            # 标准差对比
            fig.add_trace(
                go.Bar(
                    x=subjects,
                    y=stds,
                    name="标准差",
                    marker_color="lightyellow",
                ),
                row=2,
                col=2,
            )

            fig.update_layout(
                title_text="各科目关键指标对比分析",
                showlegend=False,
                height=600,
            )

            return dbc.Col(
                [dcc.Graph(figure=fig, config={"displayModeBar": True})],
                width=12,
            )

        except Exception as e:
            self.logger.error(f"关键指标对比图表创建失败: {e}")
            return html.Div(
                f"关键指标对比图表创建失败: {str(e)}", className="text-danger"
            )




def create_enhanced_selection_info_badge(
    selection_level: str,
    analysis_types: List[str],
    selected_counties: List[str],
    selected_schools: List[str],
    selected_classes: List[str],
    student_count: int,
):
    """创建增强选择信息徽章"""
    selection_info = dbc.Alert(
        [
            html.H6("📊 数据筛选信息", className="alert-heading"),
            html.P(f"分析级别: {selection_level}", className="mb-1"),
            html.P(
                f"分析类型: {', '.join(analysis_types) if analysis_types else '全部'}",
                className="mb-1",
            ),
            html.P(
                f"选中区县: {', '.join(selected_counties) if selected_counties else '全部'}",
                className="mb-1",
            ),
            html.P(
                f"选中学校: {', '.join(selected_schools) if selected_schools else '全部'}",
                className="mb-1",
            ),
            html.P(
                f"选中班级: {', '.join(selected_classes) if selected_classes else '全部'}",
                className="mb-1",
            ),
            html.P(f"学生数量: {student_count} 人", className="mb-0"),
        ],
        color="info",
    )

    return selection_info


# ========================================
# UI组件和回调函数
# ========================================
def create_comprehensive_analyzer_ui(app):
    """创建增强版综合分析器的UI组件"""

    # 综合分析回调
    @app.callback(
        [
            Output("comprehensive_welcome_message", "children"),
            Output("enhanced_selection_info", "children"),
            Output("aggregation_section", "style"),
            Output("comparison_section", "style"),
            Output("performance_section", "style"),
            Output("admission_section", "style"),
            Output("indicators_section", "style"),
            Output("radar_section", "style"),
            Output("aggregation_table", "children"),
            Output("comparison_chart", "children"),
            Output("performance_results", "children"),
            Output("admission_rate_chart", "children"),
            Output("admission_rate_stats", "children"),
            Output("subject_indicators_table", "children"),
            Output("class_radar_chart", "children"),
        ],
        [
            Input("run_comprehensive_analysis_btn", "n_clicks"),
        ],
        [
            State("county_dropdown", "value"),
            State("school_dropdown", "value"),
            State("class_dropdown", "value"),
            State("data_store", "data"),
            State("analysis_types_control", "value"),
            State("undergraduate_threshold_control", "value"),
            State("special_threshold_control", "value"),
            State("key_threshold_control", "value"),
            State("basic_threshold_control", "value"),
        ],
    )
    def run_comprehensive_analysis(
        n_clicks,
        selected_counties,
        selected_schools,
        selected_classes,
        data_json,
        analysis_types,
        undergraduate_thresh,
        special_thresh,
        key_thresh,
        basic_thresh,
    ):
        # 默认显示状态
        default_style = {"display": "none"}
        show_style = {"display": "block"}
        
        # 处理数据不存在的情况
        if data_json is None:
            return (
                dbc.Alert("请先上传数据", color="warning"),
                html.Div(),  # selection_info
                default_style, default_style, default_style, default_style, 
                default_style, default_style,  # section styles
                None, None, None, None, None, None, None,  # table/chart contents
            )
        
        # 正常的完整分析流程
        if n_clicks is None or n_clicks == 0:
            return (
                dbc.Alert(
                    [
                        html.H5("📊 综合分析", className="alert-heading"),
                        html.P("请在左侧选择分析类型并点击'开始分析'按钮"),
                    ],
                    color="info",
                ),
                html.Div(),  # selection_info
                default_style, default_style, default_style, default_style, 
                default_style, default_style,  # section styles
                None, None, None, None, None, None, None,  # table/chart contents
            )

        try:
            # 创建配置
            config = {
                "cache_enabled": False,
                "use_parallel": True,
            }

            # 创建分析器实例（使用原始数据）
            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = ComprehensiveAnalyzer(df, config)

            # 筛选数据
            filtered_df = analyzer.filter_data_by_selection(
                selected_counties=selected_counties,
                selected_schools=selected_schools,
                selected_classes=selected_classes,
            )

            # 检查筛选结果
            if filtered_df.empty:
                error_msg = dbc.Alert(
                    [
                        html.H5("❌ 筛选结果为空", className="alert-heading"),
                        html.P("根据选择的条件没有找到符合的数据"),
                    ],
                    color="warning",
                )
                return (
                    error_msg,  # welcome_message
                    html.Div(),  # selection_info
                    default_style, default_style, default_style, default_style, 
                    default_style, default_style,  # section styles
                    None, None, None, None, None, None, None,  # table/chart contents
                )

            # 创建基于筛选数据的分析器实例（确保所有分析都使用筛选后的数据）
            filtered_analyzer = ComprehensiveAnalyzer(filtered_df, config)

            # 创建增强筛选信息
            selection_level = (
                "班级"
                if selected_classes
                else (
                    "学校"
                    if selected_schools
                    else ("区县" if selected_counties else "全部")
                )
            )
            selection_info = create_enhanced_selection_info_badge(
                selection_level=selection_level,
                analysis_types=analysis_types or [],
                selected_counties=selected_counties or [],
                selected_schools=selected_schools or [],
                selected_classes=selected_classes or [],
                student_count=len(filtered_df),
            )

            # 初始化所有输出为None
            agg_table = comp_chart = performance_results = None
            admission_chart = admission_stats = indicators_table = radar_chart = None

            # 数据聚合分析（使用筛选后的数据）
            if "aggregation" in (analysis_types or []):
                agg_results = filtered_analyzer.aggregate_global_data()
                if not agg_results.empty:
                    # 为聚合结果添加统计指标表头
                    agg_display = agg_results.copy()

                    # 创建行索引映射
                    index_mapping = {}
                    for idx in agg_display.index:
                        if isinstance(idx, str):
                            if "mean" in idx:
                                index_mapping[idx] = "平均值"
                            elif "std" in idx:
                                index_mapping[idx] = "标准差"
                            elif "min" in idx:
                                index_mapping[idx] = "最小值"
                            elif "max" in idx:
                                index_mapping[idx] = "最大值"
                            elif "count" in idx:
                                index_mapping[idx] = "数据量"
                            else:
                                index_mapping[idx] = idx
                        else:
                            index_mapping[idx] = str(idx)

                    # 重命名索引
                    agg_display.index = [
                        index_mapping[idx] for idx in agg_display.index
                    ]

                    # 重置索引，使统计指标成为第一列
                    agg_display = agg_display.reset_index()
                    agg_display = agg_display.rename(columns={"index": "统计指标"})

                    agg_table = dbc.Table.from_dataframe(
                        agg_display.round(2),
                        striped=True,
                        bordered=True,
                        hover=True,
                        size="sm",
                        className="mt-2",
                        style={"maxHeight": "400px", "overflow": "auto"},
                    )

            # 关键指标对比分析（使用筛选后的数据）
            if "comparison" in (analysis_types or []):
                comp_chart = filtered_analyzer.create_comparison_chart()



            # 成绩分析（使用筛选后的数据）
            if "performance" in (analysis_types or []):
                performance_results = filtered_analyzer.merge_performance_results()

            # 创建自定义分数线
            custom_standards = {
                "本科线": undergraduate_thresh or 375,
                "特控线": special_thresh or 475,
                "重点线": key_thresh or 425,
                "保底线": basic_thresh or 300,
            }

            # 上线率分析（使用筛选后的数据）
            if "admission" in (analysis_types or []):
                admission_chart = filtered_analyzer.create_admission_rate_analysis(
                    custom_standards
                )
                admission_stats = filtered_analyzer.create_admission_stats(
                    custom_standards
                )

            # 学科指标表（使用筛选后的数据）
            if "indicators" in (analysis_types or []):
                indicators_table = filtered_analyzer.create_subject_indicators_table()

            # 班级雷达图（使用筛选后的数据）
            if "radar" in (analysis_types or []):
                radar_chart = filtered_analyzer.create_class_radar_chart()

            # 确定哪些部分应该显示
            section_styles = {
                "aggregation": show_style if "aggregation" in (analysis_types or []) else default_style,
                "comparison": show_style if "comparison" in (analysis_types or []) else default_style,
                "performance": show_style if "performance" in (analysis_types or []) else default_style,
                "admission": show_style if "admission" in (analysis_types or []) else default_style,
                "indicators": show_style if "indicators" in (analysis_types or []) else default_style,
                "radar": show_style if "radar" in (analysis_types or []) else default_style,
            }

            # 隐藏欢迎消息，显示选择信息
            welcome_msg = html.Div()  # 空div来隐藏欢迎消息
            
            return (
                welcome_msg,  # welcome_message
                selection_info,  # selection_info
                section_styles["aggregation"], section_styles["comparison"], 
                section_styles["performance"], section_styles["admission"], 
                section_styles["indicators"], section_styles["radar"],  # section styles
                agg_table, comp_chart, performance_results,  # table/chart contents
                admission_chart, admission_stats, indicators_table, radar_chart,
            )

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"增强分析失败: {e}")

            error_msg = dbc.Alert(
                [
                    html.H5("❌ 增强分析失败", className="alert-heading"),
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

            return (
                error_msg,  # welcome_message
                html.Div(),  # selection_info
                default_style, default_style, default_style, default_style, 
                default_style, default_style,  # section styles
                None, None, None, None, None, None, None,  # table/chart contents
            )


def create_comprehensive_control_panel():
    """创建综合分析控制面板"""
    return dbc.Card(
        [
            dbc.CardHeader("🔍 综合分析控制"),
            dbc.CardBody(
                [
                    # 分析类型选择
                    html.Label("分析类型:", className="form-label"),
                    dcc.Dropdown(
                        id="analysis_types_control",
                        options=[
                            {"label": "数据聚合", "value": "aggregation"},
                            {"label": "成绩分析", "value": "performance"},
                            {"label": "关键指标对比", "value": "comparison"},
                            {"label": "上线率分析", "value": "admission"},
                            {"label": "学科指标表", "value": "indicators"},
                            {"label": "班级雷达图", "value": "radar"},
                        ],
                        value=[
                            "aggregation",
                            "performance",
                            "comparison",
                            "admission",
                            "indicators",
                            "radar",
                        ],
                        multi=True,
                        className="mb-3",
                    ),
                    # 分析按钮
                    html.Div(
                        dbc.Button(
                            "开始分析",
                            id="run_comprehensive_analysis_btn",
                            color="primary",
                            size="lg",
                            className="w-100",
                        ),
                        className="mb-3",
                    ),
                    # 分析选项
                    html.H6("分析选项", className="form-label"),
                    # 分数阈值设置
                    html.Label("本科线:", className="form-label small"),
                    dbc.Input(
                        id="undergraduate_threshold_control",
                        type="number",
                        value=450,
                        className="mb-2",
                        size="sm",
                    ),
                    html.Label("专科线:", className="form-label small"),
                    dbc.Input(
                        id="special_threshold_control",
                        type="number",
                        value=350,
                        className="mb-2",
                        size="sm",
                    ),
                    html.Label("重点线:", className="form-label small"),
                    dbc.Input(
                        id="key_threshold_control",
                        type="number",
                        value=500,
                        className="mb-2",
                        size="sm",
                    ),
                    html.Label("基础线:", className="form-label small"),
                    dbc.Input(
                        id="basic_threshold_control",
                        type="number",
                        value=300,
                        className="mb-3",
                        size="sm",
                    ),
                    # 使用说明
                    dbc.Alert(
                        [
                            html.H6("📋 使用说明", className="alert-heading"),
                            html.Ul(
                                [
                                    html.Li("选择需要的分析类型"),
                                    html.Li("设置各分数线阈值"),
                                    html.Li("点击'开始分析'按钮"),
                                    html.Li("查看右侧分析结果"),
                                ],
                                className="mb-0",
                            ),
                        ],
                        color="info",
                        className="small",
                    ),
                ]
            ),
        ],
        className="h-100",
    )


def create_comprehensive_results_panel():
    """创建综合分析结果面板"""
    return dbc.Card(
        [
            dbc.CardHeader("📊 综合分析结果"),
            dbc.CardBody(
                [
                    # 初始提示信息
                    html.Div(
                        dbc.Alert(
                            [
                                html.H5("📊 综合分析", className="alert-heading"),
                                html.P("请在左侧选择分析类型并点击'开始分析'按钮"),
                            ],
                            color="info",
                        ),
                        id="comprehensive_welcome_message",
                        className="mb-4",
                    ),
                    # 选择信息显示
                    html.Div(id="enhanced_selection_info", className="mb-4", style={"display": "none"}),
                    # 数据聚合表格
                    html.Div(id="aggregation_section", className="mb-4", style={"display": "none"}, children=[
                        html.H5("📈 数据聚合表格"),
                        html.Div(id="aggregation_table"),
                    ]),
                    # 对比图表
                    html.Div(id="comparison_section", className="mb-4", style={"display": "none"}, children=[
                        html.H5("📊 关键指标对比"),
                        html.Div(id="comparison_chart"),
                    ]),
                    # 成绩分析结果
                    html.Div(id="performance_section", className="mb-4", style={"display": "none"}, children=[
                        html.H5("📈 成绩分析"),
                        html.Div(id="performance_results"),
                    ]),
                    # 上线率分析
                    html.Div(id="admission_section", className="mb-4", style={"display": "none"}, children=[
                        html.H5("🎓 上线率分析"),
                        html.Div(id="admission_rate_chart", className="mb-2"),
                        html.Div(id="admission_rate_stats"),
                    ]),
                    # 学科指标表
                    html.Div(id="indicators_section", className="mb-4", style={"display": "none"}, children=[
                        html.H5("📊 学科指标表"),
                        html.Div(id="subject_indicators_table"),
                    ]),
                    # 雷达图
                    html.Div(id="radar_section", style={"display": "none"}, children=[
                        html.H5("🕸️ 班级雷达图"),
                        html.Div(id="class_radar_chart"),
                    ]),
                ]
            ),
        ]
    )


def register_comprehensive_callbacks(app):
    """注册综合分析回调函数"""

    # 添加数据状态调试信息回调
    @app.callback(
        Output("data_status_debug", "children"), [Input("data_store", "data")]
    )
    def update_data_status_debug(data_json):
        """更新数据状态调试信息"""
        if data_json is None:
            return dbc.Alert("未上传数据", color="warning", className="small")

        try:
            from io import StringIO

            df = pd.read_json(StringIO(data_json), orient="split")
            analyzer = ComprehensiveAnalyzer(df)
            admin_cols = analyzer.get_administrative_columns()

            # 创建状态信息
            status_items = [
                f"📊 数据行数: {len(df)}",
                f"📋 数据列数: {len(df.columns)}",
                f"🏢 区县列: {admin_cols.get('county', '未找到')}",
                f"🏫 学校列: {admin_cols.get('school', '未找到')}",
                f"👥 班级列: {admin_cols.get('class', '未找到')}",
            ]

            if admin_cols:
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
                        html.P(
                            "💡 系统将尝试智能识别行政列",
                            className="mb-1 text-info",
                        ),
                    ],
                    color="info",
                    className="small",
                )

        except Exception as e:
            return dbc.Alert(
                f"❌ 数据解析错误: {str(e)}", color="danger", className="small"
            )



    create_comprehensive_analyzer_ui(app)

    # 注意：下拉菜单的更新已移至app.py中的统一处理


# ========================================
# 模块初始化
# ========================================
def initialize_comprehensive_analyzer():
    """初始化增强版综合分析器模块"""
    logger.info("增强版综合分析器模块初始化完成")
    return ComprehensiveAnalyzer
