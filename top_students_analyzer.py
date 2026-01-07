#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
尖子生分析模块
分析市排名前500名的学生
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TopStudentsAnalyzer:
    """尖子生分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化尖子生分析器
        
        Args:
            df: 原始数据框
        """
        self.df = df.copy()
        self.valid_data = None
        self._filter_valid_data()
    
    def _filter_valid_data(self):
        """过滤出有效数据（有市排名且未缺考）"""
        # 查找市排名列
        rank_col = None
        for col in ['市排名', '市排', '市rank']:
            if col in self.df.columns:
                rank_col = col
                break
        
        # 如果没找到标准名称，尝试查找其他可能的排名列
        if rank_col is None:
            for col in self.df.columns:
                if '排' in col and '名' in col:
                    rank_col = col
                    logger.info(f"自动检测到排名列: {col}")
                    break
        
        if rank_col is None:
            logger.warning("未找到市排名列")
            self.valid_data = self.df.copy()
        else:
            # 过滤有市排名且未缺考的数据
            if '缺考' in self.df.columns:
                self.valid_data = self.df[
                    (self.df[rank_col].notna()) & 
                    (self.df['缺考'] != '是')
                ].copy()
            else:
                self.valid_data = self.df[self.df[rank_col].notna()].copy()
        
        logger.info(f"有效数据量: {len(self.valid_data)}")
        if rank_col:
            logger.info(f"使用排名列: {rank_col}")
        
        # 保存排名列名供后续使用
        self.rank_column = rank_col
    
    def analyze_top_students(self, top_n: int = 500):
        """
        分析尖子生情况
        
        Args:
            top_n: 前N名学生
            
        Returns:
            dict: 分析结果
        """
        if self.valid_data is None or len(self.valid_data) == 0:
            return None
        
        # 使用保存的排名列名或重新查找
        rank_col = getattr(self, 'rank_column', None)
        score_col = None
        
        # 如果没有保存的排名列，重新查找
        if rank_col is None:
            for col in ['市排名', '市排', '市rank']:
                if col in self.valid_data.columns:
                    rank_col = col
                    break
            
            # 如果没找到，尝试查找其他排名列
            if rank_col is None:
                for col in self.valid_data.columns:
                    if '排' in col and '名' in col:
                        rank_col = col
                        logger.info(f"自动检测到排名列: {col}")
                        break
        
        for col in ['等级赋分', '总分', '新高考总分']:
            if col in self.valid_data.columns:
                score_col = col
                break
        
        # 如果没找到分数列，尝试自动检测
        if score_col is None:
            exclude_keywords = ['姓名', '学号', '班', '校', '县', '排名', '排', '等级', '选科', '准考证', '考生', '缺考']
            for col in self.valid_data.columns:
                if not any(exclude in col for exclude in exclude_keywords):
                    try:
                        numeric_data = pd.to_numeric(self.valid_data[col], errors='coerce')
                        if not numeric_data.isna().all():
                            non_null_data = numeric_data.dropna()
                            if len(non_null_data) > 0 and non_null_data.max() > 50:
                                score_col = col
                                logger.info(f"自动检测到分数列: {col}")
                                break
                    except:
                        continue
        
        if rank_col is None:
            logger.error("未找到市排名列")
            return None
        
        # 按市排名升序排序
        sorted_data = self.valid_data.copy()
        sorted_data[rank_col] = pd.to_numeric(sorted_data[rank_col], errors='coerce')
        sorted_data = sorted_data.sort_values(by=rank_col, ascending=True)
        
        # 取前N名
        top_students = sorted_data.head(top_n)
        
        # 计算统计信息
        results = {
            'total_valid': len(self.valid_data),
            'top_n': top_n,
            'actual_top_count': len(top_students),
            'students': top_students.to_dict('records') if len(top_students) > 0 else [],
            'rank_column': rank_col,
            'score_column': score_col or '未知'
        }
        
        # 分数统计
        if score_col and score_col in top_students.columns:
            scores = pd.to_numeric(top_students[score_col], errors='coerce')
            results.update({
                'score_stats': {
                    'max_score': scores.max() if not scores.empty else 0,
                    'min_score': scores.min() if not scores.empty else 0,
                    'avg_score': scores.mean() if not scores.empty else 0,
                    'median_score': scores.median() if not scores.empty else 0
                }
            })
        
        # 区县分布统计
        if '区县' in top_students.columns:
            county_dist = top_students['区县'].value_counts().to_dict()
            results['county_distribution'] = county_dist
        
        # 学校分布统计
        if '学校' in top_students.columns:
            school_dist = top_students['学校'].value_counts().to_dict()
            results['school_distribution'] = school_dist
        
        # 班级分布统计
        if '行政班' in top_students.columns:
            class_dist = top_students['行政班'].value_counts().to_dict()
            results['class_distribution'] = class_dist
        
        logger.info(f"尖子生分析完成 - 前{top_n}名: {results['actual_top_count']}人")
        
        return results
    
    def create_analysis_chart(self, results: Dict):
        """
        创建分析图表
        
        Args:
            results: 分析结果
            
        Returns:
            plotly.graph_objects.Figure: 图表对象
        """
        if not results:
            return go.Figure()
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('排名分布', '区县分布', '学校分布TOP10', '分数分布'),
            specs=[[{"type": "bar"}, {"type": "pie"}], [{"type": "bar"}, {"type": "histogram"}]]
        )
        
        # 1. 排名分布柱状图
        if results.get('students'):
            ranks = [student.get(results['rank_column'], 0) for student in results['students']]
            fig.add_trace(
                go.Histogram(
                    x=ranks,
                    nbinsx=20,
                    name='排名分布',
                    marker_color='#007bff'
                ),
                row=1, col=1
            )
        
        # 2. 区县分布饼图
        if 'county_distribution' in results:
            counties = list(results['county_distribution'].keys())
            counts = list(results['county_distribution'].values())
            fig.add_trace(
                go.Pie(
                    labels=counties,
                    values=counts,
                    name='区县分布'
                ),
                row=1, col=2
            )
        
        # 3. 学校分布TOP10
        if 'school_distribution' in results:
            schools = list(results['school_distribution'].keys())[:10]
            counts = list(results['school_distribution'].values())[:10]
            fig.add_trace(
                go.Bar(
                    x=schools,
                    y=counts,
                    name='TOP10学校',
                    marker_color='#28a745'
                ),
                row=2, col=1
            )
        
        # 4. 分数分布直方图
        if 'score_stats' in results:
            scores = [student.get(results['score_column'], 0) for student in results['students']]
            fig.add_trace(
                go.Histogram(
                    x=scores,
                    nbinsx=15,
                    name='分数分布',
                    marker_color='#17a2b8'
                ),
                row=2, col=2
            )
        
        fig.update_layout(
            title=f"尖子生分析结果 (前{results['top_n']}名)",
            showlegend=True,
            height=600
        )
        
        return fig
    
    def get_detailed_table_data(self, results: Dict, show_details: bool = True):
        """
        获取详细表格数据
        
        Args:
            results: 分析结果
            show_details: 是否显示学生详情
            
        Returns:
            List[Dict]: 表格数据
        """
        table_data = []
        
        if show_details and 'students' in results:
            for student in results['students']:
                table_data.append({
                    '市排名': student.get(results['rank_column'], ''),
                    '姓名': student.get('姓名', ''),
                    '学校': student.get('学校', ''),
                    '班级': student.get('行政班', ''),
                    '分数': student.get(results['score_column'], ''),
                    '区县': student.get('区县', '')
                })
        
        return table_data
    
    def create_summary_stats(self, results: Dict):
        """
        创建统计概览
        
        Args:
            results: 分析结果
            
        Returns:
            html.Div: 统计概览组件
        """
        if not results:
            return html.Div("暂无数据", className="text-muted")
        
        stats_cards = []
        
        # 基本统计
        stats_cards.extend([
            dbc.Col([
                html.H4(f"{results['actual_top_count']}", className="text-primary"),
                html.P("尖子生人数", className="text-muted")
            ], width=3),
            dbc.Col([
                html.H4(f"{results['top_n']}", className="text-info"),
                html.P("排名范围", className="text-muted")
            ], width=3)
        ])
        
        # 分数统计
        if 'score_stats' in results:
            stats_cards.extend([
                dbc.Col([
                    html.H4(f"{results['score_stats']['max_score']:.1f}", className="text-success"),
                    html.P("最高分", className="text-muted")
                ], width=2),
                dbc.Col([
                    html.H4(f"{results['score_stats']['avg_score']:.1f}", className="text-warning"),
                    html.P("平均分", className="text-muted")
                ], width=2)
            ])
        
        return dbc.Row(stats_cards, className="mb-4")


