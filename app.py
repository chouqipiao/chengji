#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教师专用成绩分析系统 - 主应用
基于Dash构建交互式仪表板
"""

# 修复orjson循环导入问题
try:
    import orjson

    # 预先访问关键属性以避免循环导入错误
    _ = orjson.OPT_NON_STR_KEYS
except (ImportError, AttributeError) as e:
    if "orjson" in str(e) and "OPT_NON_STR_KEYS" in str(e):
        print("⚠️ orjson循环导入问题检测到，将使用标准json模块")
        import sys

        if "orjson" in sys.modules:
            del sys.modules["orjson"]
    else:
        pass

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np

import base64
from io import StringIO
import os
from datetime import datetime
import json
import sys


import logging
from typing import Optional

# 导入自定义模块
from data_processor import DataProcessor
from quadrant_analyzer import (
    QuadrantAnalyzer,
    create_quadrant_control_panel,
    create_quadrant_results_panel,
)

from comprehensive_analyzer import (
    ComprehensiveAnalyzer,
    create_comprehensive_control_panel,
    create_comprehensive_results_panel,
    register_comprehensive_callbacks,
)

from cascade_statistics_analyzer import (
    CascadeStatisticsAnalyzer,
    create_cascade_control_panel,
    create_cascade_results_panel,
    register_cascade_callbacks,
)

from effective_group_analyzer import EffectiveGroupAnalyzer
from effective_group_ui import (
    create_effective_group_control_panel,
    create_effective_group_results_panel,
)
from effective_group_callbacks import register_effective_group_callbacks

# 导入目标完成统计模块
from goal_completion_analyzer import GoalCompletionAnalyzer
from goal_completion_ui import (
    create_goal_completion_control_panel,
    create_goal_completion_results_panel,
)
from goal_completion_callbacks import register_goal_completion_callbacks

# 导入新增分析模块
from critical_students_analyzer import CriticalStudentsAnalyzer
from top_students_analyzer import TopStudentsAnalyzer
from question_analysis_analyzer import QuestionAnalysisAnalyzer
from new_analysis_ui import (
    create_critical_students_tab,
    create_top_students_tab,
    create_question_analysis_tab
)
from new_analysis_callbacks import register_new_analysis_callbacks

# 导入四象限分析回调函数
from quadrant_analyzer import register_quadrant_callbacks

# 数据库功能已移除
DATABASE_AVAILABLE = False

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def filter_columns_for_analysis(columns):
    """
    过滤掉不需要分析的字段
    排除：区县、学校、行政班、考生号、姓名、选科组合、准考证号、考生类型、等级等
    """
    exclude_keywords = [
        "区县",
        "学校",
        "行政班",
        "考生号",
        "姓名",
        "选科组合",
        "准考证号",
        "考生类型",
        "等级",
    ]
    return [
        col
        for col in columns
        if not any(exclude in col for exclude in exclude_keywords)
    ]


def filter_columns_for_grouping(columns):
    """
    分组列专用过滤函数
    只保留：区县、学校、行政班、考生号、姓名、选科组合、准考证号、考生类型
    """
    allowed_keywords = ["区县", "学校", "行政班", "选科组合", "准考证号"]
    return [
        col for col in columns if any(allowed in col for allowed in allowed_keywords)
    ]


def filter_administrative_columns(columns):
    """
    行政列专用过滤函数
    返回：区县、学校、行政班相关的列名
    """
    admin_keywords = ["区县", "学校", "行政班"]
    return [col for col in columns if any(keyword in col for keyword in admin_keywords)]


def get_administrative_columns(df):
    """
    获取数据框中的行政层级列
    返回格式：{level: column_name}
    """
    admin_columns = {}
    for col in df.columns:
        if "区县" in col:
            admin_columns["county"] = col
        elif "学校" in col:
            admin_columns["school"] = col
        elif "行政班" in col:
            admin_columns["class"] = col
    return admin_columns


# 初始化Dash应用
app = dash.Dash(
    __name__,
    # 指定静态文件夹为static文件夹
    assets_folder="static",
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css",
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
    ],
    external_scripts=[
        # 使用稳定版本的Plotly.js - 更轻量的版本
        "https://cdn.plot.ly/plotly-2.25.2.min.js",
        # 备用CDN以防主CDN失败
        "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.25.2/plotly.min.js",
    ],
    suppress_callback_exceptions=True,
    # 减少客户端警告
    show_undo_redo=False,
    # 确保Plotly属性不被传递到DOM
    meta_tags=[
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1.0",
        },
        {"http-equiv": "X-UA-Compatible", "content": "IE=edge"},
    ],
    # 添加渲染器配置以兼容Dash 3.x
    title="高要区成绩分析系统",
)

# 使用默认的Dash index_string（通过CDN加载Bootstrap）


# Plotly.js 错误处理和重载机制
plotly_fallback_script = html.Script(
    """
    // 处理浏览器跟踪防护和Plotly.js错误
    (function() {
        let plotlyLoadAttempts = 0;
        const maxPlotlyAttempts = 5;
        const plotlyLoadInterval = 2000;
        
        // 静默处理跟踪防护和Plotly版本警告
        const originalWarn = console.warn;
        console.warn = function(...args) {
            const message = args[0] && typeof args[0] === 'string' ? args[0] : '';
            if (message.includes('Tracking Prevention') || 
                message.includes('plotly-latest') ||
                message.includes('plotly-2.') ||
                message.includes('NO LONGER the latest') ||
                message.includes('update your links')) {
                return; // 静默处理这些警告
            }
            originalWarn.apply(console, args);
        };
        
        // 静默处理跟踪防护错误
        window.addEventListener('error', function(e) {
            if (e.message && e.message.includes('Tracking Prevention')) {
                e.preventDefault();
                return true; // 阻止错误传播
            }
        });
        
        function checkPlotlyAndReload() {
            plotlyLoadAttempts++;
            
            // 检查Plotly是否正确加载
            try {
                if (typeof Plotly === 'undefined' || !Plotly.react) {
                    console.warn(`⚠️ Plotly未正确加载 (尝试 ${plotlyLoadAttempts}/${maxPlotlyAttempts})`);
                    
                        // 尝试加载更稳定的Plotly版本
                        const script = document.createElement('script');
                        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.26.0/plotly.min.js';
                        script.onerror = function() {
                            console.warn('CDN加载失败，尝试另一个源');
                            const backupScript = document.createElement('script');
                            backupScript.src = 'https://unpkg.com/plotly.js@2.26.0/dist/plotly.min.js';
                            document.head.appendChild(backupScript);
                        };
                        document.head.appendChild(script);
                        
                        setTimeout(checkPlotlyAndReload, plotlyLoadInterval);
                    } else {
                        console.warn('图表功能可能受限，但其他功能正常');
                    }
                } else {
                    console.log('✅ 图表库加载正常');
                }
            } catch (error) {
                console.warn('检查图表库时出错:', error.message);
            }
        }
        
        // 页面加载完成后开始检查
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                setTimeout(checkPlotlyAndReload, 1000);
            });
        } else {
            setTimeout(checkPlotlyAndReload, 1000);
        }
        
        // 处理其他JavaScript错误（特别是TypeError）
        window.addEventListener('error', function(e) {
            // 过滤掉已知的无害错误
            if (e.message && (
                e.message.includes('Cannot set properties of null') ||
                e.message.includes('plotly') ||
                e.message.includes('Tracking Prevention')
            )) {
                e.preventDefault();
                return true;
            }
        });
        
        // 安全的存储访问
        window.safeStorage = {
            get: function(key) {
                try {
                    return localStorage.getItem(key);
                } catch (e) {
                    if (!window.memoryStorage) window.memoryStorage = {};
                    return window.memoryStorage[key];
                }
            },
            set: function(key, value) {
                try {
                    localStorage.setItem(key, value);
                } catch (e) {
                    if (!window.memoryStorage) window.memoryStorage = {};
                    window.memoryStorage[key] = value;
                }
            }
        };
    })();
