#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新增分析模块的UI组件
包含临界生、尖子生、小题分析的控制面板和结果面板
"""

import dash_bootstrap_components as dbc
import dash
from dash import html, dcc, dash_table


def create_critical_students_tab():
    """
    创建临界生分析标签页内容
    
    Returns:
        html.Div: 临界生分析页面内容
    """
    # 避免循环导入
    try:
        from critical_students_ui import create_critical_students_control_panel, create_critical_students_results_panel
        
        return html.Div([
            # 两列布局：左侧设置面板，右侧结果面板
            dbc.Row([
                # 左侧：设置面板
                dbc.Col([
                    create_critical_students_control_panel()
                ], width=12, md=5, lg=4),  # 在中等屏幕占5列，大屏幕占4列
                
                # 右侧：结果面板
                dbc.Col([
                    create_critical_students_results_panel()
                ], width=12, md=7, lg=8)  # 在中等屏幕占7列，大屏幕占8列
            ])
        ])
    except ImportError:
        return html.Div("临界生分析模块加载失败", className="text-center text-danger my-4")


def create_top_students_tab():
    """
    创建尖子生分析标签页内容
    
    Returns:
        html.Div: 尖子生分析页面内容
    """
    try:
        from top_students_analyzer import create_top_students_control_panel, create_top_students_results_panel
        return html.Div([
            # 控制面板
            create_top_students_control_panel(),
            
            # 结果面板
            create_top_students_results_panel()
        ])
    except ImportError:
        return html.Div("尖子生分析模块加载失败", className="text-center text-danger my-4")


def create_question_analysis_tab():
    """
    创建小题分析标签页内容
    
    Returns:
        html.Div: 小题分析页面内容
    """
    try:
        from question_analysis_analyzer import create_question_analysis_control_panel, create_question_analysis_results_panel
        return html.Div([
            # 控制面板
            create_question_analysis_control_panel(),
            
            # 结果面板
            create_question_analysis_results_panel()
        ])
    except ImportError:
        return html.Div("小题分析模块加载失败", className="text-center text-danger my-4")


def create_results_table(table_data: list, table_id: str):
    """
    创建结果表格的通用函数
    
    Args:
        table_data: 表格数据
        table_id: 表格ID
        
    Returns:
        dash_table.DataTable: 数据表格组件
    """
    if not table_data:
        return html.Div("暂无数据", className="text-center text-muted my-4")
    
    # 根据数据确定列定义
    if len(table_data) > 0 and isinstance(table_data[0], dict):
        columns = [{"name": col, "id": col} for col in table_data[0].keys()]
    else:
        return html.Div("数据格式错误", className="text-center text-danger my-4")
    
    return dash_table.DataTable(
        id=table_id,
        columns=columns,
        data=table_data,
        page_size=20,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '10px'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 250)',
            'fontWeight': 'bold',
            'border': '1px solid rgb(200, 200, 220)'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            },
            {
                'if': {'row_index': 'even'},
                'backgroundColor': 'white'
            }
        ]
    )