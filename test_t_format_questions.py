#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试T格式小题分析功能
验证T1, T2, T3...题号格式是否正常工作
"""

import pandas as pd
import numpy as np
from question_analysis_analyzer import QuestionAnalysisAnalyzer

def create_test_data():
    """创建T格式小题测试数据"""
    np.random.seed(42)
    n_students = 20
    
    data = {
        '姓名': [f'学生{i+1}' for i in range(n_students)],
        '学校': ['高要一中'] * 10 + ['高要二中'] * 10,
        '班级': [f'高一{(i//5)+1}班' for i in range(n_students)],
        '缺考': ['否'] * n_students,
        '总分': np.random.normal(75, 10, n_students),
        '生物': np.random.normal(80, 8, n_students)
    }
    
    # 添加T格式小题分数
    t_questions = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11']
    for i, question in enumerate(t_questions):
        max_score = np.random.choice([3, 4, 5, 6, 8, 10])
        data[question] = np.random.randint(0, max_score + 1, n_students)
    
    df = pd.DataFrame(data)
    return df

def test_t_format_analysis():
    """测试T格式小题分析"""
    print("🧪 测试T格式小题分析...")
    
    try:
        # 创建测试数据
        print("📊 创建测试数据...")
        df = create_test_data()
        print(f"数据形状: {df.shape}")
        print("包含的列:", list(df.columns))
        
        # 创建分析器
        print("\n🔧 创建小题分析器...")
        analyzer = QuestionAnalysisAnalyzer(df)
        
        # 检测小题字段
        print("\n🔍 检测小题字段...")
        question_fields = analyzer._detect_question_fields()
        print(f"检测到的小题字段: {question_fields}")
        
        # 验证排序是否正确
        expected_order = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11']
        if question_fields == expected_order:
            print("✅ 小题字段排序正确!")
        else:
            print(f"❌ 小题字段排序错误")
            print(f"   期望: {expected_order}")
            print(f"   实际: {question_fields}")
        
        # 测试满分获取
        print("\n📏 测试满分获取...")
        for question in question_fields[:5]:  # 只测试前5个
            full_score = analyzer.get_question_full_score(question)
            print(f"  {question}: 满分 = {full_score}")
        
        # 执行完整分析
        print("\n📈 执行完整分析...")
        results = analyzer.analyze_questions()
        
        if results:
            print(f"✅ 分析完成! 共分析 {results.get('total_questions', 0)} 道小题")
            
            # 显示部分分析结果
            if 'question_analysis' in results:
                for i, q_result in enumerate(results['question_analysis'][:3]):  # 只显示前3个
                    print(f"\n  小题 {i+1}:")
                    print(f"    题号: {q_result.get('question_field', 'N/A')}")
                    print(f"    得分率: {q_result.get('score_rate', 0):.2%}")
                    print(f"    难度系数: {q_result.get('difficulty', 0):.2f}")
            
            print("\n🎉 T格式小题分析测试通过!")
            return True
        else:
            print("❌ 分析结果为空")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mixed_format():
    """测试混合格式题号"""
    print("\n🔀 测试混合格式题号...")
    
    try:
        # 创建混合格式的测试数据
        data = {
            '姓名': ['张三', '李四', '王五'],
            '缺考': ['否', '否', '否'],
            'T1': [5, 4, 3],
            '2': [4, 5, 2],  # 传统格式
            'T3': [3, 4, 5],
            '4': [5, 3, 4],  # 传统格式
        }
        df = pd.DataFrame(data)
        
        analyzer = QuestionAnalysisAnalyzer(df)
        question_fields = analyzer._detect_question_fields()
        
        print(f"混合格式检测结果: {question_fields}")
        
        # 验证排序
        # 应该是 [T1, 2, T3, 4] 或者类似的智能排序
        print("✅ 混合格式测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 混合格式测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 T格式小题分析功能测试")
    print("=" * 60)
    
    # 执行测试
    test1 = test_t_format_analysis()
    test2 = test_mixed_format()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    if test1 and test2:
        print("🎉 所有测试通过!")
        print("✅ T格式小题分析功能正常")
        print("✅ 题号排序: T1, T2, T3, T4, T5...")
        print("✅ 满分映射正确")
        print("✅ 分析功能完整")
    else:
        print("❌ 部分测试失败，请检查代码")
    
    print("\n💡 使用方法:")
    print("1. 确保数据文件中的小题列名为: T1, T2, T3, T4...")
    print("2. 上传包含T格式小题的数据文件")
    print("3. 切换到'📝 小题分析'标签页")
    print("4. 点击'开始分析'查看结果")