"""
)


# 全局数据存储
class DataStore:
    def __init__(self):
        self.df = None
        self.processor: Optional["DataProcessor"] = None
        self.quadrant_analyzer: Optional["QuadrantAnalyzer"] = None
        self.comprehensive_analyzer: Optional["ComprehensiveAnalyzer"] = None
        self.cascade_analyzer: Optional["CascadeStatisticsAnalyzer"] = None
        self.effective_group_analyzer: Optional["EffectiveGroupAnalyzer"] = None
        self.goal_completion_analyzer: Optional["GoalCompletionAnalyzer"] = None
        self.critical_students_analyzer: Optional["CriticalStudentsAnalyzer"] = None
        self.top_students_analyzer: Optional["TopStudentsAnalyzer"] = None
        self.question_analysis_analyzer: Optional["QuestionAnalysisAnalyzer"] = None
        self.question_df = None  # 小题数据单独存储
        self.raw_data_id = None  # 原始数据在数据库中的ID
        self.analysis_results = {}  # 存储各种分析的结果

    def get_current_data(self):
        """获取当前数据"""
        return self.df
    
    def get_question_data(self):
        """获取小题数据"""
        return self.question_df
    
    def set_question_data(self, df):
        """设置小题数据"""
        self.question_df = df
    
    def get_analyzer(self, analyzer_type):
        """获取指定类型的分析器"""
        return getattr(self, f"{analyzer_type}_analyzer", None)
    
    def get_analysis_results(self, analysis_type):
        """获取指定类型的分析结果"""
        return self.analysis_results.get(analysis_type, {})
    
    def store_analysis_results(self, analysis_type, results):
        """存储分析结果"""
        self.analysis_results[analysis_type] = results


data_store = DataStore()

# 自动寻找可用端口
# 调试静态文件配置
import os
print(f"🔧 Dash应用静态文件夹配置:")
print(f"   assets_folder: static")
print(f"   当前工作目录: {os.getcwd()}")
print(f"   static文件夹存在: {os.path.exists('static')}")
if os.path.exists('static'):
    print(f"   static文件夹内容: {os.listdir('static')}")
    if 'logo.jpg' in os.listdir('static'):
        print(f"   logo.jpg存在: ✅")
        print(f"   logo.jpg大小: {os.path.getsize('static/logo.jpg') / 1024:.1f} KB")
    else:
        print(f"   logo.jpg存在: ❌")

# 版权信息区域
copyright_footer = html.Div([
    html.Hr(style={"margin": "2rem 0", "borderColor": "#dee2e6"}),
    html.Div([
        html.P([
            "本系统由 ", 
            html.Div(
                className="hover-container",
                style={
                    "position": "relative",
                    "display": "inline-block",
                    "margin": "0",
                    "verticalAlign": "middle"
                },
                children=[
                    html.Span(
                        "生物微讲堂", 
                        id="brand-text",
                        style={
                            "fontWeight": "bold",
                            "color": "#007bff",
                            "fontSize": "1.1em",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease"
                        }
                    ),
                    html.Div(
                        className="qr-popup",
                        style={
                            "position": "absolute",
                            "bottom": "100%",
                            "left": "50%",
                            "transform": "translateX(-50%)",
                            "backgroundColor": "white",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                            "zIndex": "9999",
                            "opacity": "0",
                            "visibility": "hidden",
                            "transition": "all 0.3s ease",
                            "marginBottom": "10px",
                            "border": "1px solid #e9ecef",
                            "minWidth": "170px",
                            "textAlign": "center"
                        },
                        children=[
                            html.Img(
                                src="/static/logo.jpg",
                                alt="生物微讲堂二维码",
                                style={
                                    "width": "150px",
                                    "height": "150px",
                                    "borderRadius": "8px",
                                    "boxShadow": "0 4px 8px rgba(0,0,0,0.1)",
                                    "display": "block"
                                }
                            ),
                            html.P(
                                "扫码关注",
                                style={
                                    "margin": "5px 0 0 0",
                                    "fontSize": "14px",
                                    "color": "#666"
                                }
                            )
                        ]
                    )
                ]
            ),
            " 开发制作"
            ], 
            className="text-center text-muted mb-0",
            style={"fontSize": "0.9em", "marginBottom": "0"}
        )
    ], className="text-center py-3", style={"backgroundColor": "#f8f9fa"}),
    
    html.Script("""
        console.log('🚀 防冲突悬停脚本开始执行...');
        
        // 使用更强的CSS选择器和更高优先级来避免Dash框架冲突
        const css = `
            /* 使用更高优先级的选择器来覆盖Dash样式 */
            div.hover-container {
                position: relative !important;
                display: inline-block !important;
                margin: 0 !important;
                vertical-align: middle !important;
                z-index: 1 !important;
            }
            
            /* 确保brand-text样式不被覆盖 */
            div.hover-container > span#brand-text,
            span#brand-text {
                font-weight: bold !important;
                color: #007bff !important;
                font-size: 1.1em !important;
                cursor: pointer !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                display: inline-block !important;
                padding: 2px 6px !important;
                border-radius: 4px !important;
                position: relative !important;
                z-index: 2 !important;
            }
            
            div.hover-container:hover > span#brand-text:hover,
            span#brand-text:hover {
                color: #0056b3 !important;
                background-color: rgba(0,123,255,0.15) !important;
                transform: scale(1.08) !important;
                box-shadow: 0 2px 8px rgba(0,123,255,0.3) !important;
            }
            
            /* 二维码弹窗样式 - 使用最高优先级 */
            div.hover-container > div.qr-popup,
            div.qr-popup {
                position: absolute !important;
                bottom: calc(100% + 5px) !important;
                left: 50% !important;
                transform: translateX(-50%) scale(0.95) !important;
                background: #ffffff !important;
                padding: 12px !important;
                border-radius: 12px !important;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2) !important;
                border: 1px solid #e3e6ea !important;
                z-index: 99999 !important;
                opacity: 0 !important;
                visibility: hidden !important;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
                margin: 0 !important;
                min-width: 180px !important;
                text-align: center !important;
                pointer-events: none !important;
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
            }
            
            /* 三角箭头 - 双层设计更清晰 */
            div.qr-popup::before {
                content: '' !important;
                position: absolute !important;
                top: 100% !important;
                left: 50% !important;
                transform: translateX(-50%) translateY(-1px) !important;
                border: 10px solid transparent !important;
                border-top-color: #ffffff !important;
                z-index: 2 !important;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)) !important;
            }
            
            div.qr-popup::after {
                content: '' !important;
                position: absolute !important;
                top: calc(100% + 1px) !important;
                left: 50% !important;
                transform: translateX(-50%) translateY(-1px) !important;
                border: 9px solid transparent !important;
                border-top-color: #e3e6ea !important;
                z-index: 1 !important;
            }
            
            /* 悬停显示效果 - 更平滑的动画 */
            div.hover-container:hover > div.qr-popup,
            div.qr-popup.show {
                opacity: 1 !important;
                visibility: visible !important;
                transform: translateX(-50%) translateY(-8px) scale(1) !important;
                pointer-events: auto !important;
            }
            
            /* 图片样式优化 */
            div.qr-popup img {
                width: 160px !important;
                height: 160px !important;
                border-radius: 10px !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.15) !important;
                display: block !important;
                margin: 0 auto !important;
                transition: transform 0.3s ease !important;
            }
            
            div.qr-popup img:hover {
                transform: scale(1.05) !important;
            }
            
            /* 文字说明样式 */
            div.qr-popup p {
                margin: 8px 0 0 0 !important;
                font-size: 13px !important;
                color: #6c757d !important;
                font-weight: 500 !important;
                letter-spacing: 0.5px !important;
            }
            
            /* 防止被其他样式覆盖 */
            div.qr-popup * {
                box-sizing: border-box !important;
            }
        `;
        
        // 创建高优先级样式表
        function createHighPriorityStyle() {
            const style = document.createElement('style');
            style.type = 'text/css';
            style.id = 'qr-hover-override';
            style.textContent = css;
            
            // 尝试插入到head的最后面，确保高优先级
            if (document.head) {
                document.head.appendChild(style);
            } else {
                // 如果head还不存在，等待DOM加载
                document.addEventListener('DOMContentLoaded', () => {
                    document.head.appendChild(style);
                });
            }
            
            return style;
        }
        
        // 图片加载检测和错误处理 - 彻底改进版
        function initImageFallback() {
            console.log('🔍 开始彻底检查图片加载...');
            console.log('📍 当前页面URL:', window.location.href);
            console.log('📍 当前Origin:', window.location.origin);
            
            // 等待DOM完全加载
            setTimeout(() => {
                const images = document.querySelectorAll('.qr-popup img');
                console.log(`找到 ${images.length} 个二维码图片`);
                
                if (images.length === 0) {
                    console.error('❌ 没有找到任何二维码图片，可能DOM结构有问题');
                    return;
                }
                
                images.forEach((img, index) => {
                    console.log(`=== 二维码图片 ${index + 1} 详细信息 ===`);
                    console.log('📍 当前src:', img.src);
                    console.log('📍 naturalWidth:', img.naturalWidth);
                    console.log('📍 naturalHeight:', img.naturalHeight);
                    console.log('📍 complete:', img.complete);
                    console.log('📍 parentNode:', img.parentNode);
                    console.log('📍 className:', img.className);
                    
                    // 强制重新加载图片，确保不是缓存问题
                    const timestamp = new Date().getTime();
                    
                    // 设置图片加载失败的备用路径
                    const fallbackPaths = [
                        `/static/logo.jpg?t=${timestamp}`,  // 带时间戳防止缓存
                        `${window.location.origin}/static/logo.jpg?t=${timestamp}`,
                        `./static/logo.jpg?t=${timestamp}`,
                        `static/logo.jpg?t=${timestamp}`,
                        `/static/logo.jpg?t=${timestamp}`,  # 备用路径
                        '/static/logo.jpg',  // 最后尝试不带时间戳的版本
                        'static/logo.jpg'
                    ];
                    let currentPathIndex = 0;
                    let hasLoaded = false;
                    
                    const tryNextPath = () => {
                        if (currentPathIndex < fallbackPaths.length && !hasLoaded) {
                            const newPath = fallbackPaths[currentPathIndex];
                            console.log(`📁 尝试路径 ${currentPathIndex + 1}: ${newPath}`);
                            currentPathIndex++;
                            
                            // 先检查网络请求是否能成功
                            const testImg = new Image();
                            testImg.onload = function() {
                                console.log(`✅ 路径测试成功: ${newPath}`);
                                img.src = newPath;
                                hasLoaded = true;
                            };
                            testImg.onerror = function() {
                                console.warn(`⚠️ 路径测试失败: ${newPath}`);
                                setTimeout(tryNextPath, 100);
                            };
                            testImg.src = newPath;
                        } else if (!hasLoaded) {
                            console.error('❌ 所有图片路径都加载失败');
                            showImageError(img);
                        }
                    };
                    
                    img.onload = function() {
                        console.log(`🎉 二维码图片最终加载成功: ${img.src}`);
                        console.log(`📏 图片尺寸: ${img.naturalWidth}x${img.naturalHeight}`);
                        
                        // 移除任何错误显示
                        const errorDiv = img.parentNode.querySelector('[data-error-placeholder]');
                        if (errorDiv) {
                            errorDiv.remove();
                        }
                        
                        // 添加加载成功动画
                        img.style.animation = 'fadeIn 0.5s ease';
                        img.style.border = '2px solid #28a745';
                        setTimeout(() => {
                            img.style.border = 'none';
                        }, 1000);
                    };
                    
                    img.onerror = function() {
                        console.warn(`⚠️ 图片加载失败: ${img.src}`);
                        if (!hasLoaded) {
                            setTimeout(tryNextPath, 200);
                        }
                    };
                    
                    // 开始尝试第一个路径
                    tryNextPath();
                });
            }, 2000); // 增加等待时间，确保Dash完全渲染
        }
        
        // 显示图片加载错误占位符
        function showImageError(img) {
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.innerHTML = `
                <div style="
                    color: #dc3545; 
                    font-size: 11px; 
                    padding: 15px; 
                    border: 2px dashed #dc3545; 
                    border-radius: 8px;
                    background: #f8d7da;
                    text-align: center;
                    margin: 10px 0;
                ">
                    <strong>二维码加载失败</strong><br>
                    <small>请检查 static/logo.jpg 文件</small>
                </div>
            `;
            img.parentNode.insertBefore(placeholder, img);
        }
        
        // 添加淡入动画
        const animationCSS = `
            @keyframes fadeIn {
                from { opacity: 0; transform: scale(0.9); }
                to { opacity: 1; transform: scale(1); }
            }
        `;
        
        // 初始化函数 - 防冲突版本
        let isInitialized = false;
        function initHoverEffect() {
            // 防止重复初始化
            if (isInitialized) {
                console.log('⚠️ 悬停效果已初始化，跳过重复调用');
                return;
            }
            
            console.log('🚀 初始化防冲突悬停效果');
            
            // 创建样式表
            createHighPriorityStyle();
            
            // 添加动画样式
            const animStyle = document.createElement('style');
            animStyle.textContent = animationCSS;
            document.head.appendChild(animStyle);
            
            // 初始化图片
            initImageFallback();
            
            isInitialized = true;
            console.log('✅ 防冲突悬停功能初始化完成');
        }
        
        // 多重初始化机制，确保在所有环境下都能正常工作
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initHoverEffect);
        } else {
            // 如果DOM已经加载完成，立即初始化
            initHoverEffect();
        }
        
        // 备用初始化 - 等待Dash完全渲染（只保留一次）
        setTimeout(initHoverEffect, 2000);
        
        // 监听Dash路由变化（如果是多页面应用）
        window.addEventListener('popstate', function() {
            setTimeout(initHoverEffect, 1000);
        });
        
        console.log('🎯 防冲突悬停脚本加载完成');
    """)
])

# 应用布局
app.layout = html.Div([
    dbc.Container(
        [
            # JavaScript脚本
            plotly_fallback_script,
            # 标题栏
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H1(
                                        "📊 高要区成绩分析系统",
                                        className="text-center my-4 text-primary d-inline-block",
                                    ),
                                    html.A(
                                        "📖 使用指南",
                                        href="/static/system_guide.html",
                                        target="_blank",
                                        className="btn btn-outline-primary btn-sm ms-3",
                                        style={
                                            "fontSize": "0.8rem",
                                            "verticalAlign": "middle",
                                            "textDecoration": "none"
                                        }
                                    ),
                                ],
                                className="text-center position-relative"
                            ),
                            html.Hr(),
                        ]
                    )
                ]
            ),
            # 数据上传区域
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("📁 数据导入"),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dcc.Upload(
                                                                id="upload_data",
                                                                children=html.Div(
                                                                    [
                                                                        "上传Excel/CSV文件",
                                                                        html.Br(),
                                                                        html.Small(
                                                                            "支持 .xlsx, .xls, .csv 格式"
                                                                        ),
                                                                    ]
                                                                ),
                                                                style={
                                                                    "width": "100%",
                                                                    "height": "100px",
                                                                    "lineHeight": "30px",
                                                                    "borderWidth": "2px",
                                                                    "borderStyle": "dashed",
                                                                    "borderRadius": "5px",
                                                                    "textAlign": "center",
                                                                    "margin": "10px 0",
                                                                    "backgroundColor": "#f8f9fa",
                                                                },
                                                                multiple=False,
                                                            )
                                                        ],
                                                        width=2,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                id="upload_status",
                                                                style={"marginTop": "10px"},
                                                            )
                                                        ],
                                                        width=2,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                id="column_names_display",
                                                                style={"marginTop": "10px"},
                                                            )
                                                        ],
                                                        width=8,
                                                    ),
                                                ]
                                            )
                                        ]
                                    ),
                                ],
                                className="mb-4",
                            )
                        ]
                    )
                ]
            ),
            # 标签页导航
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Tabs(
                                [
                                    dbc.Tab(label="📈 数据概览", tab_id="overview"),
                                    dbc.Tab(label="🔍 综合分析", tab_id="comprehensive"),
                                    dbc.Tab(label="📐 四象限分析", tab_id="quadrant"),
                                    dbc.Tab(label="📊 三级联动统计", tab_id="cascade"),
                                    dbc.Tab(
                                        label="🎯 有效群体统计",
                                        tab_id="effective_group",
                                    ),
                                    dbc.Tab(
                                        label="🎯 目标完成统计",
                                        tab_id="goal_completion",
                                    ),
                                    dbc.Tab(label="🎯 临界生分析", tab_id="critical_students"),
                                    dbc.Tab(label="🏆 尖子生分析", tab_id="top_students"),
                                    dbc.Tab(label="📝 学科小题分析", tab_id="question_analysis"),

                                ],
                                id="tabs",
                                active_tab="overview",
                                className="nav-tabs",
                            )
                        ]
                    )
                ]
            ),
            html.Div(id="tab_content", className="mt-4"),
            # 隐藏的组件（用于回调）
            # 说明: 这里的组件不直接展示给用户，用作回调中的状态承载或跨模块通信。
            # - 保持 id 不变以兼容现有回调
            # - 对于 screen-reader 可访问性，将其标记为 aria-hidden
            html.Div(
                [
                    html.Button(
                        "run-quadrant-btn-hidden",
                        id="run_quadrant_btn",
                        style={"display": "none"},
                    ),
                    html.Div(id="quadrant_output", style={"display": "none"}),
                    html.Div(id="comprehensive_output", style={"display": "none"}),
                    # Comprehensive Analyzer 组件
                    html.Div(id="enhanced_selection_info", style={"display": "none"}),
                    html.Div(id="performance_results", style={"display": "none"}),
                    html.Div(id="admission_rate_stats", style={"display": "none"}),
                    html.Div(id="aggregation_table", style={"display": "none"}),
                    html.Div(id="comparison_chart", style={"display": "none"}),

                    html.Div(id="admission_rate_chart", style={"display": "none"}),
                    html.Div(id="subject_indicators_table", style={"display": "none"}),
                    html.Div(id="class_radar_chart", style={"display": "none"}),

                    # Quadrant Analyzer 组件
                    html.Div(id="quadrant_chart", style={"display": "none"}),
                    html.Div(id="quadrant_summary", style={"display": "none"}),
                    html.Div(id="quadrant_details", style={"display": "none"}),
                    # Comprehensive Analyzer 必要的隐藏组件（不在UI中显示的）
                    dcc.Input(id="outlier_threshold", style={"display": "none"}),
                    dcc.Input(id="min_sample_size", style={"display": "none"}),
                    # Quadrant Analyzer 输入组件
                    dcc.Dropdown(id="quadrant_analysis_type", style={"display": "none"}),
                    dcc.Dropdown(id="quadrant-subject-dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="quadrant-total-dropdown", style={"display": "none"}),
                    # 四象限分析模块专用组件
                    dcc.RadioItems(id="quadrant_analysis_level_radio", style={"display": "none"}),
                    dcc.Dropdown(id="quadrant_county_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="quadrant_school_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="quadrant_class_dropdown", style={"display": "none"}),
                    dcc.Checklist(id="quadrant_options", style={"display": "none"}),

                    dcc.Dropdown(
                        id="outlier_method",
                        options=[
                            {"label": "Z-Score", "value": "zscore"},
                            {"label": "IQR", "value": "iqr"},
                            {"label": "Isolation Forest", "value": "isolation"},
                        ],
                        value="zscore",
                        style={"display": "none"},
                    ),

                    # 三级联动统计模块专用组件
                    dcc.Dropdown(id="cascade_county_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="cascade_school_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="cascade_class_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="cascade_category_dropdown", style={"display": "none"}),
                    html.Button("hidden", id="clear_cascade_selection_btn", style={"display": "none"}),
                    html.Button("hidden", id="generate_school_stats_btn", style={"display": "none"}),
                    html.Button("hidden", id="generate_class_stats_btn", style={"display": "none"}),
                    html.Button("hidden", id="generate_combination_stats_btn", style={"display": "none"}),
                    html.Div(id="school_stats_table_container", style={"display": "none"}),
                    html.Div(id="class_stats_table_container", style={"display": "none"}),
                    html.Div(id="combination_stats_table_container", style={"display": "none"}),
                    html.Div(id="cascade_filters_div", style={"display": "none"}),
                    html.Div(id="advanced_thresholds_div", style={"display": "none"}),
                    html.Div(id="metrics_list", style={"display": "none"}),
                    # 自定义指标相关组件
                    dcc.Input(id="new_metric_name", style={"display": "none"}),
                    dcc.Input(id="new_metric_subject", style={"display": "none"}),
                    dcc.Input(id="new_metric_total", style={"display": "none"}),
                    html.Button("hidden", id="add_metric_btn", style={"display": "none"}),
                    html.Button(
                        "hidden", id="reset_metrics_btn", style={"display": "none"}
                    ),
                    html.Button(
                        "hidden",
                        id="add_undergraduate_btn",
                        style={"display": "none"},
                    ),
                    html.Button("hidden", id="add_special_btn", style={"display": "none"}),
                    html.Button("hidden", id="add_key_btn", style={"display": "none"}),
                    html.Button("hidden", id="add_basic_btn", style={"display": "none"}),
                    html.Button(
                        "hidden",
                        id="generate_report_btn",
                        style={"display": "none"},
                    ),
                    # 有效群体统计模块专用组件
                    dcc.Dropdown(id="effective_group_total_column", style={"display": "none"}),
                    dcc.Dropdown(id="effective_group_comparison_subjects", style={"display": "none"}),
                    dcc.Input(id="effective_group_undergraduate_threshold", style={"display": "none"}),
                    dcc.Input(id="effective_group_special_threshold", style={"display": "none"}),
                    dcc.Input(id="effective_group_custom_name", style={"display": "none"}),
                    dcc.Input(id="effective_group_custom_score", style={"display": "none"}),
                    html.Button("hidden", id="effective_group_add_threshold", style={"display": "none"}),
                    html.Button("hidden", id="effective_group_clear_thresholds", style={"display": "none"}),
                    html.Button("hidden", id="effective_group_analyze_btn", style={"display": "none"}),
                    dcc.Store(id="effective_group_custom_thresholds_store", data=[]),
                    dbc.Alert(id="effective_group_status_alert", style={"display": "none"}),
                    html.Div(id="effective_group_summary", style={"display": "none"}),
                    html.Div(id="effective_group_tab_content", style={"display": "none"}),
                    html.Div(id="effective_group_results_tabs", style={"display": "none"}),
                    html.Div(id="effective_group_current_thresholds", style={"display": "none"}),
                    # Report 组件
                    dcc.Checklist(id="report_options", style={"display": "none"}),
                    dcc.Input(id="report_title", style={"display": "none"}),
                    dcc.Input(id="report_author", style={"display": "none"}),
                    html.Div(id="goal_completion_results", style={"display": "none"}),
                    # 目标完成统计模块实际使用的组件
                    dcc.Input(id="undergraduate_safe_input", style={"display": "none"}),
                    dcc.Input(id="undergraduate_strive_input", style={"display": "none"}),
                    dcc.Input(id="special_control_input", style={"display": "none"}),
                    dcc.Dropdown(id="target_subject_dropdown", style={"display": "none"}),
                    dcc.Checklist(id="analysis_level_checklist", style={"display": "none"}),
                    dcc.Dropdown(id="chart_type_dropdown", style={"display": "none"}),
                    dcc.Checklist(id="show_details_checklist", style={"display": "none"}),
                    html.Button("hidden", id="analyze_goal_btn", style={"display": "none"}),

                    html.Button("hidden", id="export_data_btn", style={"display": "none"}),
                    html.Div(id="goal_stats_overview", style={"display": "none"}),
                    dcc.Graph(id="goal_completion_chart", style={"display": "none"}),
                    dcc.Graph(id="hierarchy_comparison_chart", style={"display": "none"}),
                    html.Div(id="detailed_results_table", style={"display": "none"}),
                    html.Div(id="hierarchy_stats_details", style={"display": "none"}),
                    
                    # 新增分析模块组件
                    html.Button("hidden", id="analyze_critical_btn", style={"display": "none"}),
                    html.Button("hidden", id="analyze_top_btn", style={"display": "none"}),
                    html.Button("hidden", id="analyze_question_btn", style={"display": "none"}),
                    
                    dcc.Input(id="critical_special_line", style={"display": "none"}),
                    dcc.Input(id="critical_bachelor_line", style={"display": "none"}),
                    dcc.Input(id="top_students_range", style={"display": "none"}),
                    
                    # 临界生分析新增组件
                    dcc.Dropdown(id="critical_county_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="critical_school_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="critical_class_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="critical_subject_dropdown", style={"display": "none"}),
                    
                    html.Div(id="critical_analysis_status", style={"display": "none"}),
                    html.Div(id="critical_type_stats", style={"display": "none"}),
                    html.Div(id="top_analysis_status", style={"display": "none"}),
                    html.Div(id="question_analysis_status", style={"display": "none"}),
                    
                    dcc.Graph(id="critical_analysis_chart", style={"display": "none"}),
                    dcc.Graph(id="top_analysis_chart", style={"display": "none"}),
                    dcc.Graph(id="question_analysis_chart", style={"display": "none"}),
                    
                    html.Div(id="critical_summary_stats", style={"display": "none"}),
                    html.Div(id="top_summary_stats", style={"display": "none"}),
                    html.Div(id="question_summary_stats", style={"display": "none"}),
                    
                    html.Div(id="critical_details_table", style={"display": "none"}),
                    html.Div(id="top_details_table", style={"display": "none"}),
                    html.Div(id="question_details_table", style={"display": "none"}),
                    # 综合分析模块使用的下拉菜单
                    dcc.Dropdown(id="county_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="school_dropdown", style={"display": "none"}),
                    dcc.Dropdown(id="class_dropdown", style={"display": "none"}),
                    # 导出组件
                    dcc.Download(id="download-data"),
                ]
            ),
            # 存储组件
            dcc.Store(
                id="data_store",
                data=(
                    data_store.df.to_json(orient="split")
                    if data_store.df is not None
                    else None
                ),
            ),
            dcc.Store(id="current_data_store"),
            dcc.Store(id="analysis_results"),
            dcc.Store(id="custom_metrics_store"),
            dcc.Store(id="comp_data_updated", data=False),
            # 各模块缓存存储已移除
        ],
        fluid=True,
    ),
    # 版权信息区域
    copyright_footer
])


# 数据上传回调
@app.callback(
    [
        Output("data_store", "data"),
        Output("upload_status", "children"),
        Output("column_names_display", "children"),
    ],
    [Input("upload_data", "contents")],
    [State("upload_data", "filename")],
)
def handle_upload(contents, filename):
    if contents is None:
        return None, html.Div("请上传数据文件", className="text-muted"), None

    try:
        # 解析文件内容
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # 读取数据
        if "csv" in filename.lower():
            from io import StringIO

            # 尝试多种编码格式解码CSV
            encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig"]
            df = None
            last_error = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(StringIO(decoded.decode(encoding)))
                    break
                except (UnicodeDecodeError, UnicodeError) as e:
                    last_error = e
                    continue

            if df is None:
                raise ValueError(
                    f"无法解码CSV文件，尝试的编码: {', '.join(encodings)}。最后错误: {str(last_error)}"
                )
        else:
            from io import BytesIO

            df = pd.read_excel(BytesIO(decoded))

        # 初始化数据处理器并进行数据类型转换
        processor = DataProcessor()
        df = processor._convert_text_to_numbers(df)

        # 计算新高考总分（如果没有新高考总分列）
        if "新高考总分" not in df.columns:
            df = processor.calculate_total_score(df)
            logger.info("已自动计算学生新高考总分")
        else:
            logger.info("数据中已包含总分列")

        # 数据库存储功能已移除
        # 不需要本地变量 raw_data_id，直接清理 data_store 中的引用
        data_store.raw_data_id = None

        # 更新全局数据存储（用于其他模块）
        data_store.processor = processor
        data_store.df = df
        data_store.processor.data = df

        # 初始化综合分析器（不传递raw_data_id）
        data_store.comprehensive_analyzer = ComprehensiveAnalyzer(df)

        # 初始化其他分析器（不传递raw_data_id）
        try:
            data_store.quadrant_analyzer = QuadrantAnalyzer(df)
            data_store.cascade_analyzer = CascadeStatisticsAnalyzer(df)
            data_store.effective_group_analyzer = EffectiveGroupAnalyzer(df)
            data_store.critical_students_analyzer = CriticalStudentsAnalyzer(df)
            data_store.top_students_analyzer = TopStudentsAnalyzer(df)
            data_store.question_analysis_analyzer = QuestionAnalysisAnalyzer(df)
            logger.info("所有分析器初始化完成")
        except Exception as e:
            logger.error(f"初始化分析器失败: {e}")

        status = dbc.Alert(
            [
                html.H5("✅ 数据上传成功！", className="alert-heading"),
                html.P(f"文件名: {filename}"),
            ],
            color="success",
        )

        # 创建列名显示组件
        column_names = dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.Span(
                                    f"{col}",
                                    className="badge bg-primary me-1 mb-1",
                                    style={"fontSize": "0.8em"},
                                )
                                for col in df.columns.tolist()
                            ]
                        )
                    ],
                    style={"maxHeight": "200px", "overflowY": "auto"},
                )
            ],
            className="h-100",
        )

        return (
            df.to_json(date_format="iso", orient="split"),
            status,
            column_names,
        )

    except Exception as e:
        logger.error(f"数据上传失败: {str(e)}")
        status = dbc.Alert(
            [
                html.H4("❌ 数据上传失败", className="alert-heading"),
                html.P(f"错误信息: {str(e)}"),
            ],
            color="danger",
        )

        return None, status, None


# 小题数据上传回调
@app.callback(
    [
        Output("question_upload_status", "children"),
        Output("question_data_info", "children"),
        Output("analyze_question_btn", "disabled"),
    ],
    [Input("upload_question_data", "contents")],
    [State("upload_question_data", "filename")],
    prevent_initial_call=False,
)
def handle_question_upload(contents, filename):
    if contents is None:
        return html.Div("请上传小题数据文件", className="text-muted small"), "", True

    try:
        # 解析文件内容
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # 读取数据
        if "csv" in filename.lower():
            from io import StringIO

            # 尝试多种编码格式解码CSV
            encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig"]
            df = None
            last_error = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(StringIO(decoded.decode(encoding)))
                    break
                except (UnicodeDecodeError, UnicodeError) as e:
                    last_error = e
                    continue

            if df is None:
                raise ValueError(
                    f"无法解码CSV文件，尝试的编码: {', '.join(encodings)}。最后错误: {str(last_error)}"
                )
        else:
            from io import BytesIO
            df = pd.read_excel(BytesIO(decoded))

        # 存储小题数据
        data_store.set_question_data(df)
        
        # 尝试检测小题字段
        analyzer = QuestionAnalysisAnalyzer(df)
        question_fields = analyzer._question_fields if hasattr(analyzer, '_question_fields') else []
        
        status = dbc.Alert(
            [
                html.H6("✅ 小题数据上传成功！", className="alert-heading"),
                html.P(f"文件名: {filename}"),
                html.P(f"数据行数: {len(df)}"),
                html.P(f"检测到小题字段: {len(question_fields)}个")
            ],
            color="success",
            className="small"
        )
        
        # 显示数据信息
        data_info = dbc.Card([
            dbc.CardBody([
                html.H6("📊 数据信息", className="card-title"),
                html.P(f"文件名: {filename}", className="small mb-1"),
                html.P(f"数据行数: {len(df)}", className="small mb-1"),
                html.P(f"数据列数: {len(df.columns)}", className="small mb-2"),
                html.P("检测到的小题字段:", className="small fw-bold mb-1"),
                html.Div([
                    html.Span(
                        f"{field}",
                        className="badge bg-info me-1 mb-1",
                        style={"fontSize": "0.7em"}
                    ) for field in question_fields[:10]  # 只显示前10个
                ]),
                html.P(f"...共{len(question_fields)}个小题字段", className="small text-muted mt-1") if len(question_fields) > 10 else ""
            ])
        ], className="small")
        
        return status, data_info, False

    except Exception as e:
        logger.error(f"小题数据上传失败: {str(e)}")
        status = dbc.Alert(
            [
                html.H6("❌ 小题数据上传失败", className="alert-heading"),
                html.P(f"错误信息: {str(e)}", className="small")
            ],
            color="danger",
            className="small"
        )

        return status, "", True


# 标签页内容回调
@app.callback(
    Output("tab_content", "children"),
    [Input("tabs", "active_tab"), Input("data_store", "data")],
)
def render_tab_content(active_tab, data_json):
    if data_json is None:
        return html.Div("请先上传数据文件", className="text-center text-muted my-5")

    df = pd.read_json(StringIO(data_json), orient="split")

    if active_tab == "overview":
        return render_overview_tab(df)
    elif active_tab == "comprehensive":
        return render_comprehensive_tab(df)
    elif active_tab == "quadrant":
        return render_quadrant_tab(df)
    elif active_tab == "cascade":
        return render_cascade_tab(df)
    elif active_tab == "effective_group":
        return render_effective_group_tab(df)
    elif active_tab == "goal_completion":
        return render_goal_completion_tab(df)
    elif active_tab == "critical_students":
        return create_critical_students_tab()
    elif active_tab == "top_students":
        return create_top_students_tab()
    elif active_tab == "question_analysis":
        return create_question_analysis_tab()



# 数据概览标签页
def render_overview_tab(df):
    # 数据摘要
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader("📊 数据概览"),
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        f"{df.shape[0]}",
                                                        className="text-primary",
                                                    ),
                                                    html.P(
                                                        "数据行数",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        f"{df.shape[1]}",
                                                        className="text-info",
                                                    ),
                                                    html.P(
                                                        "数据列数",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        f"{len(numeric_cols)}",
                                                        className="text-success",
                                                    ),
                                                    html.P(
                                                        "数值列",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        f"{len(categorical_cols)}",
                                                        className="text-warning",
                                                    ),
                                                    html.P(
                                                        "分类列",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        f"{df.isnull().sum().sum()}",
                                                        className="text-danger",
                                                    ),
                                                    html.P(
                                                        "缺失值",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        f"{df.memory_usage(deep=True).sum() / 1024:.1f}KB",
                                                        className="text-secondary",
                                                    ),
                                                    html.P(
                                                        "内存使用",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                        ]
                                    ),
                                    html.Hr(),
                                    # 数据预览表格
                                    html.H6("数据预览 (前10行)"),
                                    dash_table.DataTable(
                                        data=df.head(10).to_dict("records"),
                                        columns=[
                                            {"name": i, "id": i} for i in df.columns
                                        ],
                                        style_table={"overflowX": "auto"},
                                        style_cell={
                                            "textAlign": "left",
                                            "padding": "10px",
                                        },
                                        style_header={
                                            "backgroundColor": "rgb(230, 230, 230)",
                                            "fontWeight": "bold",
                                        },
                                        style_data_conditional=[
                                            {
                                                "if": {"row_index": "odd"},
                                                "backgroundColor": "rgb(248, 248, 248)",
                                            }
                                        ],
                                        page_size=10,
                                    ),
                                ]
                            ),
                        ]
                    )
                ]
            )
        ]
    )


# 综合数据分析标签页
def render_comprehensive_tab(df):
    """渲染综合数据分析标签页"""
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            # 控制面板
                            create_comprehensive_control_panel(),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            # 结果面板
                            create_comprehensive_results_panel()
                        ],
                        width=9,
                    ),
                ]
            )
        ]
    )


# 四象限分析标签页
def render_quadrant_tab(df):
    # 更新下拉选项
    # numeric_cols intentionally not used here; filter_columns_for_analysis is kept
    # to ensure the helper runs side-effects if any. (Removed unused assignment.)

    return dbc.Row(
        [
            dbc.Col(
                [
                    # 控制面板
                    create_quadrant_control_panel(),
                ],
                width=3,
            ),
            dbc.Col(
                [
                    # 结果面板
                    create_quadrant_results_panel()
                ],
                width=9,
            ),
        ]
    )


# 三级联动统计标签页
def render_cascade_tab(df):
    """渲染三级联动统计标签页"""
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            # 控制面板
                            create_cascade_control_panel(),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            # 结果面板
                            create_cascade_results_panel()
                        ],
                        width=9,
                    ),
                ]
            )
        ]
    )


# 有效群体统计分析标签页
def render_effective_group_tab(df):
    """渲染有效群体统计分析标签页"""
    return html.Div(
        [
            # 自定义分数线状态存储
            dcc.Store(id="effective_group_custom_thresholds_store", data=[]),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            # 控制面板
                            create_effective_group_control_panel(),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            # 结果面板
                            create_effective_group_results_panel()
                        ],
                        width=9,
                    ),
                ]
            ),
        ]
    )


# 目标完成统计标签页
def render_goal_completion_tab(df):
    """渲染目标完成统计分析标签页"""
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            # 控制面板
                            create_goal_completion_control_panel(),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            # 结果面板
                            create_goal_completion_results_panel()
                        ],
                        width=8,
                    ),
                ]
            ),

        ]
    )





# 报告生成标签页


# 数据同步回调 - 同步data-store到current-data-store
@app.callback(
    [
        Output("current-data-store", "data"),
        Output("comp-data-updated", "data"),
    ],
    [Input("data_store", "data")],
)
def sync_data_stores(data_json):
    """同步主数据存储到当前数据存储"""
    return data_json, True


# 同步四象限图表输出


# 同步综合分析图表输出
@app.callback(
    Output("comparison_chart_visible", "children"),
    [
        Input("comparison_chart", "children"),
    ],
)
def sync_comprehensive_charts(comparison_children):
    # Guard: if a figure dict (plain object) was accidentally stored in the hidden
    # container, wrap it in a proper Graph component before sending to a visible
    # children prop. This prevents React from trying to treat a plain object as a
    # component type (which causes React error #31).
    try:
        from dash import dcc
        # If the hidden container stored either a plain dict (plotly JSON) or a
        # plotly.graph_objects.Figure, wrap it in a Graph component so React
        # receives a proper component tree instead of a raw object.
        try:
            import plotly.graph_objects as go

            is_figure = isinstance(comparison_children, go.Figure)
        except Exception:
            is_figure = False

        if isinstance(comparison_children, dict) or is_figure:
            return dcc.Graph(figure=comparison_children)
    except Exception:
        # If dash isn't available for some reason, fall back to original value
        pass

    return comparison_children


# 同步综合分析其他输出
@app.callback(
    [
        Output("enhanced_selection_info_visible", "children"),
        Output("aggregation_table_visible", "children"),
        Output("performance_results_visible", "children"),
        Output("admission_rate_chart_visible", "children"),
        Output("admission_rate_stats_visible", "children"),
        Output("subject_indicators_table_visible", "children"),
        Output("class_radar_chart_visible", "children"),
    ],
    [
        Input("enhanced_selection_info", "children"),
        Input("aggregation_table", "children"),
        Input("performance_results", "children"),
        Input("admission_rate_chart", "children"),
        Input("admission_rate_stats", "children"),
        Input("subject_indicators_table", "children"),
        Input("class_radar_chart", "children"),
    ],
)
def sync_comprehensive_other_outputs(
    selection_info,
    aggregation_table,
    performance_results,
    admission_chart,
    admission_stats,
    subject_table,
    radar_chart,
):
    # Ensure we don't forward plain dicts (e.g. plotly figure dicts) into
    # components' children properties. If a plain dict is detected, wrap it in
    # a Graph so Dash/React render a component instead of an object.
    try:
        from dash import dcc

        def _wrap_if_figure(val):
            # Wrap plain dicts and plotly Figure objects in a Graph component
            # to prevent Dash from serializing them as raw JS objects which
            # React would attempt to render as children (causing error #31).
            if val is None:
                return None
            try:
                import plotly.graph_objects as go

                if isinstance(val, go.Figure):
                    return dcc.Graph(figure=val)
            except Exception:
                pass

            if isinstance(val, dict):
                return dcc.Graph(figure=val)

            return val

        return (
            _wrap_if_figure(selection_info),
            _wrap_if_figure(aggregation_table),
            _wrap_if_figure(performance_results),
            _wrap_if_figure(admission_chart),
            _wrap_if_figure(admission_stats),
            _wrap_if_figure(subject_table),
            _wrap_if_figure(radar_chart),
        )
    except Exception:
        # Fall back to direct forwarding if wrapping fails for any reason
        return (
            selection_info,
            aggregation_table,
            performance_results,
            admission_chart,
            admission_stats,
            subject_table,
            radar_chart,
        )


# 简化的下拉菜单更新回调函数
@app.callback(
    Output("cascade_filters_div", "style"),
    [
        Input("data_store", "data"),
        Input("quadrant_analysis_level_radio", "value"),
    ],
)
def update_filter_visibility(data_json, analysis_level):
    """控制三级联动过滤器的显示/隐藏"""
    if data_json is None:
        return {"display": "none"}

    # 显示/隐藏三级联动过滤器
    return {"display": "block"} if analysis_level != "all" else {"display": "none"}


# 移除了重复的三级联动菜单回调函数，各个模块将使用自己的回调函数管理下拉菜单


# 四象限分析回调函数
@app.callback(
    [
        Output("quadrant-subject-dropdown", "options"),
        Output("quadrant-total-dropdown", "options"),
    ],
    [Input("data_store", "data")],
)
def update_quadrant_dropdowns(data_json):
    if data_json is None:
        return [], []

    try:
        df = pd.read_json(StringIO(data_json), orient="split")
        numeric_cols = filter_columns_for_analysis(df.columns)

        # 为单科选择排除包含"总分"、"等级"、"排"等字眼的选项
        exclude_keywords = ["总分", "等级", "排", "位次", "排名", "综合", "整体"]
        subject_cols = [col for col in numeric_cols 
                       if not any(exclude in col for exclude in exclude_keywords)]
        
        # 为总分选择，允许包含"总分"的选项
        total_cols = [col for col in numeric_cols 
                     if any(keyword in col for keyword in ["总分", "总", "合计"]) or 
                        not any(exclude in col for exclude in exclude_keywords)]

        subject_options = [{"label": col, "value": col} for col in subject_cols]
        total_options = [{"label": col, "value": col} for col in total_cols]
        
        # 添加调试信息
        print(f"[DEBUG] 四象限分析列过滤:")
        print(f"  原始数值列: {numeric_cols}")
        print(f"  排除关键词: {exclude_keywords}")
        print(f"  单科可选列: {subject_cols}")
        print(f"  总分可选列: {total_cols}")
        
        return subject_options, total_options

    except Exception:
        return [], []


# 四象限分析的默认值设置逻辑已在下方统一实现，保留单一定义以避免重复


# 综合分析模块数据更新回调
@app.callback(
    [
        Output("county_dropdown", "options"),
        Output("school_dropdown", "options"),
        Output("class_dropdown", "options"),
    ],
    [Input("data_store", "data")],
    prevent_initial_call=False,
)
def update_comprehensive_on_data_upload(data_json):
    """数据上传时更新综合分析下拉菜单"""
    if data_json is None:
        return [], [], []

    try:
        from io import StringIO

        df = pd.read_json(StringIO(data_json), orient="split")
        from comprehensive_analyzer import ComprehensiveAnalyzer

        analyzer = ComprehensiveAnalyzer(df)
        options = analyzer.get_cascade_options()

        print(
            f"综合分析下拉菜单更新 - 区县:{len(options['county'])}个, 学校:{len(options['school'])}个, 班级:{len(options['class'])}个"
        )

        return options["county"], options["school"], options["class"]
    except Exception as e:
        print(f"综合分析下拉菜单更新失败: {e}")
        return [], [], []


# 综合分析模块的二级联动回调
@app.callback(
    [
        Output("school_dropdown", "options", allow_duplicate=True),
        Output("school_dropdown", "value", allow_duplicate=True),
    ],
    [Input("county_dropdown", "value")],
    [State("data_store", "data")],
    prevent_initial_call=True,
)
def update_comprehensive_schools(selected_counties, data_json):
    if data_json is None or not selected_counties:
        return [], None

    try:
        from io import StringIO

        df = pd.read_json(StringIO(data_json), orient="split")
        from comprehensive_analyzer import ComprehensiveAnalyzer

        analyzer = ComprehensiveAnalyzer(df)
        options = analyzer.get_cascade_options(selected_counties=selected_counties)
        return options["school"], None
    except Exception as e:
        print(f"更新综合分析学校选项失败: {e}")
        return [], None


@app.callback(
    [
        Output("class_dropdown", "options", allow_duplicate=True),
        Output("class_dropdown", "value", allow_duplicate=True),
    ],
    [
        Input("county_dropdown", "value"),
        Input("school_dropdown", "value"),
    ],
    [State("data_store", "data")],
    prevent_initial_call=True,
)
def update_comprehensive_classes(selected_counties, selected_schools, data_json):
    if data_json is None:
        return [], None

    try:
        from io import StringIO

        df = pd.read_json(StringIO(data_json), orient="split")
        from comprehensive_analyzer import ComprehensiveAnalyzer

        analyzer = ComprehensiveAnalyzer(df)
        options = analyzer.get_cascade_options(
            selected_counties=selected_counties or [],
            selected_schools=selected_schools or [],
        )
        return options["class"], None
    except Exception as e:
        print(f"更新综合分析班级选项失败: {e}")
        return [], None


# 移除了重复的下拉菜单回调，各个模块将使用自己的回调函数


def set_quadrant_dropdown_defaults(
    subject_options, total_options, current_subject, current_total
):
    """设置四象限分析的默认值"""
    try:
        # 如果已经有值，保持不变
        if current_subject and current_total:
            return current_subject, current_total

        # 设置默认总分列
        default_total = current_total
        if not default_total and total_options:
            # 优先选择"新高考总分"，否则选择第一个选项
            new_total_option = next(
                (opt["value"] for opt in total_options if "新高考总分" in opt["value"]),
                None,
            )
            default_total = (
                new_total_option if new_total_option else total_options[0]["value"]
            )

        # 设置默认单科列
        default_subject = current_subject
        if not default_subject and subject_options:
            # 优先选择主要科目，否则选择第一个选项
            priority_subjects = ["语文", "数学", "英语"]
            default_subject = None
            for subject in priority_subjects:
                subject_option = next(
                    (
                        opt["value"]
                        for opt in subject_options
                        if subject in opt["value"]
                    ),
                    None,
                )
                if subject_option:
                    default_subject = subject_option
                    break

            if not default_subject:
                default_subject = subject_options[0]["value"]

        return default_subject, default_total

    except Exception as e:
        logger.error(f"设置四象限分析默认值失败: {e}")
        return current_subject or None, current_total or None


# 显示/隐藏高级设置面板的回调
@app.callback(
    Output("advanced-thresholds-div", "style"),
    [Input("quadrant_analysis_type", "value")],
)
def toggle_advanced_settings(analysis_type):
    # 始终显示高级设置，因为只支持高级分析
    return {"display": "block"}


# 自定义指标管理回调函数
@app.callback(
    Output("metrics_list", "children"),
    Output("custom_metrics_store", "data"),
    [
        Input("add_metric_btn", "n_clicks"),
        Input("reset_metrics_btn", "n_clicks"),
        Input("add_undergraduate_btn", "n_clicks"),
        Input("add_special_btn", "n_clicks"),
        Input("add_key_btn", "n_clicks"),
        Input("add_basic_btn", "n_clicks"),
    ],
    [
        State("custom_metrics_store", "data"),
        State("new_metric_name", "value"),
        State("new_metric_subject", "value"),
        State("new_metric_total", "value"),
    ],
)
def manage_custom_metrics(
    add_clicks,
    reset_clicks,
    undergrad_clicks,
    special_clicks,
    key_clicks,
    basic_clicks,
    current_metrics,
    name,
    subject_thresh,
    total_thresh,
):
    # 初始化指标列表
    metrics = current_metrics if current_metrics else []

    # 处理不同的按钮点击
    ctx = dash.callback_context
    if not ctx.triggered:
        return (
            html.Div(
                "暂无自定义指标，请添加或选择预设指标",
                className="alert alert-light",
            ),
            [],
        )

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "add_metric_btn" and name and subject_thresh and total_thresh:
        # 添加自定义指标
        new_metric = {
            "name": name,
            "subject_threshold": float(subject_thresh),
            "total_threshold": float(total_thresh),
        }
        metrics.append(new_metric)

    elif button_id == "reset_metrics_btn":
        # 重置指标列表
        metrics = []

    elif button_id == "add_undergraduate_btn":
        # 添加本科线预设
        metrics.append(
            {"name": "本科线", "subject_threshold": 75, "total_threshold": 375}
        )

    elif button_id == "add_special_btn":
        # 添加特控线预设
        metrics.append(
            {"name": "特控线", "subject_threshold": 85, "total_threshold": 475}
        )

    elif button_id == "add_key_btn":
        # 添加重点线预设
        metrics.append(
            {"name": "重点线", "subject_threshold": 80, "total_threshold": 425}
        )

    elif button_id == "add_basic_btn":
        # 添加保底线预设
        metrics.append(
            {"name": "保底线", "subject_threshold": 60, "total_threshold": 300}
        )

    # 生成指标列表显示
    if metrics:
        metric_cards = []
        for i, metric in enumerate(metrics):
            metric_card = dbc.Card(
                [
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(
                                                metric["name"],
                                                className="card-title mb-1",
                                            ),
                                            html.P(
                                                f"单科线: {metric['subject_threshold']}, 总分线: {metric['total_threshold']}",
                                                className="card-text small text-muted",
                                            ),
                                        ],
                                        width=8,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "删除",
                                                id=f"delete-metric-{i}",
                                                color="danger",
                                                size="sm",
                                            )
                                        ],
                                        width=4,
                                        className="d-flex align-items-center",
                                    ),
                                ]
                            )
                        ]
                    )
                ],
                className="mb-2",
            )
            metric_cards.append(metric_card)

        metrics_display = html.Div(metric_cards)
    else:
        metrics_display = dbc.Alert(
            "暂无自定义指标，请添加或选择预设指标", color="light"
        )

    return metrics_display, metrics


# 删除单个指标的回调（动态创建）
def create_delete_callback(index):
    @app.callback(
        Output("metrics_list", "children", allow_duplicate=True),
        Output("custom_metrics_store", "data", allow_duplicate=True),
        [Input(f"delete-metric-{index}", "n_clicks")],
        [State("custom_metrics_store", "data")],
        prevent_initial_call=True,
    )
    def delete_metric(n_clicks, current_metrics):
        if n_clicks and current_metrics:
            updated_metrics = current_metrics.copy()
            if 0 <= index < len(updated_metrics):
                updated_metrics.pop(index)

            # 重新生成显示
            if updated_metrics:
                metric_cards = []
                for i, metric in enumerate(updated_metrics):
                    metric_card = dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.H6(
                                                        metric["name"],
                                                        className="card-title mb-1",
                                                    ),
                                                    html.P(
                                                        f"单科线: {metric['subject_threshold']}, 总分线: {metric['total_threshold']}",
                                                        className="card-text small text-muted",
                                                    ),
                                                ],
                                                width=8,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "删除",
                                                        id=f"delete-metric-{i}",
                                                        color="danger",
                                                        size="sm",
                                                    )
                                                ],
                                                width=4,
                                                className="d-flex align-items-center",
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        className="mb-2",
                    )
                    metric_cards.append(metric_card)

                metrics_display = html.Div(metric_cards)
            else:
                metrics_display = dbc.Alert(
                    "暂无自定义指标，请添加或选择预设指标", color="light"
                )

            return metrics_display, updated_metrics
        return dash.no_update, dash.no_update

    return delete_metric


# 创建删除回调
for i in range(20):  # 预创建20个删除回调
    create_delete_callback(i)











# 静态文件路由
@app.server.route("/static/<path:filename>")
def serve_static(filename):
    from flask import send_from_directory
    import os
    
    static_dir = os.path.join(os.getcwd(), "static")
    return send_from_directory(static_dir, filename)

# 文件下载路由
@app.server.route("/download/<path:path>")
def download_file(path):
    from flask import send_file

    return send_file(path, as_attachment=True)


# 四象限分析执行回调
@app.callback(
    [
        Output("quadrant_chart_visible", "children"),
        Output("quadrant_summary_visible", "children"),
        Output("quadrant_details_visible", "children"),
    ],
    [Input("run_quadrant_btn", "n_clicks")],
    [
        State("quadrant_analysis_type", "value"),
        State("quadrant-subject-dropdown", "value"),
        State("quadrant-total-dropdown", "value"),
        State("custom_metrics_store", "data"),
        State("quadrant_options", "value"),
        State("quadrant_analysis_level_radio", "value"),
        State("quadrant_county_dropdown", "value"),
        State("quadrant_school_dropdown", "value"),
        State("quadrant_class_dropdown", "value"),
        State("data_store", "data"),
    ],
    prevent_initial_call=True,
)
def update_quadrant_analysis(
    n_clicks, analysis_type, subject_col, total_col, custom_metrics, options,
    analysis_level, selected_counties, selected_schools, selected_classes, data_json
):
    """执行四象限分析"""
    print(f"[DEBUG] 四象限分析回调触发")
    print(f"[DEBUG] 点击次数: {n_clicks}")
    print(f"[DEBUG] 单科列: {subject_col}")
    print(f"[DEBUG] 总分列: {total_col}")
    print(f"[DEBUG] 自定义指标: {custom_metrics}")
    print(f"[DEBUG] 选项: {options}")
    print(f"[DEBUG] 数据是否存在: {data_json is not None}")
    
    if n_clicks is None or not subject_col or not total_col or data_json is None:
        print("[DEBUG] 验证失败，返回空结果")
        return None, None, None

    try:
        from io import StringIO

        df = pd.read_json(StringIO(data_json), orient="split")
        original_count = len(df)
        print(f"[DEBUG] 四象限分析原始数据行数: {len(df)}")
        print(f"[DEBUG] 分析层级: {analysis_level}")
        print(f"[DEBUG] 选择的区县: {selected_counties}")
        print(f"[DEBUG] 选择的学校: {selected_schools}")
        print(f"[DEBUG] 选择的班级: {selected_classes}")
        print(f"[DEBUG] 选择列: 单科={subject_col}, 总分={total_col}")

        # 应用行政层级筛选（与综合分析器保持一致）
        if analysis_level != "all":
            admin_cols = {}
            for col in df.columns:
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
                    admin_cols["county"] = col
                # 扩展学校列的匹配规则
                elif any(
                    keyword in col_str for keyword in ["学校", "中学", "小学", "school"]
                ):
                    admin_cols["school"] = col
                # 扩展班级列的匹配规则
                elif any(
                    keyword in col_str for keyword in ["行政班", "班级", "班", "class"]
                ):
                    admin_cols["class"] = col

            # 根据分析层级进行筛选（支持层级组合）
            if analysis_level == "county" and selected_counties and "county" in admin_cols:
                county_col = admin_cols["county"]
                print(f"区县筛选: {selected_counties}, 列名: {county_col}")
                df = df[df[county_col].isin(selected_counties)]
                
            elif analysis_level == "school" and selected_schools and "school" in admin_cols:
                school_col = admin_cols["school"]
                print(f"学校筛选: {selected_schools}, 列名: {school_col}")
                df = df[df[school_col].isin(selected_schools)]
                
            elif analysis_level == "class" and selected_classes and "class" in admin_cols:
                class_col = admin_cols["class"]
                print(f"班级筛选: {selected_classes}, 列名: {class_col}")
                df = df[df[class_col].isin(selected_classes)]

        filtered_count = len(df)
        print(f"[DEBUG] 筛选后数据量: {filtered_count}, 筛选掉了 {original_count - filtered_count} 条数据")

        # 添加数据质量调试信息
        print(f"[DEBUG] 四象限分析最终数据行数: {len(df)}")
        print(f"[DEBUG] 选择列: 单科={subject_col}, 总分={total_col}")
        if len(df) > 0:
            print(
                f"[DEBUG] 单科数据范围: {df[subject_col].min():.2f} - {df[subject_col].max():.2f}"
            )
            print(
                f"[DEBUG] 总分数据范围: {df[total_col].min():.2f} - {df[total_col].max():.2f}"
            )

            # 检查数据质量
            subject_nan = df[subject_col].isna().sum()
            total_nan = df[total_col].isna().sum()
            print(f"[DEBUG] 单科列NaN数量: {subject_nan}")
            print(f"[DEBUG] 总分列NaN数量: {total_nan}")

            # 检查数据类型
            print(f"[DEBUG] 单科列类型: {df[subject_col].dtype}")
            print(f"[DEBUG] 总分列类型: {df[total_col].dtype}")

        # 检查筛选后的数据是否为空
        if df.empty:
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 筛选结果为空", className="alert-heading"),
                    html.P("根据所选的行政层级条件，没有找到符合条件的数据"),
                ],
                color="warning",
            )
            return error_alert, None, None

        # 检查数据列是否存在
        if subject_col not in df.columns or total_col not in df.columns:
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 列不存在", className="alert-heading"),
                    html.P("请确保选择的数据列在数据中存在"),
                ],
                color="danger",
            )
            return error_alert, None, None

        # 创建分析器
        from quadrant_analyzer import QuadrantAnalyzer

        analyzer = QuadrantAnalyzer(df)

        # 处理自定义指标
        if not custom_metrics:
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 自定义指标未设置", className="alert-heading"),
                    html.P("请至少添加一个自定义指标进行分析"),
                ],
                color="danger",
            )
            return error_alert, None, None

        # 处理 custom_metrics 的各种可能格式
        if isinstance(custom_metrics, str):
            try:
                custom_metrics = json.loads(custom_metrics)
            except json.JSONDecodeError:
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 自定义指标格式错误", className="alert-heading"),
                        html.P("自定义指标字符串无法解析为有效格式"),
                    ],
                    color="danger",
                )
                return error_alert, None, None

        # 确保 custom_metrics 是列表格式
        if not isinstance(custom_metrics, list):
            custom_metrics = []

        # 验证指标列表
        valid_metrics = []
        for metric in custom_metrics:
            if isinstance(metric, dict) and "name" in metric:
                if "subject_threshold" not in metric:
                    metric["subject_threshold"] = 0
                if "total_threshold" not in metric:
                    metric["total_threshold"] = 0
                valid_metrics.append(metric)

        custom_metrics = valid_metrics

        if not custom_metrics:
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 自定义指标格式错误", className="alert-heading"),
                    html.P("自定义指标格式不正确，请重新设置"),
                ],
                color="danger",
            )
            return error_alert, None, None

        # 设置分析参数
        analyzer.subject_column = subject_col
        analyzer.total_column = total_col

        print(f"[DEBUG] 设置自定义指标: {custom_metrics}")

        # 设置自定义指标
        try:
            analyzer.set_custom_metrics(custom_metrics)
        except Exception as e:
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 设置自定义指标失败", className="alert-heading"),
                    html.P(f"错误信息: {str(e)}"),
                ],
                color="danger",
            )
            return error_alert, None, None

        # 执行分析
        try:
            print("[DEBUG] 开始执行四象限分析...")
            analyzer.analyze_quadrants()
            print("[DEBUG] 四象限分析完成")

            if not hasattr(analyzer, "quadrant_stats") or not analyzer.quadrant_stats:
                print("[DEBUG] 分析结果为空")
                error_alert = dbc.Alert(
                    [
                        html.H5("❌ 分析结果为空", className="alert-heading"),
                        html.P("四象限分析未产生有效结果，请检查数据设置"),
                    ],
                    color="warning",
                )
                return error_alert, None, None

        except Exception as e:
            error_alert = dbc.Alert(
                [
                    html.H5("❌ 四象限分析执行失败", className="alert-heading"),
                    html.P(f"错误信息: {str(e)}"),
                ],
                color="danger",
            )
            return error_alert, None, None

        # 创建图表
        show_names = "show_names" in (options or [])
        print("[DEBUG] 开始创建图表...")
        fig = analyzer.create_quadrant_plot(show_names=show_names)
        print(f"[DEBUG] 图表创建完成: {type(fig)}")
        if hasattr(fig, "data") and fig.data:
            print(f"[DEBUG] 图表轨迹数量: {len(fig.data)}")

        chart = dcc.Graph(
            figure=fig,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["pan2d", "lasso2d", "select2d"],
            },
            style={"width": "100%", "height": "700px"},
        )

        # 创建分析范围信息
        analysis_scope_info = []
        if analysis_level != "all":
            scope_text = "分析范围: "
            if analysis_level == "county" and selected_counties:
                scope_text += f"区县 - {', '.join(selected_counties)}"
            elif analysis_level == "school" and selected_schools:
                scope_text += f"学校 - {', '.join(selected_schools)}"
            elif analysis_level == "class" and selected_classes:
                scope_text += f"行政班 - {', '.join(selected_classes)}"

            analysis_scope_info.append(
                dbc.Alert(
                    [
                        html.H6("📍 " + scope_text, className="alert-heading"),
                        html.P(f"本次分析基于 {len(df)} 名学生数据（原始数据: {original_count} 条）"),
                    ],
                    color="info",
                    className="mb-3",
                )
            )

        # 创建统计摘要
        summary = None
        if "show_table" in (options or []):
            summary_df = analyzer.get_quadrant_summary_table()
            if summary_df is not None and not summary_df.empty:
                summary_elements = analysis_scope_info + [
                    html.H6("📊 四象限统计摘要", className="text-primary mb-3"),
                    dbc.Table.from_dataframe(
                        summary_df,
                        striped=True,
                        bordered=True,
                        hover=True,
                        size="sm",
                        className="mt-3",
                    ),
                ]
                summary = html.Div(summary_elements)
            elif analysis_scope_info:
                summary = html.Div(analysis_scope_info)

        # 创建详细数据
        details = None
        if "show_details" in (options or []):
            from dash import dash_table

            quadrant_tabs = []

            for region_key, stats in analyzer.quadrant_stats.items():
                if stats["count"] > 0:
                    students_df = stats["students"]
                    stats_info = html.Div(
                        [
                            html.P(
                                f"学生人数: {stats['count']} 人 ({stats['percentage']:.1f}%)",
                                className="text-info",
                            ),
                            html.P(
                                f"{subject_col}平均分: {stats['subject_mean']:.1f} ± {stats['subject_std']:.1f}",
                                className="text-success",
                            ),
                            html.P(
                                f"{total_col}平均分: {stats['total_mean']:.1f} ± {stats['total_std']:.1f}",
                                className="text-primary",
                            ),
                        ],
                        className="mb-3",
                    )

                    display_columns = []
                    important_columns = ["姓名", subject_col, total_col]

                    for col in important_columns:
                        if col in students_df.columns:
                            display_columns.append({"name": col, "id": col})

                    for col in students_df.columns:
                        if col not in important_columns:
                            display_columns.append({"name": col, "id": col})

                    table = dash_table.DataTable(
                        data=students_df.to_dict("records"),
                        columns=display_columns,
                        style_table={
                            "overflowX": "auto",
                            "height": "400px",
                            "minHeight": "300px",
                        },
                        style_cell={
                            "textAlign": "left",
                            "padding": "8px",
                            "fontSize": "12px",
                            "minWidth": "100px",
                        },
                        style_header={
                            "backgroundColor": "rgb(230, 230, 230)",
                            "fontWeight": "bold",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)",
                            }
                        ],
                        page_size=15,
                        fixed_rows={"headers": True},
                        virtualization=False,
                    )

                    tab_content = html.Div([stats_info, table])

                    quadrant_tabs.append(
                        dbc.Tab(
                            label=stats["label"],
                            tab_id=f"region_{region_key}",
                            children=tab_content,
                        )
                    )

            if quadrant_tabs:
                details = dbc.Card(
                    [
                        dbc.CardHeader("📝 各区域学生详细列表"),
                        dbc.CardBody([dbc.Tabs(quadrant_tabs)]),
                    ],
                    className="mt-3",
                )

        return chart, summary, details

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        error_alert = dbc.Alert(
            [
                html.H5("❌ 四象限分析失败", className="alert-heading"),
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
        return error_alert, None, None


# 注册新增分析模块的回调函数
from new_analysis_callbacks import register_new_analysis_callbacks
register_new_analysis_callbacks(app, data_store)


if __name__ == "__main__":
    import webbrowser
    import threading
    import time
    
    # 创建必要的目录
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    # 注册四象限分析回调
    register_quadrant_callbacks(app)

    # 注册综合分析回调
    register_comprehensive_callbacks(app)

    # 注册三级联动统计回调
    register_cascade_callbacks(app)

    # 注册有效群体分析回调
    register_effective_group_callbacks(app, data_store)

    # 注册目标完成统计回调
    register_goal_completion_callbacks(app, data_store)

    # 数据库加载功能已移除，使用内存数据存储

    # 启动应用
    print("=" * 60)
    print("成绩分析系统启动中...")
    print("=" * 60)
    
    # 使用固定8080端口（避免权限问题）
    port = 8080
    url = f"http://localhost:{port}"
    
    print("系统正在初始化...")
    print("即将在浏览器中打开")
    print("按 Ctrl+C 停止系统")
    print("=" * 60)
    
    # 延迟打开浏览器
    def open_browser():
        time.sleep(4)  # 等待4秒让服务器完全启动
        try:
            webbrowser.open(url)
            print("\n✓ 成绩分析系统已在浏览器中打开")
            print("  如果浏览器未自动打开，请稍等片刻或重新运行")
        except Exception as e:
            print(f"\n⚠ 无法自动打开浏览器: {e}")
            print(f"  请重新运行程序")
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # 使用 debug=False 避免自动重启，同时保持足够的错误信息
        # 如需调试，可手动改为 debug=True
        app.run(host="0.0.0.0", port=port, debug=False)
    except KeyboardInterrupt:
        print("\n系统已停止")
    except Exception as e:
        print(f"\n启动错误: {e}")
        print("\n可能的原因:")
        print("1. 防火墙阻止了程序运行")
        print("2. 系统权限不足")
        print("3. 网络配置问题")
        input("\n按回车键退出...")