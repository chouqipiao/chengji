#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有效群体统计分析回调函数
处理UI交互和数据分析逻辑
"""

import dash
from dash import Input, Output, State, html
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime
import logging

from effective_group_analyzer import EffectiveGroupAnalyzer
from effective_group_ui import create_school_subject_comparison_content

logger = logging.getLogger(__name__)


def register_effective_group_callbacks(app, data_store):
    """
    注册有效群体统计分析的回调函数

    Args:
        app: Dash应用实例
        data_store: 数据存储对象
    """

    # 更新列选择选项
    @app.callback(
        [
            Output("effective_group_total_column", "options"),
            Output("effective_group_comparison_subjects", "options"),
        ],
        [Input("data_store", "data")],
    )
    def update_column_options(data_json):
        """根据当前数据更新列选择选项"""
        try:
            if data_json is not None:
                df = pd.read_json(data_json, orient="split")
                columns = df.columns.tolist()

                # 生成总分列选项（包含可能的总分列名）
                total_options = []
                for col in columns:
                    if any(
                        candidate in col.lower()
                        for candidate in ["总分", "total", "合计"]
                    ):
                        total_options.append({"label": col, "value": col})
                if not total_options:
                    total_options = [{"label": col, "value": col} for col in columns]

                # 生成学科列选项（排除明显非学科列，但包含总分作为对比选项）
                subject_options = []
                exclude_cols = [
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
                ]

                # 首先添加总分作为对比选项
                for col in columns:
                    if any(
                        candidate in col.lower()
                        for candidate in ["总分", "total", "合计"]
                    ):
                        subject_options.append({"label": f"{col} (总分)", "value": col})

                # 然后添加其他学科列
                for col in columns:
                    if (
                        col not in exclude_cols
                        and not any(exclude in col for exclude in ["总分", "total"])
                        and not col.endswith("等级")
                    ):
                        subject_options.append({"label": col, "value": col})

                return total_options, subject_options
            else:
                return [], []

        except Exception as e:
            logger.error(f"更新列选项失败: {e}")
            return [], []

    # 更新当前分数线显示
    @app.callback(
        Output("effective_group_current_thresholds", "children"),
        [
            Input("effective_group_undergraduate_threshold", "value"),
            Input("effective_group_special_threshold", "value"),
            Input("effective_group_custom_thresholds_store", "data"),
        ],
    )
    def update_current_thresholds(undergraduate, special, custom_thresholds):
        """更新当前分数线显示"""
        thresholds = []

        if undergraduate is not None:
            thresholds.append(("本科线", undergraduate, "primary"))
        if special is not None:
            thresholds.append(("特控线", special, "primary"))

        # 添加自定义分数线
        if custom_thresholds:
            for thresh in custom_thresholds:
                thresholds.append((thresh["name"], thresh["score"], "success"))

        if thresholds:
            return html.Div(
                [
                    html.Small("当前设置: ", className="text-muted"),
                    html.Div(
                        [
                            dbc.Badge(
                                f"{name}: {score}分",
                                color=color,
                                className="me-2 mb-2",
                            )
                            for name, score, color in thresholds
                        ]
                    ),
                ]
            )
        else:
            return html.Div(html.Small("尚未设置分数线", className="text-muted"))

    # 执行分析
    @app.callback(
        [
            Output("effective_group_status_alert", "children"),
            Output("effective_group_status_alert", "color"),
            Output("effective_group_summary", "children"),
            Output("effective_group_tab_content", "children"),
        ],
        [Input("effective_group_analyze_btn", "n_clicks")],
        [
            State("effective_group_undergraduate_threshold", "value"),
            State("effective_group_special_threshold", "value"),
            State("effective_group_total_column", "value"),
            State("effective_group_comparison_subjects", "value"),
            State("effective_group_custom_thresholds_store", "data"),
        ],
    )
    def perform_analysis(
        n_clicks,
        undergraduate,
        special,
        total_column,
        comparison_subjects,
        custom_thresholds,
    ):
        """执行有效群体统计分析"""

        # 添加调试日志
        logger.info(f"[DEBUG] 点击次数: {n_clicks}")
        logger.info(f"[DEBUG] 本科线: {undergraduate}")
        logger.info(f"[DEBUG] 特控线: {special}")
        logger.info(f"[DEBUG] 总分列: {total_column}")
        logger.info(f"[DEBUG] 对比学科: {comparison_subjects}")
        logger.info(f"[DEBUG] 自定义分数线: {custom_thresholds}")

        # 检查是否点击了分析按钮
        if n_clicks is None:
            return "请先设置参数并点击'开始分析'", "info", "", ""

        # 验证输入参数
        if not total_column:
            return "请选择总分列", "warning", "", ""

        if undergraduate is None and special is None:
            return "请至少设置一个分数线", "warning", "", ""

        try:
            # 获取数据
            logger.info(f"[DEBUG] 检查data_store: {hasattr(data_store, 'get_current_data')}")
            if hasattr(data_store, 'get_current_data'):
                current_data = data_store.get_current_data()
                logger.info(f"[DEBUG] 当前数据是否为None: {current_data is None}")
                if current_data is not None:
                    logger.info(f"[DEBUG] 数据形状: {current_data.shape}")
            
            if (
                not hasattr(data_store, "get_current_data")
                or data_store.get_current_data() is None
            ):
                return "无可用数据，请先上传数据文件", "danger", "", ""

            df = data_store.get_current_data()

            # 自动识别学科列（包含总分列作为分析对象）
            columns = df.columns.tolist()
            subject_columns = []
            exclude_cols = [
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
            ]

            # 首先添加总分列
            for col in columns:
                if any(
                    candidate in col.lower() for candidate in ["总分", "total", "合计"]
                ):
                    subject_columns.append(col)

            # 然后添加其他学科列
            for col in columns:
                if (
                    col not in exclude_cols
                    and not any(exclude in col for exclude in ["总分", "total"])
                    and not col.endswith("等级")
                ):
                    subject_columns.append(col)

            if not subject_columns:
                return "无法自动识别学科列", "warning", "", ""

            # 创建分析器
            analyzer = EffectiveGroupAnalyzer(df)

            # 设置分数线
            thresholds = {}
            if undergraduate is not None:
                thresholds["本科线"] = undergraduate
            if special is not None:
                thresholds["特控线"] = special

            # 添加自定义分数线
            if custom_thresholds:
                for custom_thresh in custom_thresholds:
                    thresholds[custom_thresh["name"]] = custom_thresh["score"]

            analyzer.set_score_thresholds(thresholds)

            # 执行分析
            results = analyzer.perform_comprehensive_analysis(
                total_column=total_column, subject_columns=subject_columns
            )

            if not results:
                return (
                    "分析完成但无有效结果，请检查分数线设置",
                    "warning",
                    "",
                    "",
                )

            # 生成分析摘要
            summary = html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H6("📊 分析概况", className="text-primary"),
                                    html.P(f"分析群体数量: {len(results)}"),
                                    html.P(f"总分列: {total_column}"),
                                    html.P(f"学科数量: {len(subject_columns)}"),
                                    html.P(
                                        f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    html.H6("👥 群体规模", className="text-primary"),
                                    *[
                                        html.P(f"{name}: {data['群体人数']}人")
                                        for name, data in results.items()
                                    ],
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    html.H6(
                                        "🎯 分数线设置",
                                        className="text-primary",
                                    ),
                                    *[
                                        html.P(f"{name}: {data['分数线']}分")
                                        for name, data in results.items()
                                    ],
                                ],
                                width=4,
                            ),
                        ]
                    )
                ]
            )

            # 生成学校学科对比内容
            tab_content = html.Div(
                create_school_subject_comparison_content(results, comparison_subjects)
            )

            # 将分析结果存储到会话状态
            return (
                f"分析完成！共分析{len(results)}个有效群体",
                "success",
                summary,
                tab_content,
            )

        except Exception as e:
            logger.error(f"有效群体分析失败: {e}")
            return f"分析失败: {str(e)}", "danger", "", ""

    # 处理标签页切换 - 临时禁用以避免回调冲突
    # @app.callback(
    #     Output("effective_group_tab_content", "children", allow_duplicate=True),
    #     [Input("effective_group_results_tabs", "active_tab")],
    #     [
    #         State("effective_group_analyze_btn", "n_clicks"),
    #         State("effective_group_undergraduate_threshold", "value"),
    #         State("effective_group_special_threshold", "value"),
    #         State("effective_group_total_column", "value"),
    #         State("effective_group_comparison_subjects", "value"),
    #     ],
    #     prevent_initial_call=True,
    # )
    # def update_tab_content(
    #     active_tab,
    #     n_clicks,
    #     undergraduate,
    #     special,
    #     total_column,
    #     comparison_subjects,
    # ):
        """根据选择的标签页更新内容"""
        pass  # 临时禁用，避免回调冲突

    # 自定义分数线管理功能（合并添加和清空）
    @app.callback(
        Output(
            "effective_group_custom_thresholds_store",
            "data",
            allow_duplicate=True,
        ),
        [
            Input("effective_group_add_threshold", "n_clicks"),
            Input("effective_group_clear_thresholds", "n_clicks"),
        ],
        [
            State("effective_group_custom_thresholds_store", "data"),
            State("effective_group_custom_name", "value"),
            State("effective_group_custom_score", "value"),
        ],
        prevent_initial_call=True,
    )
    def manage_custom_thresholds(
        add_clicks, clear_clicks, current_thresholds, custom_name, custom_score
    ):
        """管理自定义分数线（添加和清空）"""
        ctx = dash.callback_context

        if not ctx.triggered:
            return dash.no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # 确保current_thresholds不为None
        if current_thresholds is None:
            current_thresholds = []

        # 处理添加分数线
        if trigger_id == "effective_group_add_threshold" and add_clicks:
            if custom_name and custom_score is not None:
                # 验证分数范围
                if custom_score < 0 or custom_score > 750:
                    return current_thresholds

                # 检查是否已存在同名分数线
                if current_thresholds:
                    for thresh in current_thresholds:
                        if thresh["name"] == custom_name:
                            return current_thresholds

                # 添加新的自定义分数线
                updated_thresholds = (
                    current_thresholds.copy() if current_thresholds else []
                )
                updated_thresholds.append({"name": custom_name, "score": custom_score})

                return updated_thresholds

        # 处理清空分数线
        elif trigger_id == "effective_group_clear_thresholds" and clear_clicks:
            return []

        return dash.no_update

    def create_threshold_display(custom_thresholds):
        """创建分数线显示组件"""
        threshold_elements = []

        if custom_thresholds:
            for thresh in custom_thresholds:
                threshold_elements.append(
                    dbc.Badge(
                        f"{thresh['name']}: {thresh['score']}分",
                        color="success",
                        className="me-2 mb-2",
                    )
                )

        return html.Div(threshold_elements) if threshold_elements else html.Div()

    logger.info("有效群体统计分析回调函数注册完成")
