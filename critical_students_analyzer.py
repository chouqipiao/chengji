#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临界生分析模块
分析特控线和本科线附近±5分范围内的学生
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


class CriticalStudentsAnalyzer:
    """临界生分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化临界生分析器
        
        Args:
            df: 原始数据框
        """
        self.df = df.copy()
        self.valid_data = None
        self._filter_valid_data()
    
    def _filter_valid_data(self):
        """过滤出有效数据（缺考为'否'）"""
        if '缺考' in self.df.columns:
            self.valid_data = self.df[self.df['缺考'] == '否'].copy()
        else:
            self.valid_data = self.df.copy()
        logger.info(f"有效数据量: {len(self.valid_data)}")
    
    def analyze_critical_students(self, special_line: float = 80.0, bachelor_line: float = 60.0, subject_column: str = None):
        """
        分析临界生情况
        
        Args:
            special_line: 特控线分数
            bachelor_line: 本科线分数
            subject_column: 指定分析的学科列名（None表示使用总分）
            
        Returns:
            dict: 分析结果
        """
        if self.valid_data is None or len(self.valid_data) == 0:
            return None
        
        # 确定分析的分数列
        score_col = None
        
        # 如果指定了学科列，优先使用
        if subject_column and subject_column in self.valid_data.columns:
            score_col = subject_column
            logger.info(f"使用指定学科列: {subject_column}")
        else:
            # 优先查找总分列
            for col in ['等级赋分', '总分', '新高考总分']:
                if col in self.valid_data.columns:
                    score_col = col
                    break
            
            # 如果没找到标准名称，尝试查找其他可能的分数列
            if score_col is None:
                exclude_keywords = ['姓名', '学号', '班', '校', '县', '排名', '排', '等级', '选科', '准考证', '考生', '缺考']
                for col in self.valid_data.columns:
                    if not any(exclude in col for exclude in exclude_keywords):
                        try:
                            # 尝试转换为数字
                            numeric_data = pd.to_numeric(self.valid_data[col], errors='coerce')
                            if not numeric_data.isna().all():
                                # 检查是否像总分（数值较大）
                                non_null_data = numeric_data.dropna()
                                if len(non_null_data) > 0 and non_null_data.max() > 50:
                                    score_col = col
                                    logger.info(f"自动检测到分数列: {col}")
                                    break
                        except:
                            continue
        
        if score_col is None:
            logger.error("未找到分数列（等级赋分/总分/新高考总分）")
            logger.warning("可用的列名: " + str(list(self.valid_data.columns)))
            return None
        
        scores = self.valid_data[score_col].astype(float)
        
        # 四类临界生分析
        special_above = self.valid_data[(scores > special_line) & (scores <= special_line + 5)]
        special_below = self.valid_data[(scores < special_line) & (scores >= special_line - 5)]
        bachelor_above = self.valid_data[(scores > bachelor_line) & (scores <= bachelor_line + 5)]
        bachelor_below = self.valid_data[(scores < bachelor_line) & (scores >= bachelor_line - 5)]
        
        results = {
            'total_valid': len(self.valid_data),
            'special_line': special_line,
            'bachelor_line': bachelor_line,
            'special_above': {
                'count': len(special_above),
                'students': special_above.to_dict('records') if len(special_above) > 0 else [],
                'percentage': len(special_above) / len(self.valid_data) * 100
            },
            'special_below': {
                'count': len(special_below),
                'students': special_below.to_dict('records') if len(special_below) > 0 else [],
                'percentage': len(special_below) / len(self.valid_data) * 100
            },
            'bachelor_above': {
                'count': len(bachelor_above),
                'students': bachelor_above.to_dict('records') if len(bachelor_above) > 0 else [],
                'percentage': len(bachelor_above) / len(self.valid_data) * 100
            },
            'bachelor_below': {
                'count': len(bachelor_below),
                'students': bachelor_below.to_dict('records') if len(bachelor_below) > 0 else [],
                'percentage': len(bachelor_below) / len(self.valid_data) * 100
            }
        }
        
        logger.info(f"临界生分析完成 - 特控线上5分: {results['special_above']['count']}人, "
                   f"特控线下5分: {results['special_below']['count']}人, "
                   f"本科线上5分: {results['bachelor_above']['count']}人, "
                   f"本科线下5分: {results['bachelor_below']['count']}人")
        
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
        
        categories = ['特控线上5分', '特控线下5分', '本科线上5分', '本科线下5分']
        counts = [
            results['special_above']['count'],
            results['special_below']['count'],
            results['bachelor_above']['count'],
            results['bachelor_below']['count']
        ]
        percentages = [
            results['special_above']['percentage'],
            results['special_below']['percentage'],
            results['bachelor_above']['percentage'],
            results['bachelor_below']['percentage']
        ]
        
        # 创建子图
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
                marker=dict(
                    color=['#28a745', '#ffc107', '#17a2b8', '#dc3545'],
                    line=dict(color='#ffffff', width=2),
                    pattern_shape="/",
                    pattern_size=8,
                    pattern_fillmode="replace"
                ),
                text=counts,
                textposition='auto',
                textfont=dict(size=12, color='white'),
                hovertemplate='<b>%{x}</b><br>人数: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 饼图
        fig.add_trace(
            go.Pie(
                labels=categories,
                values=counts,
                name='比例',
                marker=dict(
                    colors=['#28a745', '#ffc107', '#17a2b8', '#dc3545'],
                    line=dict(color='#ffffff', width=3)
                ),
                textinfo='label+percent+value',
                textfont=dict(size=11),
                hovertemplate='<b>%{label}</b><br>人数: %{value}<br>占比: %{percent}<extra></extra>',
                pull=[0.05, 0.05, 0.05, 0.05]
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title={
                'text': "临界生分析结果",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            showlegend=True,
            height=450,
            margin=dict(t=60, b=40, l=40, r=20)
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
        
        if show_details:
            # 特控线上5分
            for student in results['special_above']['students']:
                table_data.append({
                    '类型': '特控线上5分',
                    '姓名': student.get('姓名', ''),
                    '学校': student.get('学校', ''),
                    '班级': student.get('行政班', ''),
                    '分数': student.get('等级赋分', student.get('总分', student.get('新高考总分', ''))),
                    '区县': student.get('区县', '')
                })
            
            # 特控线下5分
            for student in results['special_below']['students']:
                table_data.append({
                    '类型': '特控线下5分',
                    '姓名': student.get('姓名', ''),
                    '学校': student.get('学校', ''),
                    '班级': student.get('行政班', ''),
                    '分数': student.get('等级赋分', student.get('总分', student.get('新高考总分', ''))),
                    '区县': student.get('区县', '')
                })
            
            # 本科线上5分
            for student in results['bachelor_above']['students']:
                table_data.append({
                    '类型': '本科线上5分',
                    '姓名': student.get('姓名', ''),
                    '学校': student.get('学校', ''),
                    '班级': student.get('行政班', ''),
                    '分数': student.get('等级赋分', student.get('总分', student.get('新高考总分', ''))),
                    '区县': student.get('区县', '')
                })
            
            # 本科线下5分
            for student in results['bachelor_below']['students']:
                table_data.append({
                    '类型': '本科线下5分',
                    '姓名': student.get('姓名', ''),
                    '学校': student.get('学校', ''),
                    '班级': student.get('行政班', ''),
                    '分数': student.get('等级赋分', student.get('总分', student.get('新高考总分', ''))),
                    '区县': student.get('区县', '')
                })
        
        return table_data


# UI相关函数已移至 critical_students_ui.py
# 这里保留纯分析逻辑


def safe_divide(numerator, denominator, default=0):
    """安全的除法运算，避免除零错误"""
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default