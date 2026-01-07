#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试小题分析功能是否修复
"""

import pandas as pd
import numpy as np
from question_analysis_analyzer import QuestionAnalysisAnalyzer

def test_question_analysis():
    """测试小题分析功能"""
    print("🧪 测试小题分析功能...")
    
    # 创建模拟的小题数据
    np.random.seed(42)
    n_students = 30
    
    data = {
        '姓名': [f'学生{i+1}' for i in range(n_students)],
        '学校': ['高要一中'] * 15 + ['高要二中'] * 15,
        '班级': [f'高一{(i//5)+1}班' for i in range(n_students)],
        '缺考': ['否'] * n_students,
        '总分': np.random.normal(75, 10, n_students),
        '生物': np.random.normal(80, 8, n_students)
    }
    
    # 添加小题分数
    questions = ['1', '2', '3', '4', '5', '17(1)', '17(2)(3)', '18(1)(2)', '18(3)', '18(4)']
    for q in questions:
        max_score = np.random.choice([3, 4, 5, 6, 8, 10])
        data[q] = np.random.randint(0, max_score + 1, n_students)
    
    df = pd.DataFrame(data)
    
    try:
        # 创建分析器
        analyzer = QuestionAnalysisAnalyzer(df)
        print("✓ 小题分析器创建成功")
        
        # 执行分析
        results = analyzer.analyze_questions()
        print(f"✓ 分析完成，共分析{results.get('total_questions', 0)}道小题")
        
        # 创建图表
        chart = analyzer.create_analysis_chart(results)
        print("✓ 图表创建成功")
        
        # 创建统计概览
        summary = analyzer.create_summary_stats(results)
        print("✓ 统计概览创建成功")
        
        # 获取详细数据
        table_data = analyzer.get_detailed_table_data(results, show_details=True)
        print(f"✓ 详细表格数据获取成功，包含{len(table_data)}条记录")
        
        print("\n🎉 小题分析功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 小题分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_question_analysis()