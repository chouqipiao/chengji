#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标完成统计UI组件
提供目标完成分析的用户界面组件
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

# 预设的目标配置
GOAL_PRESETS = {
    "standard": {
        "name": "标准目标",
        "goals": {
            "undergraduate_safe": {"name": "本科确保目标", "min_score": 450},
            "undergraduate_strive": {"name": "本科力争目标", "min_score": 420},
            "special_control": {"name": "特控目标", "min_score": 520},
        },
    },
    "conservative": {
        "name": "保守目标",
        "goals": {
            "undergraduate_safe": {"name": "本科确保目标", "min_score": 430},
            "undergraduate_strive": {"name": "本科力争目标", "min_score": 400},
            "special_control": {"name": "特控目标", "min_score": 500},
        },
    },
    "aggressive": {
        "name": "进取目标",
        "goals": {
            "undergraduate_safe": {"name": "本科确保目标", "min_score": 470},
            "undergraduate_strive": {"name": "本科力争目标", "min_score": 440},
            "special_control": {"name": "特控目标", "min_score": 540},
        },
    },
}

CHART_TYPES = [
    {"label": "柱状图", "value": "bar"},
    {"label": "饼图", "value": "pie"},
    {"label": "漏斗图", "value": "funnel"},
    {"label": "折线图", "value": "line"},
]

ANALYSIS_LEVELS = [
    {"label": "全区统计", "value": "county"},
    {"label": "学校统计", "value": "school"},
    {"label": "班级统计", "value": "class"},
]


