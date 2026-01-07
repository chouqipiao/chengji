#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有效群体统计分析UI组件
创建控制面板和结果展示界面
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from typing import Any
import logging

# 类型提示：由于外部库类型存根不完整，使用 type: ignore 注释抑制相关错误

logger = logging.getLogger(__name__)


def create_effective_group_control_panel() -> dbc.Card:
    """
    创建有效群体统计分析控制面板

    Returns:
        dbc.Card: 控制面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("📊 有效群体统计分析", className="mb-0"),
                    html.P(
                        "基于自定义分数线对学生群体进行多维度分析",
                        className="text-muted mb-0",
                    ),
                ]
            ),
            dbc.CardBody(
                [
                    # 分数线设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label(
                                        "分数线设置",
                                        className="fw-bold text-primary",
                                    ),
                                    html.P(
                                        "设置不同类型分数线的标准分",
                                        className="text-muted small",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    # 预设分数线
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("本科线:"),
                                    dbc.Input(
                                        id="effective_group_undergraduate_threshold",
                                        type="number",
                                        value=450,
                                        min=0,
                                        max=750,
                                        placeholder="本科线（总分）",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("特控线:"),
                                    dbc.Input(
                                        id="effective_group_special_threshold",
                                        type="number",
                                        value=520,
                                        min=0,
                                        max=750,
                                        placeholder="特控线",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # 自定义分数线
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("添加自定义分数线:"),
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id="effective_group_custom_name",
                                                type="text",
                                                placeholder="自定义分数线名称，例如 本科线",
                                            ),
                                            dbc.Input(
                                                id="effective_group_custom_score",
                                                type="number",
                                                min=0,
                                                max=750,
                                                placeholder="自定义分数线的数值",
                                            ),
                                            dbc.Button(
                                                "添加",
                                                id="effective_group_add_threshold",
                                                color="outline-primary",
                                                size="sm",
                                            ),
                                            dbc.Button(
                                                "清空",
                                                id="effective_group_clear_thresholds",
                                                color="outline-danger",
                                                size="sm",
                                            ),
                                        ]
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    # 当前分数线显示
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label("当前分数线设置:", className="fw-bold"),
                                    html.Div(
                                        id="effective_group_current_thresholds",
                                        className="border rounded p-2 bg-light",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    html.Hr(),
                    # 数据列设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label(
                                        "数据列设置",
                                        className="fw-bold text-primary",
                                    ),
                                    html.P(
                                        "选择总分列（学科列将自动识别）",
                                        className="text-muted small",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("总分列:"),
                                    dcc.Dropdown(
                                        id="effective_group_total_column",
                                        options=[],
                                        value=None,
                                        clearable=False,
                                        placeholder="选择代表总分的列",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    # 学校学科对比设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label(
                                        "学校学科对比设置",
                                        className="fw-bold text-primary",
                                    ),
                                    html.P(
                                        "选择要对比的学科，动态生成学校学科对比表格",
                                        className="text-muted small",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("选择对比学科:"),
                                    dcc.Dropdown(
                                        id="effective_group_comparison_subjects",
                                        options=[],
                                        value=[],
                                        multi=True,
                                        placeholder="选择多个学科用于学校学科对比",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-4",
                    ),
                    # 分析按钮
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-bar-chart me-2"),
                                            "开始分析",
                                        ],
                                        id="effective_group_analyze_btn",
                                        color="primary",
                                        size="lg",
                                        className="w-100",
                                    )
                                ],
                                width=12,
                            )
                        ]
                    ),
                ]
            ),
        ],
        className="shadow-sm",
    )


def create_effective_group_results_panel() -> dbc.Card:
    """
    创建有效群体统计分析结果展示面板

    Returns:
        dbc.Card: 结果展示面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("📈 分析结果", className="mb-0"),
                    html.P("有效群体统计分析结果展示", className="text-muted mb-0"),
                ]
            ),
            dbc.CardBody(
                [
                    # 分析状态
                    dbc.Alert(
                        "请先设置参数并点击'开始分析'",
                        id="effective_group_status_alert",
                        color="info",
                        className="mb-3",
                    ),
                    # 结果摘要
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5("分析摘要", className="text-primary"),
                                    html.Div(id="effective_group_summary"),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-4",
                    ),
                    # 学校学科对比标签页
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="学校学科对比",
                                tab_id="school_subject_comparison",
                            )
                        ],
                        id="effective_group_results_tabs",
                        active_tab="school_subject_comparison",
                        className="mb-3",
                    ),
                    # 标签页内容
                    html.Div(id="effective_group_tab_content"),
                ]
            ),
        ],
        className="shadow-sm",
    )


