#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临界生分析UI组件
创建控制面板和结果展示界面
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Any
import logging

logger = logging.getLogger(__name__)


def create_critical_students_control_panel() -> dbc.Card:
    """
    创建临界生分析控制面板
    
    Returns:
        dbc.Card: 控制面板组件
    """
    return dbc.Card(
        [
                    dbc.CardHeader(
                [
                    html.H4("🎯 临界生分析", className="mb-0"),
                    html.P(
                        "分析特控线和本科线附近±5分范围内的学生",
                        className="text-muted mb-0",
                    ),
                ]
            ),
            dbc.CardBody(
                [
                    # 筛选条件设置
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label(
                                        "数据筛选",
                                        className="fw-bold text-primary",
                                    ),
                                    html.P(
                                        "选择区县、学校、行政班进行筛选",
                                        className="text-muted small",
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                    # 三级联动菜单 - 放在一行
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("选择区县:"),
                                    dcc.Dropdown(
                                        id="critical_county_dropdown",
                                        options=[],
                                        value=[],
                                        multi=True,
                                        placeholder="选择区县（可选）",
                                        className="mb-3",
                                    ),
                                ],
                                width=4
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("选择学校:"),
                                    dcc.Dropdown(
                                        id="critical_school_dropdown",
                                        options=[],
                                        value=[],
                                        multi=True,
                                        placeholder="选择学校（可选）",
                                        className="mb-3",
                                    ),
                                ],
                                width=4
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("选择行政班:"),
                                    dcc.Dropdown(
                                        id="critical_class_dropdown",
                                        options=[],
                                        value=[],
                                        multi=True,
                                        placeholder="选择行政班（可选）",
                                        className="mb-3",
                                    ),
                                ],
                                width=4
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("选择学科:"),
                                    dcc.Dropdown(
                                        id="critical_subject_dropdown",
                                        options=[],
                                        value=[],
                                        multi=True,
                                        placeholder="选择要分析的学科（可选）",
                                        className="mb-3",
                                    ),
                                ],
                                width=12
                            )
                        ]
                    ),
                    html.Hr(),
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
                                        "设置特控线和本科线分数，用于临界生分析",
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
                                    dbc.Label("特控线分数:"),
                                    dbc.Input(
                                        id="critical_special_line",
                                        type="number",
                                        value=80.0,
                                        min=0,
                                        max=150,
                                        step=0.5,
                                        style={"width": "100%"}
                                    ),
                                    html.Small(
                                        "特控线分数，用于临界生分析",
                                        className="text-muted"
                                    )
                                ],
                                width=6
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("本科线分数:"),
                                    dbc.Input(
                                        id="critical_bachelor_line",
                                        type="number",
                                        value=60.0,
                                        min=0,
                                        max=150,
                                        step=0.5,
                                        style={"width": "100%"}
                                    ),
                                    html.Small(
                                        "本科线分数，用于临界生分析",
                                        className="text-muted"
                                    )
                                ],
                                width=6
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
                                            html.I(className="bi bi-search me-2"),
                                            "开始分析",
                                        ],
                                        id="analyze_critical_btn",
                                        color="primary",
                                        size="lg",
                                        className="w-100",
                                        n_clicks=0
                                    )
                                ]
                            )
                        ]
                    ),
                    # 使用说明
                    dbc.Alert(
                        [
                            html.H6("📋 使用说明", className="alert-heading"),
                            html.Ul(
                                [
                                    html.Li("可选择区县、学校、行政班进行筛选"),
                                    html.Li("可选择特定学科进行分析"),
                                    html.Li("设置特控线和本科线分数"),
                                    html.Li("点击'开始分析'查看结果"),
                                ],
                                className="mb-0",
                            ),
                        ],
                        color="info",
                        className="small mt-3",
                    ),
                ]
            ),
        ],
        className="shadow-sm mb-4",
    )