def create_goal_completion_control_panel():
    """
    创建目标完成分析控制面板

    Returns:
        dbc.Card: 控制面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("🎯 目标完成统计分析", className="mb-0"),
                    html.P(
                        "分析学生目标分数的完成情况，支持多层级对比分析",
                        className="text-muted mb-0",
                    ),
                ]
            ),
            dbc.CardBody(
                [
                    # 分数线设置
                    html.Div(
                        [
                            html.H5("📊 分数线设置", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "本科线:",
                                                className="fw-bold",
                                            ),
                                            dbc.Input(
                                                id="undergraduate_line_input",
                                                type="number",
                                                value=450,
                                                min=0,
                                                max=750,
                                                className="mb-3",
                                                placeholder="本科分数线",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "特控线:",
                                                className="fw-bold",
                                            ),
                                            dbc.Input(
                                                id="special_control_line_input",
                                                type="number",
                                                value=520,
                                                min=0,
                                                max=750,
                                                className="mb-3",
                                                placeholder="特控线",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "高分线(可选):",
                                                className="fw-bold",
                                            ),
                                            dbc.Input(
                                                id="high_score_line_input",
                                                type="number",
                                                value=600,
                                                min=0,
                                                max=750,
                                                className="mb-3",
                                                placeholder="高分分数线(可选)",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ]
                            ),
                            dbc.Alert(
                                [
                                    html.P(
                                        "💡 提示：设置分数线后，系统将统计达到各分数线的人数，按区县-学校-班级三个层级展示",
                                        className="mb-0",
                                    )
                                ],
                                color="info",
                                className="mb-3",
                            ),
                        ]
                    ),
                    # 分析设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("目标科目:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="target_subject_dropdown",
                                        placeholder="选择用于分析的目标科目",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("分析层级:", className="fw-bold"),
                                    dcc.Checklist(
                                        id="analysis_level_checklist",
                                        options=ANALYSIS_LEVELS,
                                        value=["county", "school"],
                                        inline=True,
                                        className="mt-2",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # 层级筛选控制
                    html.Div(
                        [
                            dbc.Alert(
                                [
                                    html.P(
                                        "🔍 三级联动筛选：选择区县→学校→班级，动态过滤层级统计数据。可以留空显示该层级全部数据。",
                                        className="mb-0",
                                    )
                                ],
                                color="info",
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("区县筛选（可多选）:", className="fw-bold"),
                                            dcc.Dropdown(
                                                id="county_filter_dropdown",
                                                placeholder="选择区县（可多选，留空显示全部）",
                                                multi=True,
                                                clearable=True,
                                                className="mb-2",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("学校筛选（可多选）:", className="fw-bold"),
                                            dcc.Dropdown(
                                                id="school_filter_dropdown",
                                                placeholder="选择学校（可多选，留空显示全部）",
                                                multi=True,
                                                clearable=True,
                                                className="mb-2",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("班级筛选:", className="fw-bold"),
                                            dcc.Dropdown(
                                                id="class_filter_dropdown",
                                                placeholder="选择班级（可多选，留空显示全部）",
                                                multi=True,
                                                clearable=True,
                                                className="mb-2",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    ),
                    # 可视化设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("图表类型:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="chart_type_dropdown",
                                        options=CHART_TYPES,
                                        value="bar",
                                        placeholder="选择展示图表的类型（柱状/饼图等）",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "显示详细数据:",
                                        className="fw-bold mt-2",
                                    ),
                                    dcc.Checklist(
                                        id="show_details_checklist",
                                        options=[
                                            {
                                                "label": "显示分布详情",
                                                "value": "show_distribution",
                                            },
                                        ],
                                        value=["show_distribution"],
                                        inline=True,
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # 操作按钮
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "开始分析",
                                        id="analyze_goal_btn",
                                        color="primary",
                                        size="lg",
                                        className="w-100",
                                        n_clicks=0,
                                    )
                                ],
                                width=12,
                            ),

                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )


def create_goal_completion_results_panel():
    """
    创建目标完成分析结果面板

    Returns:
        dbc.Card: 结果面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("📊 分析结果", className="mb-0"),
                    html.P(
                        "目标完成统计结果和多维度对比分析",
                        className="text-muted mb-0",
                    ),
                ]
            ),
            dbc.CardBody(
                [
                    # 统计概览
                    html.Div(
                        id="goal_stats_overview",
                        children=[
                            dbc.Alert(
                                '请先配置目标参数并点击"开始分析"按钮',
                                color="info",
                                className="text-center",
                            )
                        ],
                    ),
                    # 图表展示区域
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5(
                                        "完成率图表",
                                        className="text-center mb-3",
                                    ),
                                    dcc.Graph(
                                        id="goal_completion_chart",
                                        style={"height": "400px"},
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.H5(
                                        "层级对比图表",
                                        className="text-center mb-3",
                                    ),
                                    dcc.Graph(
                                        id="hierarchy_comparison_chart",
                                        style={"height": "450px"},
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # 详细数据表格
                    html.Div(
                        id="detailed_results_table",
                        children=[
                            html.H5("详细统计数据", className="mb-3"),
                            html.Div(id="goal_completion_table"),
                        ],
                    ),
                    # 分层统计数据
                    html.Div(
                        id="hierarchy_stats_details",
                        children=[
                            html.H5("分层统计分析", className="mb-3"),
                            html.Div(id="hierarchy_stats_table"),
                        ],
                    ),
                ]
            ),
        ]
    )


def create_goal_comparison_panel():
    """
    创建多目标对比面板

    Returns:
        dbc.Card: 对比面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("📈 多目标对比分析", className="mb-0"),
                    html.P(
                        "多个目标的完成情况对比分析",
                        className="text-muted mb-0",
                    ),
                ]
            ),
            dbc.CardBody(
                [
                    # 对比图表
                    dcc.Graph(id="goal_comparison_chart", style={"height": "500px"}),
                    # 对比表格
                    html.Div(id="goal_comparison_table"),
                ]
            ),
        ]
    )


def create_subject_goal_panel():
    """
    创建多科目目标分析面板

    Returns:
        dbc.Card: 多科目分析面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("📚 多科目目标分析", className="mb-0"),
                    html.P("各科目目标完成情况分析", className="text-muted mb-0"),
                ]
            ),
            dbc.CardBody(
                [
                    # 科目目标设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H6("科目目标设置", className="mb-3"),
                                    html.Div(
                                        id="subject_goals_settings",
                                        children=[
                                            # 动态生成科目目标输入框
                                        ],
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-4",
                    ),
                    # 科目完成率图表
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5(
                                        "各科目完成率对比",
                                        className="text-center mb-3",
                                    ),
                                    dcc.Graph(
                                        id="subject_completion_chart",
                                        style={"height": "400px"},
                                    ),
                                ],
                                width=12,
                            )
                        ]
                    ),
                    # 科目详细统计
                    html.Div(id="subject_detailed_stats"),
                ]
            ),
        ]
    )