def create_top_students_control_panel():
    """
    创建尖子生分析控制面板
    
    Returns:
        dbc.Card: 控制面板组件
    """
    return dbc.Card([
        dbc.CardHeader("🏆 尖子生分析设置"),
        dbc.CardBody([
            # 第一行：数据筛选
            dbc.Row([
                dbc.Col([
                    html.H6("📋 数据筛选", className="text-primary mb-3"),
                    html.P("选择区县、学校、行政班进行筛选，不选则分析全部", className="text-muted small mb-3")
                ], width=12)
            ]),
            
            dbc.Row([
                # 区县选择
                dbc.Col([
                    dbc.Label("选择区县:"),
                    dcc.Dropdown(
                        id="top_county_dropdown",
                        placeholder="选择区县（可选）",
                        multi=True,
                        style={"width": "100%"}
                    )
                ], width=3),
                
                # 学校选择
                dbc.Col([
                    dbc.Label("选择学校:"),
                    dcc.Dropdown(
                        id="top_school_dropdown",
                        placeholder="选择学校（可选）",
                        multi=True,
                        style={"width": "100%"}
                    )
                ], width=3),
                
                # 班级选择
                dbc.Col([
                    dbc.Label("选择行政班:"),
                    dcc.Dropdown(
                        id="top_class_dropdown",
                        placeholder="选择行政班（可选）",
                        multi=True,
                        style={"width": "100%"}
                    )
                ], width=3),
                
                # 尖子生数量设置
                dbc.Col([
                    dbc.Label("尖子生数量:"),
                    dbc.Input(
                        id="top_students_range",
                        type="number",
                        value=500,
                        min=1,
                        max=2000,
                        step=1,
                        style={"width": "100%"}
                    ),
                    html.Small("市排名前N名，用于尖子生分析", className="text-muted")
                ], width=3)
            ], className="mb-3"),
            
            # 第二行：尖子生定义说明
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.P([
                            "📝 尖子生定义：市排名前",
                            html.Strong("500名", className="text-primary fw-bold"),
                            "范围内的考生"
                        ], className="mb-2"),
                        html.P([
                            "📊 可根据需要调整分析范围，查看不同排名区间的尖子生情况"
                        ], className="text-muted small mb-3")
                    ], className="bg-light p-3 rounded")
                ], width=12)
            ], className="mb-3"),
            
            # 分析按钮
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-bar-chart-line me-2"),
                        "开始分析"
                    ], 
                    id="analyze_top_btn", 
                    color="primary", 
                    size="lg", 
                    className="w-100",
                    n_clicks=0)
                ], width=12)
            ])
        ])
    ], className="mb-4 shadow-sm")


def create_top_students_results_panel():
    """
    创建尖子生分析结果面板
    
    Returns:
        dbc.Card: 结果面板组件
    """
    return dbc.Card([
        dbc.CardHeader("📊 尖子生分析结果"),
        dbc.CardBody([
            # 状态提示
            html.Div(id="top_analysis_status", className="mb-3"),
            
            # 两列布局：统计概览 + 分类统计
            dbc.Row([
                dbc.Col([
                    # 基本统计概览
                    html.Div(id="top_summary_stats", className="mb-3")
                ], width=12, lg=8),
                
                dbc.Col([
                    # 分类详细统计（右侧展示）
                    html.Div(id="top_type_stats", className="mb-3")
                ], width=12, lg=4)
            ]),
            
            # 分析图表
            dcc.Graph(
                id="top_analysis_chart",
                style={"height": "600px"},
                className="mb-4 shadow-sm"
            ),
            
            # 详细数据表格
            html.Div(id="top_details_table", className="mt-4"),
        ])
    ], className="mb-4 shadow-sm")


def safe_divide(numerator, denominator, default=0):
    """安全的除法运算，避免除零错误"""
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default