def create_group_tables_content(
    analysis_results: dict[str, Any],
) -> list[dbc.Card]:
    """
    创建群体统计表格内容

    Args:
        analysis_results: 分析结果

    Returns:
        List[dbc.Card]: 表格卡片列表
    """
    cards = []

    for group_name, group_data in analysis_results.items():
        # 创建基础信息表格
        basic_data = [
            {"指标": "群体名称", "数值": group_data["群体名称"], "备注": ""},
            {
                "指标": "分数线",
                "数值": group_data["分数线"],
                "备注": "最低要求分",
            },
            {
                "指标": "群体人数",
                "数值": group_data["群体人数"],
                "备注": "达到线人数",
            },
            {
                "指标": "总分平均分",
                "数值": group_data["总分平均分"],
                "备注": "",
            },
            {
                "指标": "总分最高分",
                "数值": group_data["总分最高分"],
                "备注": "",
            },
            {
                "指标": "总分最低分",
                "数值": group_data["总分最低分"],
                "备注": "",
            },
            {
                "指标": "总分标准差",
                "数值": group_data["总分标准差"],
                "备注": "",
            },
        ]

        # 创建学科统计表格
        subject_data = []
        for subject, avg_score in group_data["学科平均分"].items():
            deviation_rate = group_data["学科离均率"].get(subject, 0)
            subject_data.append(
                {
                    "学科": subject,
                    "平均分": avg_score,
                    "离均率(%)": deviation_rate,
                }
            )

        # 创建排名表格
        ranking_data = group_data.get("学科排名", [])

        card = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H5(
                            f"{group_name}群体情况统计",
                            className="text-primary mb-0",
                        )
                    ]
                ),
                dbc.CardBody(
                    [
                        # 基础信息表格
                        html.H6("📋 基础信息", className="text-secondary"),
                        dash_table.DataTable(
                            id=f"basic_table_{group_name}",
                            columns=[
                                {"name": "指标", "id": "指标"},
                                {"name": "数值", "id": "数值"},
                                {"name": "备注", "id": "备注"},
                            ],
                            data=basic_data,  # type: ignore
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                            },
                            style_header={"fontWeight": "bold"},
                            style_data_conditional=[  # type: ignore
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "rgb(248, 248, 248)",
                                    "color": "black"
                                }
                            ],
                        ),
                        html.Hr(),
                        # 学科统计表格
                        html.H6("📊 学科统计", className="text-secondary"),
                        dash_table.DataTable(
                            id=f"subject_table_{group_name}",
                            columns=[
                                {"name": "学科", "id": "学科"},
                                {"name": "平均分", "id": "平均分"},
                                {"name": "离均率(%)", "id": "离均率(%)"},
                            ],
                            data=subject_data,  # type: ignore
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                            },
                            style_header={"fontWeight": "bold"},
                            style_data_conditional=[  # type: ignore
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "rgb(248, 248, 248)",
                                    "color": "black"
                                }
                            ],
                        ),
                        html.Hr(),
                        # 学科排名表格
                        html.H6("🏆 学科排名", className="text-secondary"),
                        dash_table.DataTable(
                            id=f"ranking_table_{group_name}",
                            columns=[
                                {"name": "排名", "id": "排名"},
                                {"name": "学科", "id": "学科"},
                                {"name": "平均分", "id": "平均分"},
                                {"name": "标准差", "id": "标准差"},
                                {"name": "离均率(%)", "id": "离均率(%)"},
                            ],
                            data=ranking_data,  # type: ignore
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                            },
                            style_header={"fontWeight": "bold"},
                            style_data_conditional=[
                                {
                                    "if": {
                                        "filter_query": "{排名} = 1",
                                        "column_id": "排名",
                                    },
                                    "backgroundColor": "#d4edda",
                                    "color": "black",
                                    "fontWeight": "bold",
                                }
                            ],
                        ),
                    ]
                ),
            ],
            className="mb-4",
        )

        cards.append(card)

    return cards