def create_custom_goal_settings_panel():
    """
    创建自定义目标设置面板

    Returns:
        html.Div: 自定义目标设置组件
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H6("自定义目标设置", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("目标名称:", size="sm"),
                                            dbc.Input(
                                                id="custom_goal_name",
                                                type="text",
                                                placeholder="输入目标名称",
                                                size="sm",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("目标分数:", size="sm"),
                                            dbc.Input(
                                                id="custom_goal_score",
                                                type="number",
                                                placeholder="输入目标分数",
                                                size="sm",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ]
                            ),
                            dbc.Button(
                                "添加自定义目标",
                                id="add_custom_goal_btn",
                                color="secondary",
                                size="sm",
                                className="mt-2",
                            ),
                            html.Div(id="custom_goals_list", className="mt-2"),
                        ],
                        width=12,
                    )
                ]
            )
        ]
    )


def create_stats_card(title: str, value: str, color: str = "primary", icon: str = "📊"):
    """
    创建统计卡片组件

    Args:
        title: str, 卡片标题
        value: str, 统计值
        color: str, 主题颜色
        icon: str, 图标

    Returns:
        dbc.Card: 统计卡片
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.H3(
                                [icon, " ", value],
                                className=f"text-{color} mb-0",
                            ),
                            html.P(title, className="text-muted mb-0"),
                        ]
                    )
                ]
            )
        ],
        className="text-center",
    )


def create_progress_bar(
    label: str, current: float, total: float, color: str = "primary"
):
    """
    创建进度条组件

    Args:
        label: str, 标签
        current: float, 当前进度值
        total: float, 总值
        color: str, 进度条颜色

    Returns:
        html.Div: 进度条组件
    """
    percentage = (current / total * 100) if total > 0 else 0

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col([html.Strong(f"{label}: {current}/{total}")], width=4),
                    dbc.Col(
                        [
                            dbc.Progress(
                                value=percentage,
                                label=f"{percentage:.1f}%",
                                color=color,
                                striped=True,
                                animated=True,
                            )
                        ],
                        width=8,
                    ),
                ]
            )
        ],
        className="mb-2",
    )


def create_results_table(data: dict, table_id: str = "results-table"):
    """
    创建结果表格组件

    Args:
        data: dict, 表格数据
        table_id: str, 表格ID

    Returns:
        dash_table.DataTable: 数据表格组件
    """
    import dash_table

    if not data:
        return html.Div("暂无数据", className="text-center text-muted")

    # 准备表格数据
    if isinstance(data, dict):
        # 如果是统计数据字典
        table_data = []
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    table_data.append(
                        {
                            "类别": key,
                            "项目": sub_key,
                            "数值": (
                                f"{sub_value:.2f}"
                                if isinstance(sub_value, (int, float))
                                else str(sub_value)
                            ),
                        }
                    )
            else:
                table_data.append(
                    {
                        "类别": "统计",
                        "项目": key,
                        "数值": (
                            f"{value:.2f}"
                            if isinstance(value, (int, float))
                            else str(value)
                        ),
                    }
                )
    else:
        table_data = data

    return dash_table.DataTable(
        id=table_id,
        data=table_data,
        columns=[
            {"name": col, "id": col} for col in table_data[0].keys() if table_data
        ],
        style_cell={
            "textAlign": "center",
            "padding": "10px",
            "fontFamily": "SimHei, sans-serif",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold",
            "fontFamily": "SimHei, sans-serif",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)",
            }
        ],
        page_size=10,
        sort_action="native",
        filter_action="native",
    )