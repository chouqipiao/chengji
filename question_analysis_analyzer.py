#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学科小题分析模块
分析各小题的得分率、难度系数等指标
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


class QuestionAnalysisAnalyzer:
    """小题分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化小题分析器
        
        Args:
            df: 原始数据框
        """
        self.df = df.copy()
        self.valid_data = None
        self._filter_valid_data()
        self._question_fields = self._detect_question_fields()
    
    def _filter_valid_data(self):
        """过滤出有效数据（缺考为'否'）"""
        if '缺考' in self.df.columns:
            self.valid_data = self.df[self.df['缺考'] == '否'].copy()
        else:
            self.valid_data = self.df.copy()
        logger.info(f"有效数据量: {len(self.valid_data)}")
    
    def _detect_question_fields(self):
        """检测小题字段"""
        question_fields = []
        
        # 首先检查T格式题号 (T1, T2, T3...)
        t_pattern_cols = []
        for col in self.valid_data.columns:
            if col.strip().upper().startswith('T') and col.strip()[1:].isdigit():
                t_pattern_cols.append(col.strip())
        
        if t_pattern_cols:
            # 按数字排序 T1, T2, T3...
            t_pattern_cols.sort(key=lambda x: int(x[1:]))
            question_fields.extend(t_pattern_cols)
            logger.info(f"检测到T格式题号: {t_pattern_cols}")
        else:
            # 如果没有T格式，使用原有检测逻辑
            patterns = [
                '1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16',
                '17(1)','17(2)(3)','18(1)(2)','18(3)','18(4)','19(1)(2)','19(3)(4)','20(1)(2)','20(3)(4)','21(1)(2)(3)','21(4)',
                '题','小题','q','question','t'
            ]
            
            for pattern in patterns:
                matching_cols = [col for col in self.valid_data.columns if pattern in col]
                question_fields.extend(matching_cols)
        
        # 如果没有找到，尝试检测数字列
        if not question_fields:
            # 查找可能是分数的数字列（排除明显不是小题的列）
            exclude_keywords = ['总分','分','排名','排','等级','学号','号','班','校','县']
            for col in self.valid_data.columns:
                if not any(exclude in col for exclude in exclude_keywords):
                    try:
                        # 尝试转换为数字
                        numeric_data = pd.to_numeric(self.valid_data[col], errors='coerce')
                        if not numeric_data.isna().all():
                            # 检查是否像分数（数值较小，通常是整数或小数）
                            non_null_data = numeric_data.dropna()
                            if len(non_null_data) > 0:
                                max_val = non_null_data.max()
                                min_val = non_null_data.min()
                                # 如果最大值不超过20，且是整数或简单小数，可能是小题分数
                                if max_val <= 20 and max_val > 0:
                                    question_fields.append(col)
                    except:
                        continue
        
        # 去重并智能排序
        question_fields = list(set(question_fields))
        question_fields = self._sort_question_fields(question_fields)
        logger.info(f"检测到的小题字段: {question_fields}")
        self._question_fields = question_fields
        return question_fields
    
    def _sort_question_fields(self, question_fields):
        """智能排序小题字段，支持多种格式"""
        def extract_number(field_name):
            """从字段名中提取数字"""
            import re
            # 匹配各种数字格式：T1, 1, 题1, 1(1)等
            match = re.search(r'(\d+)', field_name)
            return int(match.group(1)) if match else 0
        
        # 优先按数字排序，如果数字相同则按原字符串排序
        return sorted(question_fields, key=lambda x: (extract_number(x), x.lower()))
    
    def get_question_full_score(self, question_field: str):
        """
        获取小题的满分
        
        Args:
            question_field: 小题字段名
            
        Returns:
            float: 满分值
        """
        # 满分映射表 - 支持T格式和数字格式
        full_score_map = {
            # T格式题号
            'T1':5,'T2':5,'T3':5,'T4':5,'T5':5,'T6':5,'T7':5,'T8':5,'T9':5,'T10':5,'T11':5,'T12':5,'T13':5,'T14':5,'T15':5,'T16':5,
            # 传统格式
            '1':5,'2':5,'3':5,'4':5,'5':5,'6':5,'7':5,'8':5,'9':5,'10':5,'11':5,'12':5,'13':5,'14':5,'15':5,'16':5,
            '17(1)':3,'17(2)(3)':7,'18(1)(2)':6,'18(3)':2,'18(4)':2,'19(1)(2)':6,'19(3)(4)':4,'20(1)(2)':6,'20(3)(4)':4,'21(1)(2)(3)':8,'21(4)':2
        }
        
        for pattern, score in full_score_map.items():
            if pattern in question_field:
                return score
        
        # 如果映射表中没有，尝试从数据中推断
        try:
            scores = pd.to_numeric(self.valid_data[question_field], errors='coerce').dropna()
            if len(scores) > 0:
                max_score = scores.max()
                # 常见的满分值
                common_full_scores = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20]
                # 找到最接近的常见满分值（允许小误差）
                for full_score in common_full_scores:
                    if max_score <= full_score * 1.05:  # 允许5%的误差
                        return full_score
                # 如果没有找到，返回最大值的向上取整
                return int(max_score) + 1 if max_score != int(max_score) else int(max_score)
        except:
            pass
        
        # 默认满分
        return 5.0
    
    def analyze_questions(self):
        """
        分析小题情况
        
        Returns:
            dict: 分析结果
        """
        if self.valid_data is None or len(self.valid_data) == 0 or not self._question_fields:
            return None
        
        question_analysis = []
        
        for question_field in self._question_fields:
            if question_field not in self.valid_data.columns:
                continue
            
            # 获取该小题的得分
            scores = pd.to_numeric(self.valid_data[question_field], errors='coerce')
            valid_scores = scores.dropna()
            
            if len(valid_scores) == 0:
                continue
            
            # 计算统计指标
            full_score = self.get_question_full_score(question_field)
            avg_score = valid_scores.mean()
            max_score = valid_scores.max()
            min_score = valid_scores.min()
            score_rate = (avg_score / full_score) * 100 if full_score > 0 else 0
            difficulty = 1 - (avg_score / full_score) if full_score > 0 else 1
            
            # 得分率分布
            excellent_count = len(valid_scores[valid_scores >= full_score * 0.9])  # 优秀率（90%以上）
            good_count = len(valid_scores[(valid_scores >= full_score * 0.7) & (valid_scores < full_score * 0.9)])  # 良好率（70-90%）
            pass_count = len(valid_scores[(valid_scores >= full_score * 0.6) & (valid_scores < full_score * 0.7)])  # 及格率（60-70%）
            
            question_analysis.append({
                'question_id': question_field,
                'full_score': full_score,
                'avg_score': avg_score,
                'max_score': max_score,
                'min_score': min_score,
                'score_rate': score_rate,
                'difficulty': difficulty,
                'excellent_rate': (excellent_count / len(valid_scores)) * 100,
                'good_rate': (good_count / len(valid_scores)) * 100,
                'pass_rate': (pass_count / len(valid_scores)) * 100,
                'valid_count': len(valid_scores),
                'zero_count': len(valid_scores[valid_scores == 0])
            })
        
        results = {
            'total_questions': len(question_analysis),
            'questions': question_analysis,
            'summary': {
                'avg_score_rate': np.mean([q['score_rate'] for q in question_analysis]),
                'avg_difficulty': np.mean([q['difficulty'] for q in question_analysis]),
                'overall_excellent_rate': np.mean([q['excellent_rate'] for q in question_analysis]),
                'overall_good_rate': np.mean([q['good_rate'] for q in question_analysis]),
                'overall_pass_rate': np.mean([q['pass_rate'] for q in question_analysis])
            }
        }
        
        logger.info(f"小题分析完成 - 共{results['total_questions']}题")
        
        return results
    
    def create_analysis_chart(self, results: Dict):
        """
        创建分析图表
        
        Args:
            results: 分析结果
            
        Returns:
            plotly.graph_objects.Figure: 图表对象
        """
        if not results or not results.get('questions'):
            return go.Figure()
        
        questions = results['questions']
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('得分率分布', '难度系数分布', '小题得分统计', '得分率难度关系'),
            specs=[[{"type": "bar"}, {"type": "bar"}], [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        question_ids = [q['question_id'] for q in questions]
        score_rates = [q['score_rate'] for q in questions]
        difficulties = [q['difficulty'] for q in questions]
        avg_scores = [q['avg_score'] for q in questions]
        full_scores = [q['full_score'] for q in questions]
        
        # 1. 得分率柱状图
        fig.add_trace(
            go.Bar(
                x=question_ids,
                y=score_rates,
                name='得分率(%)',
                marker_color='rgba(40, 167, 69, 0.8)',
                text=[f'{rate:.1f}%' for rate in score_rates],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        # 2. 难度系数柱状图
        fig.add_trace(
            go.Bar(
                x=question_ids,
                y=difficulties,
                name='难度系数',
                marker_color='rgba(220, 53, 69, 0.8)',
                text=[f'{diff:.2f}' for diff in difficulties],
                textposition='auto'
            ),
            row=1, col=2
        )
        
        # 3. 小题得分统计柱状图
        fig.add_trace(
            go.Bar(
                x=question_ids,
                y=avg_scores,
                name='平均得分',
                marker_color='rgba(13, 110, 253, 0.8)',
                text=[f'{score:.1f}' for score in avg_scores],
                textposition='auto'
            ),
            row=2, col=1
        )
        
        # 4. 满分对比柱状图
        fig.add_trace(
            go.Bar(
                x=question_ids,
                y=full_scores,
                name='满分',
                marker_color='rgba(108, 117, 125, 0.8)',
                text=[f'{score:.0f}' for score in full_scores],
                textposition='auto'
            ),
            row=2, col=2
        )
        
        # 散点图（得分率vs难度）
        fig.add_trace(
            go.Scatter(
                x=score_rates,
                y=difficulties,
                mode='markers+text',
                name='难度-得分率关系',
                marker=dict(
                    size=8,
                    color=score_rates,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="得分率")
                ),
                text=question_ids,
                textposition="top center"
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title="小题分析结果",
            showlegend=True,
            height=600
        )
        
        return fig
    
    def get_detailed_table_data(self, results: Dict, show_details: bool = True):
        """
        获取详细表格数据
        
        Args:
            results: 分析结果
            show_details: 是否显示详情
            
        Returns:
            List[Dict]: 表格数据
        """
        table_data = []
        
        if show_details and 'questions' in results:
            for question in results['questions']:
                # 根据难度设置颜色标记
                if question['difficulty'] < 0.3:
                    difficulty_level = '容易'
                    color_class = 'text-success'
                elif question['difficulty'] < 0.5:
                    difficulty_level = '中等'
                    color_class = 'text-warning'
                else:
                    difficulty_level = '困难'
                    color_class = 'text-danger'
                
                table_data.append({
                    '小题编号': question['question_id'],
                    '满分': question['full_score'],
                    '平均得分': question['avg_score'],
                    '得分率': f"{question['score_rate']:.1f}%",
                    '难度系数': f"{question['difficulty']:.2f}",
                    '难度等级': difficulty_level,
                    '优秀率': f"{question['excellent_rate']:.1f}%",
                    '良好率': f"{question['good_rate']:.1f}%",
                    '及格率': f"{question['pass_rate']:.1f}%",
                    '有效人数': question['valid_count'],
                    '零分人数': question['zero_count']
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
        if not results or not results.get('summary'):
            return html.Div("暂无数据", className="text-muted")
        
        summary = results['summary']
        
        stats_cards = [
            dbc.Col([
                html.H4(f"{results['total_questions']}", className="text-primary"),
                html.P("小题总数", className="text-muted")
            ], width=2),
            dbc.Col([
                html.H4(f"{summary['avg_score_rate']:.1f}%", className="text-info"),
                html.P("平均得分率", className="text-muted")
            ], width=2),
            dbc.Col([
                html.H4(f"{summary['avg_difficulty']:.2f}", className="text-warning"),
                html.P("平均难度", className="text-muted")
            ], width=2),
            dbc.Col([
                html.H4(f"{summary['overall_excellent_rate']:.1f}%", className="text-success"),
                html.P("整体优秀率", className="text-muted")
            ], width=3),
            dbc.Col([
                html.H4(f"{summary['overall_pass_rate']:.1f}%", className="text-danger"),
                html.P("整体及格率", className="text-muted")
            ], width=3)
        ]
        
        return dbc.Row(stats_cards, className="mb-4")


def create_question_analysis_control_panel():
    """
    创建小题分析控制面板
    
    Returns:
        dbc.Card: 控制面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader("📝 学科小题分析"),
            dbc.CardBody(
                [
                    html.P([
                        "⚠️ 注意：学科小题分析需要导入单独的小题数据文件",
                        html.Br(),
                        "支持常见的小题编号格式，如：1, 2, 17(1), 18(2)(3)等",
                        html.Br(),
                        "数据格式要求：每列对应一道小题，包含学生得分"
                    ], className="text-warning mb-3"),
                    
                    # 数据导入区域
                    dbc.Card([
                        dbc.CardHeader("📁 小题数据导入", className="bg-info text-white"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dcc.Upload(
                                        id="upload_question_data",
                                        children=html.Div([
                                            "📊 上传小题数据文件",
                                            html.Br(),
                                            html.Small("Excel/CSV格式", className="text-muted")
                                        ]),
                                        style={
                                            "width": "100%",
                                            "height": "80px",
                                            "lineHeight": "30px",
                                            "borderWidth": "2px",
                                            "borderStyle": "dashed",
                                            "borderRadius": "5px",
                                            "textAlign": "center",
                                            "margin": "10px 0",
                                            "backgroundColor": "#f8f9fa",
                                            "cursor": "pointer"
                                        },
                                        multiple=False
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Div(id="question_upload_status", className="mt-2")
                                ], width=6)
                            ]),
                            html.Div(id="question_data_info", className="mt-3")
                        ])
                    ], className="mb-3"),
                    
                    # 分析控制区域
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "🚀 开始分析",
                                id="analyze_question_btn",
                                color="primary",
                                size="lg",
                                className="w-100",
                                n_clicks=0,
                                disabled=True  # 初始禁用，等待数据导入
                            )
                        ])
                    ])
                ]
            )
        ],
        className="mb-4"
    )


def create_question_analysis_results_panel():
    """
    创建小题分析结果面板
    
    Returns:
        dbc.Card: 结果面板组件
    """
    return dbc.Card(
        [
            dbc.CardHeader("📊 小题分析结果"),
            dbc.CardBody(
                [
                    html.Div(id="question_analysis_status"),
                    
                    # 统计概览
                    html.Div(id="question_summary_stats", className="mb-4"),
                    
                    # 分析图表
                    dcc.Graph(
                        id="question_analysis_chart",
                        style={"height": "600px"}
                    ),
                    
                    # 详细数据表格
                    html.Div(id="question_details_table", className="mt-4"),
                ]
            )
        ],
        className="mb-4"
    )


def safe_divide(numerator, denominator, default=0):
    """安全的除法运算，避免除零错误"""
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default