def create_critical_students_results_panel() -> dbc.Card:
    """
    创建临界生分析结果面板
    
    Returns:
        dbc.Card: 结果面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H4("📊 分析结果", className="mb-0"),
                    html.P("临界生分析结果展示", className="text-muted mb-0"),
                ]
            ),
            dbc.CardBody(
                [
                    # 分析状态
                    dbc.Alert(
                        "请先设置参数并点击'开始分析'",
                        id="critical_analysis_status",
                        color="info",
                        className="mb-3",
                    ),
                    
                    # 结果摘要
                    html.H5("📈 分析摘要", className="text-primary mb-3"),
                    html.Div(id="critical_summary_stats"),
                    
                    html.Hr(className="my-3"),
                    
                    # 分类型详细统计
                    html.H5("🎯 分类统计", className="text-primary mb-3"),
                    html.Div(id="critical_type_stats"),
                    
                    html.Hr(className="my-3"),
                    
                    # 统计图表
                    html.H5("📊 分析图表", className="text-primary mb-3"),
                    dcc.Graph(
                        id="critical_analysis_chart",
                        style={"height": "400px"}
                    ),
                    
                    html.Hr(className="my-3"),
                    
                    # 详细数据表格
                    html.H5("📋 详细名单", className="text-primary mb-3"),
                    html.Div(id="critical_details_table"),
                ]
            ),
        ],
        className="shadow-sm",
    )


def create_critical_summary_cards(results: dict[str, Any]) -> list[dbc.Card]:
    """
    创建临界生分析摘要卡片
    
    Args:
        results: 分析结果
        
    Returns:
        List[dbc.Card]: 摘要卡片列表
    """
    if not results:
        return []
    
    cards = []
    
    # 总体统计卡片
    total_card = dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6("📊 总体统计", className="text-primary mb-3"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H3(
                                        results.get('total_valid', 0),
                                        className="text-primary mb-0"
                                    ),
                                    html.P(
                                        "有效学生总数",
                                        className="text-muted small"
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    html.H3(
                                        results['special_above']['count'],
                                        className="success mb-0",
                                        style={"color": "#28a745"}
                                    ),
                                    html.P(
                                        "特控线上5分",
                                        className="text-muted small"
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    html.H3(
                                        results['special_below']['count'],
                                        className="warning mb-0",
                                        style={"color": "#ffc107"}
                                    ),
                                    html.P(
                                        "特控线下5分",
                                        className="text-muted small"
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    html.H3(
                                        results['bachelor_above']['count'] + results['bachelor_below']['count'],
                                        className="info mb-0",
                                        style={"color": "#17a2b8"}
                                    ),
                                    html.P(
                                        "本科线附近10分",
                                        className="text-muted small"
                                    ),
                                ],
                                width=3,
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-3",
    )
    cards.append(total_card)
    
    # 分数线统计卡片
    for line_type, line_data in [
        ("特控线", [results['special_above'], results['special_below']]),
        ("本科线", [results['bachelor_above'], results['bachelor_below']])
    ]:
        line_card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H6(f"📈 {line_type}分析", className="text-secondary mb-3"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.P(f"{line_type}上5分", className="mb-1 small"),
                                        html.H4(
                                            f"{line_data[0]['count']}人",
                                            className="mb-1",
                                            style={"color": "#28a745"}
                                        ),
                                        html.P(
                                            f"{line_data[0]['percentage']:.1f}%",
                                            className="small text-muted"
                                        ),
                                    ],
                                    width=6,
                                    className="text-center",
                                ),
                                dbc.Col(
                                    [
                                        html.P(f"{line_type}下5分", className="mb-1 small"),
                                        html.H4(
                                            f"{line_data[1]['count']}人",
                                            className="mb-1",
                                            style={"color": "#ffc107"}
                                        ),
                                        html.P(
                                            f"{line_data[1]['percentage']:.1f}%",
                                            className="small text-muted"
                                        ),
                                    ],
                                    width=6,
                                    className="text-center",
                                ),
                            ]
                        ),
                    ]
                ),
            ],
            className="mb-3",
        )
        cards.append(line_card)
    
    return cards


def create_critical_students_table(results: dict[str, Any], group_type: str) -> html.Div:
    """
    创建临界生详细表格
    
    Args:
        results: 分析结果
        group_type: 群体类型
        
    Returns:
        html.Div: 表格组件
    """
    if not results or group_type not in ['special_above', 'special_below', 'bachelor_above', 'bachelor_below']:
        return html.Div("暂无数据", className="text-muted text-center p-3")
    
    students = results[group_type]['students']
    if not students:
        return html.Div("该群体暂无学生数据", className="text-muted text-center p-3")
    
    # 准备表格数据
    table_data = []
    for student in students:
        table_data.append({
            '姓名': student.get('姓名', ''),
            '学校': student.get('学校', ''),
            '行政班': student.get('行政班', ''),
            '分数': student.get('等级赋分', student.get('总分', student.get('新高考总分', ''))),
            '区县': student.get('区县', ''),
        })
    
    # 群体名称映射
    type_names = {
        'special_above': '特控线上5分',
        'special_below': '特控线下5分',
        'bachelor_above': '本科线上5分',
        'bachelor_below': '本科线下5分'
    }
    
    return html.Div(
        [
            html.H6(f"📋 {type_names[group_type]} - 详细名单", className="text-primary mb-3"),
            dash_table.DataTable(
                id=f"critical_table_{group_type}",
                columns=[
                    {"name": "姓名", "id": "姓名"},
                    {"name": "学校", "id": "学校"},
                    {"name": "行政班", "id": "行政班"},
                    {"name": "分数", "id": "分数"},
                    {"name": "区县", "id": "区县"},
                ],
                data=table_data,
                style_cell={
                    "textAlign": "left",
                    "padding": "10px",
                },
                style_header={"fontWeight": "bold"},
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
        ]
    )


def create_analysis_chart(results: dict[str, Any]):
    """
    创建分析图表
    
    Args:
        results: 分析结果
        
    Returns:
        plotly.graph_objects.Figure: 图表对象
    """
    if not results:
        return {}
    
    categories = ['特控线上5分', '特控线下5分', '本科线上5分', '本科线下5分']
    counts = [
        results['special_above']['count'],
        results['special_below']['count'],
        results['bachelor_above']['count'],
        results['bachelor_below']['count']
    ]
    
    # 创建子图
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('临界生人数统计', '临界生比例分布'),
        specs=[[{"type": "bar"}, {"type": "pie"}]]
    )
    
    # 柱状图
    fig.add_trace(
        go.Bar(
            x=categories,
            y=counts,
            name='人数',
            marker_color=['#28a745', '#ffc107', '#17a2b8', '#dc3545'],
            text=counts,
            textposition='auto'
        ),
        row=1, col=1
    )
    
    # 饼图
    fig.add_trace(
        go.Pie(
            labels=categories,
            values=counts,
            name='比例',
            marker_colors=['#28a745', '#ffc107', '#17a2b8', '#dc3545']
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title="临界生分析结果",
        showlegend=True,
        height=400
    )
    
    return fig