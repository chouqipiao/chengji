#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新增分析模块的回调函数
包含临界生、尖子生、小题分析的回调逻辑
"""

import dash
from dash import Input, Output, State, callback_context,html
import dash_bootstrap_components as dbc
import pandas as pd
from io import StringIO
import logging

from critical_students_analyzer import CriticalStudentsAnalyzer
from critical_students_ui import create_critical_students_control_panel, create_critical_students_results_panel
from top_students_analyzer import TopStudentsAnalyzer, create_top_students_control_panel, create_top_students_results_panel
from question_analysis_analyzer import QuestionAnalysisAnalyzer, create_question_analysis_control_panel, create_question_analysis_results_panel
from new_analysis_ui import create_results_table

logger = logging.getLogger(__name__)

# 全局数据存储引用
_global_data_store = None

def set_global_data_store(data_store):
    """设置全局数据存储引用"""
    global _global_data_store
    _global_data_store = data_store


def _create_compact_student_table(students, group_type):
    """
    创建包含完整学科成绩的学生信息表格
    
    Args:
        students: 学生列表
        group_type: 群体类型
        
    Returns:
        html.Table: 包含完整学科成绩的表格
    """
    if not students:
        return html.P("暂无学生数据", className="text-muted small text-center")
    
    # 获取第一个学生来确定所有学科列
    if students:
        first_student = students[0]
        
        # 定义要排除的非学科列
        exclude_keywords = ["姓名", "学校", "行政班", "区县", "考生号", "选科组合", "准考证号", "考生类型", "等级"]
        
        # 获取所有学科列（数值列且不在排除列表中）
        subject_columns = []
        for key, value in first_student.items():
            if key not in exclude_keywords:
                # 进一步检查是否为学科分数（通常为数值型）
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit()):
                    subject_columns.append(key)
        
        # 按照优先级排序学科
        priority_order = ["新高考总分", "总分", "语文", "数学", "外语", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]
        ordered_subjects = []
        other_subjects = []
        
        for subject in subject_columns:
            matched = False
            for priority in priority_order:
                if priority in subject:
                    if priority not in [s.split('(')[0] for s in ordered_subjects]:
                        ordered_subjects.append(subject)
                    matched = True
                    break
            if not matched:
                other_subjects.append(subject)
        
        # 合并有序学科和其他学科
        final_subjects = ordered_subjects + sorted(other_subjects)
    else:
        final_subjects = []
    
    # 构建表头
    headers = [html.Th("姓名", className="small text-center", style={"minWidth": "80px"}),
              html.Th("学校", className="small text-center", style={"minWidth": "100px"}),
              html.Th("班级", className="small text-center", style={"minWidth": "80px"})]
    
    # 添加学科表头
    for subject in final_subjects:
        headers.append(html.Th(subject, className="small text-center", style={"minWidth": "60px"}))
    
    # 构建数据行
    rows = []
    for student in students:  # 显示所有学生
        row_data = [
            html.Td(student.get('姓名', ''), className="fw-semibold"),
            html.Td(student.get('学校', ''), className="small"),
            html.Td(student.get('行政班', ''), className="small")
        ]
        
        # 添加各学科成绩
        for subject in final_subjects:
            score = student.get(subject, '')
            # 高亮总分
            if '总分' in subject:
                cell_class = "fw-bold text-primary"
            else:
                cell_class = ""
            row_data.append(html.Td(score, className=f"small {cell_class} text-center"))
        
        rows.append(html.Tr(row_data))
    
    table = html.Table([
        html.Thead([html.Tr(headers)]),
        html.Tbody(rows)
    ], className="table table-sm table-hover", style={"fontSize": "0.85rem"})
    
    # 根据数据量决定是否添加滚动容器
    info_text = f"共 {len(students)} 名学生，{len(final_subjects)} 个学科"
    
    if len(students) > 15 or len(final_subjects) > 8:
        # 学生数量或学科数量较多时，添加双向滚动
        container_style = {
            "maxHeight": "500px", 
            "maxWidth": "100%",
            "overflow": "auto",
            "border": "1px solid #dee2e6",
            "borderRadius": "0.375rem",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
        }
        
        return html.Div([
            html.P(info_text, className="text-muted small mb-2"),
            html.Div(table, style=container_style)
        ])
    else:
        return html.Div([
            html.P(info_text, className="text-muted small mb-2"),
            table
        ])


def register_new_analysis_callbacks(app, data_store=None):
    """注册新增分析模块的回调函数"""
    # 设置全局数据存储引用
    if data_store is not None:
        set_global_data_store(data_store)
    
    # 临界生分析下拉菜单更新回调
    @app.callback(
        [
            Output("critical_county_dropdown", "options"),
            Output("critical_school_dropdown", "options"),
            Output("critical_class_dropdown", "options"),
            Output("critical_subject_dropdown", "options"),
        ],
        [Input("data_store", "data")],
        prevent_initial_call=False,
    )
    def update_critical_dropdowns_on_data_upload(data_json):
        """数据上传时更新临界生分析下拉菜单"""
        if data_json is None:
            return [], [], [], []
        
        try:
            from io import StringIO
            df = pd.read_json(StringIO(data_json), orient="split")
            from data_processor import DataProcessor
            
            processor = DataProcessor()
            options = {}
            
            # 获取区县选项
            county_cols = [col for col in df.columns if "区县" in col]
            if county_cols:
                counties = df[county_cols[0]].dropna().unique().tolist()
                options["county"] = [{"label": str(c), "value": str(c)} for c in sorted(counties)]
            else:
                options["county"] = []
            
            # 获取学校选项
            school_cols = [col for col in df.columns if "学校" in col and "行政班" not in col]
            if school_cols:
                schools = df[school_cols[0]].dropna().unique().tolist()
                options["school"] = [{"label": str(s), "value": str(s)} for s in sorted(schools)]
            else:
                options["school"] = []
            
            # 获取行政班选项
            class_cols = [col for col in df.columns if "行政班" in col]
            if class_cols:
                classes = df[class_cols[0]].dropna().unique().tolist()
                options["class"] = [{"label": str(c), "value": str(c)} for c in sorted(classes)]
            else:
                options["class"] = []
            
            # 获取学科选项（过滤掉非学科列）
            subject_cols = []
            for col in df.columns:
                if not any(exclude in col for exclude in ["区县", "学校", "行政班", "考生号", "姓名", "选科组合", "准考证号", "考生类型", "等级"]):
                    # 检查是否为数值列（学科分数）
                    try:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            subject_cols.append(col)
                    except:
                        continue
            
            # 按指定顺序排列学科：总分-语数外-理化生-史地政
            priority_order = ["新高考总分", "总分", "语文", "数学", "外语", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]
            ordered_subjects = []
            other_subjects = []
            
            for subject in subject_cols:
                matched = False
                for priority in priority_order:
                    if priority in subject:
                        if priority not in [s.split('(')[0] for s in ordered_subjects]:
                            ordered_subjects.append(subject)
                        matched = True
                        break
                if not matched:
                    other_subjects.append(subject)
            
            # 合并有序学科和其他学科，其他学科按字母顺序排序
            final_subjects = ordered_subjects + sorted(other_subjects)
            options["subject"] = [{"label": str(s), "value": str(s)} for s in final_subjects]
            
            logger.info(f"临界生分析下拉菜单更新 - 区县:{len(options['county'])}个, 学校:{len(options['school'])}个, 班级:{len(options['class'])}个, 学科:{len(options['subject'])}个")
            
            return options["county"], options["school"], options["class"], options["subject"]
            
        except Exception as e:
            logger.error(f"临界生分析下拉菜单更新失败: {e}")
            return [], [], [], []
    
    # 临界生分析二级联动回调（区县选择影响学校）
    @app.callback(
        [
            Output("critical_school_dropdown", "options", allow_duplicate=True),
            Output("critical_school_dropdown", "value", allow_duplicate=True),
        ],
        [Input("critical_county_dropdown", "value")],
        [State("data_store", "data")],
        prevent_initial_call=True,
    )
    def update_critical_schools_on_county_selection(selected_counties, data_json):
        """区县选择时更新学校下拉菜单"""
        if data_json is None or not selected_counties:
            return [], []
        
        try:
            from io import StringIO
            df = pd.read_json(StringIO(data_json), orient="split")
            
            school_cols = [col for col in df.columns if "学校" in col and "行政班" not in col]
            if not school_cols:
                return [], []
            
            # 根据选择的区县筛选学校
            county_cols = [col for col in df.columns if "区县" in col]
            if county_cols and selected_counties:
                filtered_df = df[df[county_cols[0]].isin(selected_counties)]
                schools = filtered_df[school_cols[0]].dropna().unique().tolist()
            else:
                schools = df[school_cols[0]].dropna().unique().tolist()
            
            school_options = [{"label": str(s), "value": str(s)} for s in sorted(schools)]
            
            return school_options, []
            
        except Exception as e:
            logger.error(f"临界生分析学校下拉菜单更新失败: {e}")
            return [], []
    
    # 临界生分析三级联动回调（学校选择影响班级）
    @app.callback(
        [
            Output("critical_class_dropdown", "options", allow_duplicate=True),
            Output("critical_class_dropdown", "value", allow_duplicate=True),
        ],
        [Input("critical_school_dropdown", "value")],
        [State("data_store", "data"), State("critical_county_dropdown", "value")],
        prevent_initial_call=True,
    )
    def update_critical_classes_on_school_selection(selected_schools, data_json, selected_counties):
        """学校选择时更新班级下拉菜单"""
        if data_json is None or not selected_schools:
            return [], []
        
        try:
            from io import StringIO
            df = pd.read_json(StringIO(data_json), orient="split")
            
            class_cols = [col for col in df.columns if "行政班" in col]
            if not class_cols:
                return [], []
            
            # 根据选择的区县和学校筛选班级
            filtered_df = df.copy()
            county_cols = [col for col in df.columns if "区县" in col]
            school_cols = [col for col in df.columns if "学校" in col and "行政班" not in col]
            
            if county_cols and selected_counties:
                filtered_df = filtered_df[filtered_df[county_cols[0]].isin(selected_counties)]
            if school_cols and selected_schools:
                filtered_df = filtered_df[filtered_df[school_cols[0]].isin(selected_schools)]
            
            classes = filtered_df[class_cols[0]].dropna().unique().tolist()
            class_options = [{"label": str(c), "value": str(c)} for c in sorted(classes)]
            
            return class_options, []
            
        except Exception as e:
            logger.error(f"临界生分析班级下拉菜单更新失败: {e}")
            return [], []
    
    # 临界生分析回调
    @app.callback(
        [
            Output("critical_analysis_status", "children"),
            Output("critical_analysis_chart", "figure"),
            Output("critical_summary_stats", "children"),
            Output("critical_details_table", "children"),
            Output("critical_type_stats", "children")
        ],
        [
            Input("analyze_critical_btn", "n_clicks"),
            Input("critical_special_line", "value"),
            Input("critical_bachelor_line", "value"),
        ],
        [
            State("data_store", "data"),
            State("critical_county_dropdown", "value"),
            State("critical_school_dropdown", "value"),
            State("critical_class_dropdown", "value"),
            State("critical_subject_dropdown", "value")
        ]
    )
    def update_critical_analysis(n_clicks, special_line, bachelor_line, data_json, selected_counties, selected_schools, selected_classes, selected_subjects):
        if n_clicks == 0 or data_json is None:
            return html.Div("请配置参数并点击分析", className="text-muted"), {"data": [], "layout": {}}, html.Div(), "", html.Div()
        
        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            
            # 应用筛选条件
            filtered_df = df.copy()
            
            # 筛选区县
            if selected_counties:
                county_cols = [col for col in df.columns if "区县" in col]
                if county_cols:
                    filtered_df = filtered_df[filtered_df[county_cols[0]].isin(selected_counties)]
            
            # 筛选学校
            if selected_schools:
                school_cols = [col for col in df.columns if "学校" in col and "行政班" not in col]
                if school_cols:
                    filtered_df = filtered_df[filtered_df[school_cols[0]].isin(selected_schools)]
            
            # 筛选班级
            if selected_classes:
                class_cols = [col for col in df.columns if "行政班" in col]
                if class_cols:
                    filtered_df = filtered_df[filtered_df[class_cols[0]].isin(selected_classes)]
            
            # 筛选学科（这里主要用于显示，实际分析由分析器处理）
            analysis_subject = None
            if selected_subjects and len(selected_subjects) == 1:
                analysis_subject = selected_subjects[0]
            
            logger.info(f"临界生分析筛选: 原始{len(df)}条 -> 筛选后{len(filtered_df)}条")
            
            analyzer = CriticalStudentsAnalyzer(filtered_df)
            
            results = analyzer.analyze_critical_students(
                special_line=float(special_line or 80),
                bachelor_line=float(bachelor_line or 60),
                subject_column=analysis_subject  # 传递分析的学科
            )
            
            if not results:
                return dbc.Alert("分析失败，请检查数据格式", color="danger"), {"data": [], "layout": {}}, html.Div(), "", html.Div()
            
            # 创建状态提示
            status = dbc.Alert([
                html.H5("✅ 临界生分析完成！", className="alert-heading"),
                html.P(f"特控线: {results['special_line']}分，本科线: {results['bachelor_line']}分")
            ], color="success")
            
            # 创建图表
            chart = analyzer.create_analysis_chart(results)
            
            # 创建统计概览（两列布局）
            summary_stats = html.Div([
                # 总体统计卡片
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📈 总体概况", className="text-primary mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.H4(f"{results.get('total_valid', 0)}", className="text-primary mb-1"),
                                html.P("有效学生总数", className="text-muted small")
                            ], width=6),
                            dbc.Col([
                                html.H4(f"{results['special_above']['count'] + results['special_below']['count'] + results['bachelor_above']['count'] + results['bachelor_below']['count']}", 
                                         className="text-success mb-1"),
                                html.P("临界生总数", className="text-muted small")
                            ], width=6)
                        ])
                    ])
                ], className="mb-3 shadow-sm"),
                
                # 分类型统计卡片（两列布局）
                dbc.Row([
                    # 特控线统计
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("🎯 特控线分析", className="text-warning mb-2"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['special_above']['count']}", className="text-success mb-0", style={"fontSize": "1.8rem"}),
                                            html.P("线上5分", className="text-muted small mb-0"),
                                            html.P(f"{results['special_above']['percentage']:.1f}%", className="text-success small")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=6),
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['special_below']['count']}", className="text-warning mb-0", style={"fontSize": "1.8rem"}),
                                            html.P("线下5分", className="text-muted small mb-0"),
                                            html.P(f"{results['special_below']['percentage']:.1f}%", className="text-warning small")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=6)
                                ])
                            ])
                        ], className="mb-2 shadow-sm")
                    ], width=12, lg=6),
                    
                    # 本科线统计
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("🎓 本科线分析", className="text-info mb-2"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['bachelor_above']['count']}", className="text-primary mb-0", style={"fontSize": "1.8rem"}),
                                            html.P("线上5分", className="text-muted small mb-0"),
                                            html.P(f"{results['bachelor_above']['percentage']:.1f}%", className="text-primary small")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=6),
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['bachelor_below']['count']}", className="text-danger mb-0", style={"fontSize": "1.8rem"}),
                                            html.P("线下5分", className="text-muted small mb-0"),
                                            html.P(f"{results['bachelor_below']['percentage']:.1f}%", className="text-danger small")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=6)
                                ])
                            ])
                        ], className="mb-2 shadow-sm")
                    ], width=12, lg=6)
                ])
            ])
            
            # 创建详细表格
            table_data = analyzer.get_detailed_table_data(results, show_details=True)
            details_table = create_results_table(table_data, "critical_students_details")
            
            # 创建分类详细统计（右侧展示）
            type_stats = html.Div([
# 各群体详细名单（折叠式展示）
            dbc.Accordion([
                dbc.AccordionItem([
                    html.P(f"占总体比例: {results['special_above']['percentage']:.1f}%", className="mb-2"),
                    _create_compact_student_table(results['special_above']['students'], "特控线上5分")
                ], title=[
                    html.Span("特控线上5分", className="text-success fw-bold"),
                    dbc.Badge(f"{results['special_above']['count']}人", color="success", className="ms-2")
                ]),
                
                dbc.AccordionItem([
                    html.P(f"占总体比例: {results['special_below']['percentage']:.1f}%", className="mb-2"),
                    _create_compact_student_table(results['special_below']['students'], "特控线下5分")
                ], title=[
                    html.Span("特控线下5分", className="text-warning fw-bold"),
                    dbc.Badge(f"{results['special_below']['count']}人", color="warning", className="ms-2")
                ]),
                
                dbc.AccordionItem([
                    html.P(f"占总体比例: {results['bachelor_above']['percentage']:.1f}%", className="mb-2"),
                    _create_compact_student_table(results['bachelor_above']['students'], "本科线上5分")
                ], title=[
                    html.Span("本科线上5分", className="text-primary fw-bold"),
                    dbc.Badge(f"{results['bachelor_above']['count']}人", color="primary", className="ms-2")
                ]),
                
                dbc.AccordionItem([
                    html.P(f"占总体比例: {results['bachelor_below']['percentage']:.1f}%", className="mb-2"),
                    _create_compact_student_table(results['bachelor_below']['students'], "本科线下5分")
                ], title=[
                    html.Span("本科线下5分", className="text-danger fw-bold"),
                    dbc.Badge(f"{results['bachelor_below']['count']}人", color="danger", className="ms-2")
                ]),
            ], start_collapsed=True, always_open=False)
            ])
            
            return status, chart, summary_stats, details_table, type_stats
            
        except Exception as e:
            logger.error(f"临界生分析回调错误: {str(e)}")
            error_alert = dbc.Alert([
                html.H5("❌ 分析失败", className="alert-heading"),
                html.P(f"错误信息: {str(e)}")
            ], color="danger")
            return error_alert, {"data": [], "layout": {}}, html.Div(), "", html.Div()
    
    # 尖子生分析下拉菜单更新回调
    @app.callback(
        [
            Output("top_county_dropdown", "options"),
            Output("top_school_dropdown", "options"),
            Output("top_class_dropdown", "options"),
        ],
        [Input("data_store", "data")],
        prevent_initial_call=False,
    )
    def update_top_dropdowns_on_data_upload(data_json):
        """数据上传时更新尖子生分析下拉菜单"""
        if data_json is None:
            return [], [], []
        
        try:
            from io import StringIO
            df = pd.read_json(StringIO(data_json), orient="split")
            
            # 获取区县选项
            county_cols = [col for col in df.columns if "区县" in col]
            county_options = []
            if county_cols:
                counties = df[county_cols[0]].dropna().unique()
                county_options = [{"label": str(c), "value": str(c)} for c in sorted(counties)]
            
            # 获取学校选项
            school_cols = [col for col in df.columns if "学校" in col and "行政班" not in col]
            school_options = []
            if school_cols:
                schools = df[school_cols[0]].dropna().unique()
                school_options = [{"label": str(s), "value": str(s)} for s in sorted(schools)]
            
            # 获取班级选项
            class_cols = [col for col in df.columns if "行政班" in col]
            class_options = []
            if class_cols:
                classes = df[class_cols[0]].dropna().unique()
                class_options = [{"label": str(c), "value": str(c)} for c in sorted(classes)]
            
            return county_options, school_options, class_options
            
        except Exception as e:
            logger.error(f"更新尖子生分析下拉菜单失败: {str(e)}")
            return [], [], []

    # 尖子生分析回调
    @app.callback(
        [
            Output("top_analysis_status", "children"),
            Output("top_analysis_chart", "figure"),
            Output("top_summary_stats", "children"),
            Output("top_details_table", "children"),
            Output("top_type_stats", "children")
        ],
        [
            Input("analyze_top_btn", "n_clicks"),
            Input("top_students_range", "value"),
        ],
        [
            State("data_store", "data"),
            State("top_county_dropdown", "value"),
            State("top_school_dropdown", "value"),
            State("top_class_dropdown", "value")
        ]
    )
    def update_top_analysis(n_clicks, top_n, data_json, selected_counties, selected_schools, selected_classes):
        if n_clicks == 0 or data_json is None:
            return html.Div("请配置参数并点击分析", className="text-muted"), {"data": [], "layout": {}}, html.Div(), ""
        
        try:
            df = pd.read_json(StringIO(data_json), orient="split")
            
            # 应用筛选条件
            filtered_df = df.copy()
            
            # 筛选区县
            if selected_counties:
                county_cols = [col for col in df.columns if "区县" in col]
                if county_cols:
                    filtered_df = filtered_df[filtered_df[county_cols[0]].isin(selected_counties)]
            
            # 筛选学校
            if selected_schools:
                school_cols = [col for col in df.columns if "学校" in col and "行政班" not in col]
                if school_cols:
                    filtered_df = filtered_df[filtered_df[school_cols[0]].isin(selected_schools)]
            
            # 筛选班级
            if selected_classes:
                class_cols = [col for col in df.columns if "行政班" in col]
                if class_cols:
                    filtered_df = filtered_df[filtered_df[class_cols[0]].isin(selected_classes)]
            
            logger.info(f"尖子生分析筛选: 原始{len(df)}条 -> 筛选后{len(filtered_df)}条")
            
            analyzer = TopStudentsAnalyzer(filtered_df)
            
            results = analyzer.analyze_top_students(top_n=int(top_n or 500))
            
            if not results:
                return dbc.Alert("分析失败，请检查数据格式", color="danger"), {"data": [], "layout": {}}, html.Div(), "", html.Div()
            
            # 创建状态提示
            status = dbc.Alert([
                html.H5("✅ 尖子生分析完成！", className="alert-heading"),
                html.P(f"排名范围: 前{results['top_n']}名，实际找到{results['actual_top_count']}人")
            ], color="success")
            
            # 创建图表
            chart = analyzer.create_analysis_chart(results)
            
            # 创建统计概览（两列布局）
            summary_stats = html.Div([
                # 总体统计卡片
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📈 尖子生概况", className="text-primary mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.H4(f"{results.get('total_valid', 0)}", className="text-primary mb-1"),
                                html.P("有效学生总数", className="text-muted small")
                            ], width=6),
                            dbc.Col([
                                html.H4(f"{results['actual_top_count']}", className="text-success mb-1", style={"fontSize": "1.8rem"}),
                                html.P("尖子生人数", className="text-muted small")
                            ], width=6)
                        ])
                    ])
                ], className="mb-3 shadow-sm"),
                
                # 分数统计卡片
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("📊 分数统计", className="text-info mb-2"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['score_stats']['max_score']:.1f}", className="text-success mb-0", style={"fontSize": "1.6rem"}),
                                            html.P("最高分", className="text-muted small mb-0")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=4),
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['score_stats']['min_score']:.1f}", className="text-warning mb-0", style={"fontSize": "1.6rem"}),
                                            html.P("最低分", className="text-muted small mb-0")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=4),
                                    dbc.Col([
                                        html.Div([
                                            html.H5(f"{results['score_stats']['avg_score']:.1f}", className="text-primary mb-0", style={"fontSize": "1.6rem"}),
                                            html.P("平均分", className="text-muted small mb-0")
                                        ], className="text-center p-2", style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
                                    ], width=4)
                                ])
                            ])
                        ], className="mb-2 shadow-sm")
                    ], width=12)
                ])
            ])
            
            # 创建详细表格
            details_table = _create_top_student_table(results['students'], "尖子生")
            
            # 创建分类详细统计（右侧展示）
            type_stats = html.Div([
                # 各区域尖子生分布（折叠式展示）
                dbc.Accordion([
                    dbc.AccordionItem([
                        html.P(f"占比: {len(results['students'])/results['total_valid']*100:.1f}%", className="mb-2"),
                        _create_top_student_table(results['students'][:20], "尖子生前20名")
                    ], title=[
                        html.Span("尖子生详细名单", className="text-success fw-bold"),
                        dbc.Badge(f"{len(results['students'])}人", color="success", className="ms-2")
                    ]),
                ], start_collapsed=True, always_open=False)
            ])
            
            return status, chart, summary_stats, details_table, type_stats
            
        except Exception as e:
            logger.error(f"尖子生分析回调错误: {str(e)}")
            error_alert = dbc.Alert([
                html.H5("❌ 分析失败", className="alert-heading"),
                html.P(f"错误信息: {str(e)}")
            ], color="danger")
            return error_alert, {"data": [], "layout": {}}, html.Div(), "", html.Div()
    
    # 小题分析回调
    @app.callback(
        [
            Output("question_analysis_status", "children"),
            Output("question_analysis_chart", "figure"),
            Output("question_summary_stats", "children"),
            Output("question_details_table", "children")
        ],
        [
            Input("analyze_question_btn", "n_clicks"),
        ],
        [
            State("data_store", "data")  # 保持兼容性，但不使用
        ]
    )
    def update_question_analysis(n_clicks, data_json):
        if n_clicks == 0:
            return html.Div("请先上传小题数据并点击分析", className="text-muted"), {"data": [], "layout": {}}, html.Div(), ""
        
        try:
            # 使用全局数据存储
            global _global_data_store
            if _global_data_store is None:
                return dbc.Alert("数据存储未初始化", color="warning"), {"data": [], "layout": {}}, html.Div(), ""
            
            question_df = _global_data_store.get_question_data()
            if question_df is None:
                return dbc.Alert("请先上传小题数据文件", color="warning"), {"data": [], "layout": {}}, html.Div(), ""
            
            analyzer = QuestionAnalysisAnalyzer(question_df)
            
            results = analyzer.analyze_questions()
            
            if not results:
                return dbc.Alert("分析失败，请检查数据格式", color="danger"), {"data": [], "layout": {}}, html.Div(), ""
            
            # 创建状态提示
            status = dbc.Alert([
                html.H5("✅ 小题分析完成！", className="alert-heading"),
                html.P(f"共分析{results['total_questions']}道小题")
            ], color="success")
            
            # 创建图表
            chart = analyzer.create_analysis_chart(results)
            
            # 创建统计概览
            summary_stats = analyzer.create_summary_stats(results)
            
            # 创建详细表格
            table_data = analyzer.get_detailed_table_data(results, show_details=True)
            details_table = create_results_table(table_data, "question_analysis_details")
            
            return status, chart, summary_stats, details_table
            
        except Exception as e:
            logger.error(f"小题分析回调错误: {str(e)}")
            error_alert = dbc.Alert([
                html.H5("❌ 分析失败", className="alert-heading"),
                html.P(f"错误信息: {str(e)}")
            ], color="danger")
            return error_alert, {"data": [], "layout": {}}, html.Div(), ""
    
    logger.info("新增分析模块回调函数注册完成")


def _create_top_student_table(students, group_type):
    """
    创建包含完整学科成绩的尖子生信息表格
    
    Args:
        students: 学生列表
        group_type: 群体类型
        
    Returns:
        html.Table: 包含完整学科成绩的表格
    """
    if not students:
        return html.P("暂无学生数据", className="text-muted small text-center")
    
    # 获取第一个学生来确定所有学科列
    if students:
        first_student = students[0]
        
        # 定义要排除的非学科列
        exclude_keywords = ["姓名", "学校", "行政班", "区县", "考生号", "选科组合", "准考证号", "考生类型", "等级", "市排名", "市排", "市rank"]
        
        # 获取所有学科列（数值列且不在排除列表中）
        subject_columns = []
        for key, value in first_student.items():
            if key not in exclude_keywords:
                # 进一步检查是否为学科分数（通常为数值型）
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit()):
                    subject_columns.append(key)
        
        # 按照优先级排序学科
        priority_order = ["新高考总分", "总分", "语文", "数学", "外语", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]
        ordered_subjects = []
        other_subjects = []
        
        for subject in subject_columns:
            matched = False
            for priority in priority_order:
                if priority in subject:
                    if priority not in [s.split('(')[0] for s in ordered_subjects]:
                        ordered_subjects.append(subject)
                    matched = True
                    break
            if not matched:
                other_subjects.append(subject)
        
        # 合并有序学科和其他学科
        final_subjects = ordered_subjects + sorted(other_subjects)
    else:
        final_subjects = []
    
    # 构建表头（添加排名列）
    headers = [html.Th("市排名", className="small text-center", style={"minWidth": "70px"}),
              html.Th("姓名", className="small text-center", style={"minWidth": "80px"}),
              html.Th("学校", className="small text-center", style={"minWidth": "100px"}),
              html.Th("班级", className="small text-center", style={"minWidth": "80px"})]
    
    # 添加学科表头
    for subject in final_subjects:
        headers.append(html.Th(subject, className="small text-center", style={"minWidth": "60px"}))
    
    # 构建数据行
    rows = []
    for student in students:  # 显示所有学生
        # 获取排名列名
        rank_col = None
        for col in ['市排名', '市排', '市rank']:
            if col in student:
                rank_col = col
                break
        
        if rank_col is None:
            # 如果没找到标准排名列，尝试查找其他排名列
            for key, value in student.items():
                if '排' in key and '名' in key:
                    rank_col = key
                    break
        
        row_data = [
            html.Td(student.get(rank_col, ''), className="fw-bold text-success text-center"),
            html.Td(student.get('姓名', ''), className="fw-semibold"),
            html.Td(student.get('学校', ''), className="small"),
            html.Td(student.get('行政班', ''), className="small")
        ]
        
        # 添加各学科成绩
        for subject in final_subjects:
            score = student.get(subject, '')
            # 高亮总分
            if '总分' in subject:
                cell_class = "fw-bold text-primary"
            else:
                cell_class = ""
            row_data.append(html.Td(score, className=f"small {cell_class} text-center"))
        
        rows.append(html.Tr(row_data))
    
    table = html.Table([
        html.Thead([html.Tr(headers)]),
        html.Tbody(rows)
    ], className="table table-sm table-hover", style={"fontSize": "0.85rem"})
    
    # 根据数据量决定是否添加滚动容器
    info_text = f"共 {len(students)} 名尖子生，{len(final_subjects)} 个学科"
    
    if len(students) > 15 or len(final_subjects) > 8:
        # 学生数量或学科数量较多时，添加双向滚动
        container_style = {
            "maxHeight": "500px", 
            "maxWidth": "100%",
            "overflow": "auto",
            "border": "1px solid #dee2e6",
            "borderRadius": "0.375rem",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
        }
        
        return html.Div([
            html.P(info_text, className="text-muted small mb-2"),
            html.Div(table, style=container_style)
        ])
    else:
        return html.Div([
            html.P(info_text, className="text-muted small mb-2"),
            table
        ])