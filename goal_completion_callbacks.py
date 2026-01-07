#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标完成统计回调函数
处理目标完成分析的用户交互和数据处理
"""

from dash import html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import logging

from goal_completion_analyzer import GoalCompletionAnalyzer
from goal_completion_ui import (
    create_stats_card,
    create_progress_bar,
    create_results_table,
)

# 初始化日志
logger = logging.getLogger(__name__)


def register_goal_completion_callbacks(app, data_store):
    """
    注册目标完成分析的回调函数

    Args:
        app: Dash应用实例
        data_store: 数据存储对象
    """

    # 目标设置区域现在直接在UI中定义，使用固定配置

    @app.callback(
        Output("target_subject_dropdown", "options"),
        [Input("analyze_goal_btn", "id")],  # 使用分析按钮触发
    )
    def update_subject_options(_):
        """更新科目选项"""
        try:
            # 从数据存储获取当前数据
            if (
                hasattr(data_store, "get_current_data")
                and data_store.get_current_data() is not None
            ):
                df = data_store.get_current_data()
            else:
                return []

            if df is None:
                return []

            # 获取数值列（排除管理列）
            exclude_keywords = [
                "区县",
                "学校",
                "行政班",
                "考生号",
                "姓名",
                "选科组合",
                "准考证号",
            ]
            numeric_cols = []

            for col in df.select_dtypes(include=["number"]).columns:
                if not any(keyword in col for keyword in exclude_keywords):
                    numeric_cols.append({"label": col, "value": col})

            # 添加"总分"选项（如果存在）
            total_col = None
            for col in df.columns:
                if "总分" in col or "total" in col.lower():
                    total_col = col
                    break

            if total_col:
                numeric_cols.insert(
                    0, {"label": f"{total_col} (推荐)", "value": total_col}
                )

            return numeric_cols

        except Exception as e:
            logger.error(f"更新科目选项失败: {e}")
            return []

    # 移除了多科目分析选项回调，因为UI简化

    # 三级联动菜单初始化回调 - 在数据上传后立即初始化
    @app.callback(
        [
            Output("county_filter_dropdown", "options"),
            Output("school_filter_dropdown", "options"),
            Output("class_filter_dropdown", "options"),
        ],
        [Input("data_store", "data")],
    )
    def init_hierarchy_filters(data_json):
        """初始化三级联动菜单的选项"""
        try:
            # 数据上传后同步到DataStore实例
            if data_json:
                # 通知同步回调已经处理
                pass
            
            # 从DataStore实例获取数据
            if (
                hasattr(data_store, "get_current_data")
                and data_store.get_current_data() is not None
            ):
                df = data_store.get_current_data()
            else:
                return [], [], []

            if df is None:
                return [], [], []

            # 获取区县选项
            county_options = []
            county_col = None
            for col in df.columns:
                if "区县" in col:
                    county_col = col
                    break
            
            if county_col:
                counties = df[county_col].dropna().unique()
                county_options = [{"label": county, "value": county} for county in sorted(counties)]

            # 获取学校选项
            school_options = []
            school_col = None
            for col in df.columns:
                if "学校" in col:
                    school_col = col
                    break
            
            if school_col:
                schools = df[school_col].dropna().unique()
                school_options = [{"label": school, "value": school} for school in sorted(schools)]

            # 获取班级选项
            class_options = []
            class_col = None
            for col in df.columns:
                if "行政班" in col:
                    class_col = col
                    break
                elif "班级" in col and class_col is None:
                    class_col = col
            
            if class_col:
                classes = df[class_col].dropna().unique()
                class_options = [{"label": class_name, "value": class_name} for class_name in sorted(classes)]

            return county_options, school_options, class_options

        except Exception as e:
            logger.error(f"更新层级筛选菜单失败: {e}")
            return [], [], []

    @app.callback(
        Output("school_filter_dropdown", "options", allow_duplicate=True),
        [Input("county_filter_dropdown", "value")],
        prevent_initial_call=True,
    )
    def update_school_options_by_county(selected_county):
        """根据选择的区县更新学校选项"""
        try:
            if (
                hasattr(data_store, "get_current_data")
                and data_store.get_current_data() is not None
            ):
                df = data_store.get_current_data()
            else:
                return []

            if df is None:
                return []

            # 查找区县和学校列
            county_col = None
            school_col = None
            for col in df.columns:
                if "区县" in col:
                    county_col = col
                if "学校" in col:
                    school_col = col

            if county_col and school_col:
                if selected_county:
                    # 支持多选：如果是列表或元组，使用 isin 筛选；否则按单个值筛选
                    if isinstance(selected_county, (list, tuple, set)):
                        filtered_df = df[df[county_col].isin(selected_county)]
                    else:
                        filtered_df = df[df[county_col] == selected_county]
                    schools = filtered_df[school_col].dropna().unique()
                else:
                    # 没有选择区县，显示所有学校
                    schools = df[school_col].dropna().unique()
                return [{"label": school, "value": school} for school in sorted(schools)]

            return []

        except Exception as e:
            logger.error(f"更新学校选项失败: {e}")
            return []

    @app.callback(
        Output("class_filter_dropdown", "options", allow_duplicate=True),
        [Input("school_filter_dropdown", "value")],
        prevent_initial_call=True,
    )
    def update_class_options_by_school(selected_school):
        """根据选择的学校更新班级选项"""
        try:
            if (
                hasattr(data_store, "get_current_data")
                and data_store.get_current_data() is not None
            ):
                df = data_store.get_current_data()
            else:
                return []

            if df is None:
                return []

            # 查找学校和班级列
            school_col = None
            class_col = None
            for col in df.columns:
                if "学校" in col:
                    school_col = col
                if "行政班" in col:
                    class_col = col
                elif "班级" in col and class_col is None:
                    class_col = col

            if school_col and class_col:
                if selected_school:
                    # 支持多选：如果是列表或元组，使用 isin 筛选；否则按单个值筛选
                    if isinstance(selected_school, (list, tuple, set)):
                        filtered_df = df[df[school_col].isin(selected_school)]
                    else:
                        filtered_df = df[df[school_col] == selected_school]
                    classes = filtered_df[class_col].dropna().unique()
                else:
                    # 没有选择学校，显示所有班级
                    classes = df[class_col].dropna().unique()
                return [{"label": class_name, "value": class_name} for class_name in sorted(classes)]

            return []

        except Exception as e:
            logger.error(f"更新班级选项失败: {e}")
            return []

    # 筛选条件变化时更新层级统计表格
    @app.callback(
        Output("hierarchy_stats_details", "children", allow_duplicate=True),
        [
            Input("county_filter_dropdown", "value"),
            Input("school_filter_dropdown", "value"),
            Input("class_filter_dropdown", "value"),
        ],
        [
            State("analyze_goal_btn", "n_clicks"),
            State("show_details_checklist", "value"),
        ],
        prevent_initial_call=True,
    )
    def update_hierarchy_table_by_filters(
        selected_county, selected_school, selected_class, n_clicks, show_details
    ):
        """根据筛选条件更新层级统计表格"""
        if not n_clicks or n_clicks == 0:
            return html.Div()

        try:
            # 从分析器获取存储的结果
            if hasattr(data_store, 'get_analysis_results') and hasattr(data_store, 'get_analyzer'):
                all_results = data_store.get_analysis_results('goal_completion')
                if not all_results:
                    return html.Div("暂无分析数据", className="text-center text-muted")
            else:
                return html.Div("暂无分析数据", className="text-center text-muted")

            # 处理详细数据显示选项
            if not show_details:
                show_details = []

            # 创建筛选条件
            filter_conditions = {
                "county": selected_county,
                "school": selected_school,
                "class": selected_class,
            }

            # 创建筛选后的层级统计表格
            from goal_completion_ui import create_results_table
            hierarchy_table = create_multiple_score_lines_hierarchy_table(
                all_results, filter_conditions
            )
            
            return html.Div([
                html.H5("分层统计分析", className="mb-3"),
                hierarchy_table,
            ])

        except Exception as e:
            logger.error(f"更新层级统计表格失败: {e}")
            return html.Div(f"更新失败: {str(e)}", className="text-danger")

    @app.callback(
        [
            Output("goal_stats_overview", "children"),
            Output("goal_completion_chart", "figure"),
            Output("hierarchy_comparison_chart", "figure"),
            Output("detailed_results_table", "children"),
            Output("hierarchy_stats_details", "children", allow_duplicate=True),
        ],
        [Input("analyze_goal_btn", "n_clicks")],
        [
            State("target_subject_dropdown", "value"),
            State("analysis_level_checklist", "value"),
            State("chart_type_dropdown", "value"),
            State("show_details_checklist", "value"),
            State("county_filter_dropdown", "value"),
            State("school_filter_dropdown", "value"),
            State("class_filter_dropdown", "value"),
            State("undergraduate_line_input", "value"),
            State("special_control_line_input", "value"),
            State("high_score_line_input", "value"),
        ],
        prevent_initial_call=True,
    )
    def analyze_score_line_completion(
        n_clicks,
        target_subject,
        analysis_levels,
        chart_type,
        show_details,
        selected_county,
        selected_school,
        selected_class,
        undergraduate_score,
        special_control_score,
        high_score,
    ):
        """执行分数线达标分析"""

        if not n_clicks or n_clicks == 0:
            return (
                html.Div(
                    "请配置目标参数并点击分析",
                    className="text-center text-muted",
                ),
                {},
                {},
                html.Div(),
                html.Div(),
            )

        # 从输入框获取自定义分数线，设置默认值
        undergraduate_score = undergraduate_score or 450
        special_control_score = special_control_score or 520
        high_score = high_score or 600

        try:
            # 获取数据
            if (
                hasattr(data_store, "get_current_data")
                and data_store.get_current_data() is not None
            ):
                df = data_store.get_current_data()
            else:
                error_msg = dbc.Alert("未找到数据，请先上传数据文件", color="danger")
                return error_msg, {"data": [], "layout": {}}, {}, html.Div(), html.Div()

            if df is None:
                error_msg = dbc.Alert("未找到数据，请先上传数据文件", color="danger")
                return error_msg, {"data": [], "layout": {}}, {}, html.Div(), html.Div()

            # 初始化分析器
            analyzer = GoalCompletionAnalyzer(df)
            # 将分析器存储到数据存储中
            data_store.goal_completion_analyzer = analyzer

            # 设置自定义分数线配置
            custom_lines = {
                "undergraduate": {
                    "name": "本科线",
                    "min_score": undergraduate_score,
                },
                "special_control": {
                    "name": "特控线",
                    "min_score": special_control_score,
                },
                "high_score": {
                    "name": "高分线",
                    "min_score": high_score,
                },
            }
            analyzer.set_score_line_config(custom_lines)

            # 根据用户选择的分析层级过滤结果
            if not analysis_levels:
                analysis_levels = ["county", "school"]  # 默认值
            
            # 执行多分数线分析（分析所有分数线）
            all_results = {}
            for line_type in ["undergraduate", "special_control", "high_score"]:
                line_results = analyzer.analyze_score_line_completion(
                    line_type, target_subject, analysis_levels
                )
                if line_results:
                    all_results[line_type] = line_results

            if not all_results:
                error_msg = dbc.Alert("分析失败，请检查参数设置", color="danger")
                return error_msg, {"data": [], "layout": {}}, {}, html.Div(), html.Div()

            # 创建多分数线分析结果组件
            overview = create_multiple_score_lines_analysis_overview(
                all_results, custom_lines
            )

            # 生成对比图表
            completion_chart = analyzer.create_multiple_score_lines_comparison_chart(
                all_results, chart_type
            )
            hierarchy_chart = (
                analyzer.create_hierarchy_comparison_chart_for_multiple_score_lines(
                    all_results
                )
            )

            # 处理详细数据显示选项
            if not show_details:
                show_details = []
            
            show_distribution = "show_distribution" in show_details
            
            # 创建综合数据表格（根据用户选择控制显示内容）
            details_table = create_multiple_score_lines_results_table(all_results, show_distribution)
            
            # 创建层级统计表格，应用筛选条件
            filter_conditions = {
                "county": selected_county,
                "school": selected_school,
                "class": selected_class,
            }
            hierarchy_table = create_multiple_score_lines_hierarchy_table(all_results, filter_conditions)

            # 存储分析结果到数据存储
            data_store.store_analysis_results('goal_completion', all_results)

            return (
                overview,
                completion_chart,
                hierarchy_chart,
                details_table,
                hierarchy_table,
            )

        except Exception as e:
            logger.error(f"目标完成分析失败: {e}")
            error_msg = dbc.Alert(f"分析过程出现错误: {str(e)}", color="danger")
            return error_msg, {"data": [], "layout": {}}, {}, html.Div(), html.Div()




def create_single_goal_overview(results: dict) -> html.Div:
    """创建单目标分析概览"""
    if "basic_stats" not in results:
        return html.Div("无有效数据", className="text-center text-muted")

    basic = results["basic_stats"]

    # 确定完成率颜色
    rate_color = (
        "success"
        if basic["reach_rate"] >= 50
        else "warning" if basic["reach_rate"] >= 30 else "danger"
    )

    # 创建统计卡片
    cards = dbc.Row(
        [
            dbc.Col(
                [
                    create_stats_card(
                        "分数线达标率",
                        f"{basic['reach_rate']:.1f}%",
                        rate_color,
                        "🎯",
                    )
                ],
                width=3,
            ),
            dbc.Col(
                [
                    create_stats_card(
                        "完成人数",
                        f"{basic['completed_students']}",
                        "info",
                        "👥",
                    )
                ],
                width=3,
            ),
            dbc.Col(
                [
                    create_stats_card(
                        "平均分", f"{basic['avg_score']:.1f}", "primary", "📊"
                    )
                ],
                width=3,
            ),
            dbc.Col(
                [
                    create_stats_card(
                        "与线差距",
                        f"{basic['score_gap_to_line']:.1f}",
                        (
                            "secondary"
                            if basic["score_gap_to_line"] <= 0
                            else "warning"
                        ),
                        "📏",
                    )
                ],
                width=3,
            ),
        ],
        className="mb-4",
    )

    # 添加进度条
    progress = html.Div(
        [
            html.H6("完成进度", className="mb-3"),
            create_progress_bar(
                f"{basic['goal_name']}",
                basic["completed_students"],
                basic["total_students"],
                rate_color,
            ),
        ]
    )

    return html.Div([cards, progress])


def create_multiple_goals_overview(results: dict) -> html.Div:
    """创建多目标对比概览"""
    if "comparison_summary" not in results:
        return html.Div("无有效对比数据", className="text-center text-muted")

    summary = results["comparison_summary"]

    # 创建统计卡片
    cards = dbc.Row(
        [
            dbc.Col(
                [
                    create_stats_card(
                        "最高达标率",
                        f"{summary['highest_reach_rate']:.1f}%",
                        "success",
                        "🏆",
                    )
                ],
                width=4,
            ),
            dbc.Col(
                [
                    create_stats_card(
                        "最低达标率",
                        f"{summary['lowest_reach_rate']:.1f}%",
                        "danger",
                        "📉",
                    )
                ],
                width=4,
            ),
            dbc.Col(
                [
                    create_stats_card(
                        "对比目标数",
                        f"{len(results) - 1}",  # 减去comparison_summary
                        "info",
                        "📊",
                    )
                ],
                width=4,
            ),
        ],
        className="mb-4",
    )

    return cards


def create_hierarchy_stats_table(hierarchy_stats: dict) -> html.Div:
    """创建层级统计表格"""
    if not hierarchy_stats:
        return html.Div("暂无层级统计数据", className="text-center text-muted")

    table_data = []

    for level, groups in hierarchy_stats.items():
        for group_name, stats in groups.items():
            table_data.append(
                {
                    "层级": level,
                    "分组": group_name,
                    "总人数": stats["total_count"],
                    "达标人数": stats["reached_count"],
                    "达标率": f"{stats['reach_rate']:.2f}%",
                    "平均分": f"{stats['avg_score']:.2f}",
                    "最高分": f"{stats['max_score']:.2f}",
                    "最低分": f"{stats['min_score']:.2f}",
                    "与线差距": f"{stats['score_gap_to_line']:.2f}",
                }
            )

    return create_results_table(table_data, "hierarchy_stats_table")


def create_comparison_chart(results: dict, chart_type: str) -> dict:
    """创建对比图表"""
    import plotly.graph_objects as go

    if "comparison_summary" not in results:
        return None

    trend = results["comparison_summary"]["goal_completion_trend"]

    if chart_type == "bar":
        fig = go.Figure(
            data=[
                go.Bar(
                    x=list(trend.keys()),
                    y=list(trend.values()),
                    text=[f"{v:.1f}%" for v in trend.values()],
                    textposition="auto",
                    marker_color=["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
                )
            ]
        )

    elif chart_type == "pie":
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=list(trend.keys()),
                    values=list(trend.values()),
                    textinfo="label+percent",
                    hole=0.3,
                )
            ]
        )

    else:
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=list(trend.keys()),
                    y=list(trend.values()),
                    mode="lines+markers",
                    line=dict(width=3),
                    marker=dict(size=10),
                )
            ]
        )

    fig.update_layout(title="多目标完成率对比", yaxis_title="完成率 (%)", height=400)

    return fig


def create_comparison_table(results: dict) -> html.Div:
    """创建对比表格"""
    if "comparison_summary" not in results:
        return html.Div("暂无对比数据", className="text-center text-muted")

    table_data = []

    for goal_type, stats in results.items():
        if goal_type == "comparison_summary":
            continue

        table_data.append(
            {
                "分数线类型": stats["line_name"],
                "分数线": stats["line_score"],
                "总人数": stats["total_students"],
                "达标人数": stats["reached_students"],
                "达标率": f"{stats['reach_rate']:.2f}%",
                "平均分": f"{stats['avg_score']:.2f}",
                "最高分": f"{stats['max_score']:.2f}",
                "最低分": f"{stats['min_score']:.2f}",
                "与线差距": f"{stats['score_gap_to_line']:.2f}",
            }
        )

    return create_results_table(table_data, "comparison_table")





def create_multiple_score_lines_analysis_overview(
    all_results: dict, custom_lines: dict
) -> html.Div:
    """创建多分数线分析概览"""
    if not all_results:
        return html.Div("无有效数据", className="text-center text-muted")

    # 创建统计卡片行
    cards = []

    for line_type, line_config in custom_lines.items():
        if line_type in all_results:
            results = all_results[line_type]
            basic_stats = results.get("basic_stats", {})

            # 确定达标率颜色
            reach_rate = basic_stats.get("reach_rate", 0)
            rate_color = (
                "success"
                if reach_rate >= 50
                else "warning" if reach_rate >= 30 else "danger"
            )

            cards.append(
                dbc.Col(
                    [
                        create_stats_card(
                            f"{line_config['name']}达标人数",
                            f"{basic_stats.get('reached_students', 0)}人",
                            rate_color,
                            "🎯",
                        )
                    ],
                    width=4,
                )
            )

    return html.Div(
        [
            html.H5("📊 各分数线达标情况概览", className="mb-3"),
            dbc.Row(cards, className="mb-4"),
            dbc.Alert(
                [
                    html.P(
                        "💡 以上显示了各分数线的达标人数情况，系统将按区县-学校-班级三个层级进行详细统计。",
                        className="mb-0",
                    )
                ],
                color="info",
            ),
        ]
    )


def create_multiple_score_lines_results_table(all_results: dict, show_distribution: bool = False) -> html.Div:
    """创建多分数线结果表格"""
    if not all_results:
        return html.Div("暂无数据", className="text-center text-muted")

    table_data = []

    for line_type, results in all_results.items():
        basic_stats = results.get("basic_stats", {})
        
        # 基础统计信息
        row_data = {
            "分数线类型": basic_stats.get("line_name", line_type),
            "分数线": basic_stats.get("target_score", 0),
            "总人数": basic_stats.get("total_students", 0),
            "达标人数": basic_stats.get("reached_students", 0),
            "达标率": f"{basic_stats.get('reach_rate', 0):.2f}%",
            "平均分": f"{basic_stats.get('avg_score', 0):.2f}",
            "与线差距": f"{basic_stats.get('score_gap_to_line', 0):.2f}",
        }
        
        # 根据用户选择添加详细信息
        if show_distribution:
            row_data.update({
                "最高分": f"{basic_stats.get('max_score', 0):.2f}",
                "最低分": f"{basic_stats.get('min_score', 0):.2f}",
            })
        
        table_data.append(row_data)

    return create_results_table(table_data, "multiple_score_lines_results_table")


def create_multiple_score_lines_hierarchy_table(all_results: dict, filter_conditions: dict = None) -> html.Div:
    """创建多分数线层级统计表格"""
    if not all_results:
        return html.Div("暂无层级统计数据", className="text-center text-muted")

    if filter_conditions is None:
        filter_conditions = {}

    table_data = []

    for line_type, results in all_results.items():
        hierarchy_stats = results.get("hierarchy_stats", {})
        line_name = results.get("basic_stats", {}).get("line_name", line_type)

        for level, groups in hierarchy_stats.items():
            for group_name, stats in groups.items():
                # 应用筛选条件（支持多选的 county / school / class）
                if filter_conditions:
                    # 区县筛选（支持单值或多值）
                    if filter_conditions.get("county") and level == "county":
                        selected_counties = filter_conditions["county"]
                        if isinstance(selected_counties, (list, tuple, set)):
                            if group_name not in selected_counties:
                                continue
                        else:
                            if group_name != selected_counties:
                                continue
                    # 学校筛选（支持单值或多值）
                    if filter_conditions.get("school") and level == "school":
                        selected_schools = filter_conditions["school"]
                        if isinstance(selected_schools, (list, tuple, set)):
                            if group_name not in selected_schools:
                                continue
                        else:
                            if group_name != selected_schools:
                                continue
                    # 班级筛选（支持多选或单值）
                    if filter_conditions.get("class") and level == "class":
                        selected_classes = filter_conditions["class"]
                        if isinstance(selected_classes, str):
                            selected_classes = [selected_classes]
                        if group_name not in selected_classes:
                            continue
                
                # 将level转换为中文显示
                level_display = {"county": "区县", "school": "学校", "class": "班级"}.get(level, level)
                
                # 基础统计信息
                row_data = {
                    "分数线类型": line_name,
                    "层级": level_display,
                    "分组": group_name,
                    "总人数": stats.get("total_count", 0),
                    "达标人数": stats.get("reached_count", 0),
                    "达标率": f"{stats.get('reach_rate', 0):.2f}%",
                    "平均分": f"{stats.get('avg_score', 0):.2f}",
                    "与线差距": f"{stats.get('score_gap_to_line', 0):.2f}",
                }
                
                table_data.append(row_data)

    return create_results_table(table_data, "multiple_score_lines_hierarchy_table")