def create_subject_rankings_comparison(
    analysis_results: dict[str, Any],
) -> dbc.Card:
    """
    创建学科排名对比图表

    Args:
        analysis_results: 分析结果

    Returns:
        dbc.Card: 学科排名对比卡片
    """
    # 准备对比数据
    comparison_data = []

    for group_name, group_data in analysis_results.items():
        rankings = group_data.get("学科排名", [])
        for rank_info in rankings:
            comparison_data.append(
                {
                    "群体": group_name,
                    "学科": rank_info["学科"],
                    "排名": rank_info["排名"],
                    "平均分": rank_info["平均分"],
                    "离均率(%)": rank_info["离均率(%)"],
                }
            )

    if not comparison_data:
        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.P(
                            "暂无数据可供对比",
                            className="text-muted text-center",
                        )
                    ]
                )
            ]
        )

    df_comparison = pd.DataFrame(comparison_data)

    return dbc.Card(
        [
            dbc.CardHeader([html.H5("🏆 学科排名对比", className="text-primary mb-0")]),
            dbc.CardBody(
                [
                    # 排名对比表格
                    dash_table.DataTable(
                        id="subject_comparison_table",
                        columns=[
                            {"name": "群体", "id": "群体"},
                            {"name": "学科", "id": "学科"},
                            {"name": "排名", "id": "排名"},
                            {"name": "平均分", "id": "平均分"},
                            {"name": "离均率(%)", "id": "离均率(%)"},
                        ],
                        data=df_comparison.to_dict("records"),
                        style_cell={"textAlign": "left", "padding": "8px"},
                        style_header={"fontWeight": "bold"},
                        style_data_conditional=[  # type: ignore
                            {
                                "if": {
                                    "filter_query": "{排名} = 1",
                                    "column_id": "排名",
                                },
                                "backgroundColor": "#d4edda",
                                "color": "black",
                                "fontWeight": "bold"
                            }
                        ],
                        sort_action="native",
                        filter_action="native",
                    ),
                    html.Hr(),
                    # 平均分对比图表
                    html.H6("📊 学科平均分对比", className="text-secondary"),
                    dcc.Graph(
                        figure=px.bar(
                            df_comparison,
                            x="学科",
                            y="平均分",
                            color="群体",
                            barmode="group",
                            title="不同群体学科平均分对比",
                        )
                    ),
                ]
            ),
        ]
    )


def create_visualization_content(
    analysis_results: dict[str, Any],
) -> list[dbc.Card]:
    """
    创建可视化图表内容

    Args:
        analysis_results: 分析结果

    Returns:
        List[dbc.Card]: 图表卡片列表
    """
    cards = []

    # 群体规模对比
    group_names = list(analysis_results.keys())
    group_counts = [analysis_results[name]["群体人数"] for name in group_names]

    cards.append(
        dbc.Card(
            [
                dbc.CardHeader(
                    [html.H5("👥 群体规模对比", className="text-primary mb-0")]
                ),
                dbc.CardBody(
                    [
                        dcc.Graph(
                            figure=px.pie(
                                values=group_counts,
                                names=group_names,
                                title="各有效群体人数分布",
                            )
                        )
                    ]
                ),
            ]
        )
    )

    # 总分分布对比
    cards.append(
        dbc.Card(
            [
                dbc.CardHeader(
                    [html.H5("📈 总分统计对比", className="text-primary mb-0")]
                ),
                dbc.CardBody(
                    [
                        dcc.Graph(
                            figure=px.bar(
                                x=group_names,
                                y=[
                                    analysis_results[name]["总分平均分"]
                                    for name in group_names
                                ],
                                title="各群体总分平均分对比",
                                labels={"x": "群体", "y": "平均分"},
                            )
                        )
                    ]
                ),
            ]
        )
    )

    # 学科离均率热力图
    heatmap_data = []
    for group_name, group_data in analysis_results.items():
        for subject, rate in group_data["学科离均率"].items():
            heatmap_data.append({"群体": group_name, "学科": subject, "离均率": rate})

    if heatmap_data:
        df_heatmap = pd.DataFrame(heatmap_data)
        cards.append(
            dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.H5(
                                "🌡️ 学科离均率热力图",
                                className="text-primary mb-0",
                            )
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dcc.Graph(
                                figure=px.density_heatmap(
                                    df_heatmap,
                                    x="学科",
                                    y="群体",
                                    z="离均率",
                                    title="学科离均率分布热力图",
                                )
                            )
                        ]
                    ),
                ]
            )
        )

    return cards


