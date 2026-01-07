#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 检查系统基本功能
"""

import time
import sys
import os

def test_basic_imports():
    """测试基础模块导入"""
    print("🔍 测试基础模块导入...")
    
    modules = [
        "os", "sys", "time", "json",
        "pandas", "numpy",
        "dash", "dash_bootstrap_components"
    ]
    
    success_count = 0
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
            success_count += 1
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
    
    return success_count == len(modules)

def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")
    
    try:
        import pandas as pd
        import numpy as np
        
        # 测试pandas基本功能
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        print("  ✓ Pandas基本操作")
        
        # 测试numpy基本功能
        arr = np.array([1, 2, 3])
        print("  ✓ Numpy基本操作")
        
        return True
    except Exception as e:
        print(f"  ❌ 基本功能测试失败: {e}")
        return False

def test_dash_basic():
    """测试Dash基本功能"""
    print("\n🌐 测试Dash基本功能...")
    
    try:
        import dash
        from dash import html, dcc
        
        # 创建最小化应用
        app = dash.Dash(__name__)
        app.layout = html.Div([html.H1("测试")])
        
        print("  ✓ Dash应用创建")
        return True
    except Exception as e:
        print(f"  ❌ Dash测试失败: {e}")
        return False

def check_files():
    """检查必要文件"""
    print("\n📁 检查必要文件...")
    
    required_files = [
        "app.py",
        "data_processor.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ❌ {file} (缺失)")
            missing_files.append(file)
    
    return len(missing_files) == 0

def main():
    print("=" * 50)
    print("🚀 成绩分析系统快速测试")
    print("=" * 50)
    
    start_time = time.time()
    
    # 执行测试
    tests = [
        ("基础模块导入", test_basic_imports),
        ("基本功能", test_basic_functionality),
        ("Dash框架", test_dash_basic),
        ("文件完整性", check_files),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:15} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("\n🎉 所有测试通过！系统环境正常")
        print("\n💡 如果系统仍然启动缓慢，建议:")
        print("1. 使用 fast_start.py 启动")
        print("2. 检查硬件性能（内存和CPU）")
        print("3. 关闭不必要的后台程序")
        print("4. 检查网络连接")
    else:
        print("\n⚠️ 部分测试失败，请:")
        print("1. 重新安装依赖: pip install -r requirements.txt")
        print("2. 检查Python环境")
        print("3. 运行 startup_diagnosis.py 获取详细信息")
    
    print(f"\n⏱️ 测试耗时: {time.time() - start_time:.2f}秒")

if __name__ == "__main__":
    main()