def create_school_subject_comparison_content(
    analysis_results: dict[str, Any], selected_subjects: list[str] | None = None
) -> list[dbc.Card]:
    """
    创建学校学科对比内容

    Args:
        analysis_results: 分析结果
        selected_subjects: 选择的学科列表

    Returns:
        List[dbc.Card]: 对比卡片列表
    """
    cards = []

    for group_name, group_data in analysis_results.items():
        school_analysis = group_data.get("学校学科分析", {})
        subject_rankings = school_analysis.get("学科排名", {})

        if not subject_rankings:
            cards.append(
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.P(
                                    f"{group_name}群体暂无学校学科分析数据",
                                    className="text-muted text-center",
                                )
                            ]
                        )
                    ]
                )
            )
            continue

        # 如果没有选择学科，显示所有学科
        if not selected_subjects:
            selected_subjects = list(subject_rankings.keys())

        # 为每个选择的学科创建对比表格
        for subject in selected_subjects:
            if subject in subject_rankings:
                ranking_data = subject_rankings[subject]

                if ranking_data:
                    df_ranking = pd.DataFrame(ranking_data)

                    card = dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.H5(
                                        f"{group_name}群体 - {subject}学校对比",
                                        className="text-primary mb-0",
                                    ),
                                    html.Small(
                                        f"共{len(df_ranking)}所学校",
                                        className="text-muted",
                                    ),
                                ]
                            ),
                            dbc.CardBody(
                                [
                                        dash_table.DataTable(
                                        id=f"school_comparison_{group_name}_{subject}",
                                        columns=[
                                            {"name": "均值排名", "id": "排名"},
                                            {"name": "学校", "id": "学校"},
                                            {
                                                "name": "学校均分",
                                                "id": "学校均分",
                                            },
                                            {
                                                "name": "群体均分",
                                                "id": "群体均分",
                                            },
                                            {
                                                "name": "离均率(%)",
                                                "id": "离均率(%)",
                                            },
                                            {
                                                "name": "学校人数",
                                                "id": "学校人数",
                                            },
                                        ],
                                        data=df_ranking.to_dict("records"),
                                        style_cell={
                                            "textAlign": "left",
                                            "padding": "8px",
                                        },
                                        style_header={"fontWeight": "bold"},
                                        style_data_conditional=[
                                            {
                                                "if": {
                                                    "filter_query": "{排名} = 1",
                                                    "column_id": "排名",
                                                },
                                                "backgroundColor": "#d4edda",
                                                "color": "black",
                                                "fontWeight": "bold"
                                            },
                                            {
                                                "if": {
                                                    "filter_query": "{离均率(%)} > 0",
                                                    "column_id": "离均率(%)",
                                                },
                                                "color": "green",
                                                "fontWeight": "bold"
                                            },
                                            {
                                                "if": {
                                                    "filter_query": "{离均率(%)} < 0",
                                                    "column_id": "离均率(%)",
                                                },
                                                "color": "red"
                                            }
                                        ],
                                        sort_action="native",
                                        filter_action="native",
                                    )
                                ]
                            ),
                        ],
                        className="mb-4",
                    )

                    cards.append(card)

    if not cards:
        cards.append(
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.P(
                                "请选择要对比的学科",
                                className="text-muted text-center",
                            )
                        ]
                    )
                ]
            )
        )

    return cards


def create_hierarchy_analysis_content(
    analysis_results: dict[str, Any],
) -> dbc.Card:
    """
    创建层级分析内容

    Args:
        analysis_results: 分析结果

    Returns:
        dbc.Card: 层级分析卡片
    """
    hierarchy_data = []

    for group_name, group_data in analysis_results.items():
        hierarchy = group_data.get("层级分析", {})
        for level, level_data in hierarchy.items():
            for sub_group, stats in level_data.items():
                hierarchy_data.append(
                    {
                        "群体": group_name,
                        "层级": level,
                        "分组": sub_group,
                        "人数": stats["人数"],
                        "平均分": (
                            sum(stats["各学科平均分"].values())
                            / len(stats["各学科平均分"])
                            if stats["各学科平均分"]
                            else 0
                        ),
                    }
                )

    if not hierarchy_data:
        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.P(
                            "暂无层级分析数据",
                            className="text-muted text-center",
                        )
                    ]
                )
            ]
        )

    df_hierarchy = pd.DataFrame(hierarchy_data)

    return dbc.Card(
        [
            dbc.CardHeader([html.H5("🏢 层级分布分析", className="text-primary mb-0")]),
            dbc.CardBody(
                [
                    dash_table.DataTable(
                        id="hierarchy_table",
                        columns=[
                            {"name": "群体", "id": "群体"},
                            {"name": "层级", "id": "层级"},
                            {"name": "分组", "id": "分组"},
                            {"name": "人数", "id": "人数"},
                            {"name": "平均分", "id": "平均分"},
                        ],
                        data=df_hierarchy.to_dict("records"),
                        style_cell={"textAlign": "left", "padding": "8px"},
                        style_header={"fontWeight": "bold"},
                        sort_action="native",
                        filter_action="native",
                    )
                ]
            ),
        ]
    )
