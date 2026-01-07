#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统启动诊断工具
用于诊断成绩分析系统启动缓慢的问题
"""

import time
import importlib
import traceback
import sys
from pathlib import Path

def test_import(module_name, description=""):
    """测试模块导入时间"""
    start_time = time.time()
    try:
        importlib.import_module(module_name)
        end_time = time.time()
        print(f"✓ {module_name} {description} - {(end_time - start_time)*1000:.1f}ms")
        return True
    except Exception as e:
        end_time = time.time()
        print(f"✗ {module_name} {description} - {(end_time - start_time)*1000:.1f}ms - ERROR: {e}")
        return False

def test_local_import(file_path, module_name, description=""):
    """测试本地文件导入时间"""
    start_time = time.time()
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"✗ {module_name} - 文件不存在: {file_path}")
            return False
            
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        end_time = time.time()
        print(f"✓ {module_name} {description} - {(end_time - start_time)*1000:.1f}ms")
        return True
    except Exception as e:
        end_time = time.time()
        print(f"✗ {module_name} {description} - {(end_time - start_time)*1000:.1f}ms - ERROR: {e}")
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("成绩分析系统启动诊断工具")
    print("=" * 60)
    
    # 测试基础包导入
    print("\n📦 测试基础Python包导入:")
    basic_packages = [
        ("os", "系统操作"),
        ("sys", "系统相关"),
        ("time", "时间处理"),
        ("json", "JSON处理"),
        ("pandas", "数据分析"),
        ("numpy", "数值计算"),
        ("dash", "Web框架"),
        ("dash_bootstrap_components", "Dash UI组件"),
        ("plotly", "图表库"),
        ("matplotlib", "图表库"),
        ("reportlab", "PDF生成"),
    ]
    
    basic_results = []
    for package, desc in basic_packages:
        basic_results.append(test_import(package, desc))
    
    # 测试核心模块导入
    print("\n🔧 测试核心模块导入:")
    core_modules = [
        ("data_processor.py", "data_processor", "数据处理"),
        ("quadrant_analyzer.py", "quadrant_analyzer", "四象限分析"),
        ("comprehensive_analyzer.py", "comprehensive_analyzer", "综合分析"),
        ("cascade_statistics_analyzer.py", "cascade_statistics_analyzer", "级联统计"),
        ("effective_group_analyzer.py", "effective_group_analyzer", "有效分组"),
        ("critical_students_analyzer.py", "critical_students_analyzer", "临界生分析"),
        ("top_students_analyzer.py", "top_students_analyzer", "优秀生分析"),
        ("question_analysis_analyzer.py", "question_analysis_analyzer", "题目分析"),
    ]
    
    core_results = []
    import importlib.util
    
    for file_path, module_name, desc in core_modules:
        core_results.append(test_local_import(file_path, module_name, desc))
    
    # 测试UI模块导入
    print("\n🎨 测试UI模块导入:")
    ui_modules = [
        ("effective_group_ui.py", "effective_group_ui", "有效分组UI"),
        ("goal_completion_ui.py", "goal_completion_ui", "目标完成UI"),
        ("critical_students_ui.py", "critical_students_ui", "临界生UI"),
        ("new_analysis_ui.py", "new_analysis_ui", "新分析UI"),
    ]
    
    ui_results = []
    for file_path, module_name, desc in ui_modules:
        ui_results.append(test_local_import(file_path, module_name, desc))
    
    # 测试回调模块导入
    print("\n⚙️ 测试回调模块导入:")
    callback_modules = [
        ("effective_group_callbacks.py", "effective_group_callbacks", "有效分组回调"),
        ("goal_completion_callbacks.py", "goal_completion_callbacks", "目标完成回调"),
        ("new_analysis_callbacks.py", "new_analysis_callbacks", "新分析回调"),
    ]
    
    callback_results = []
    for file_path, module_name, desc in callback_modules:
        callback_results.append(test_local_import(file_path, module_name, desc))
    
    # 测试其他模块
    print("\n🛠️ 测试其他模块导入:")
    other_modules = [
        ("pdf_exporter.py", "pdf_exporter", "PDF导出"),
        ("goal_completion_analyzer.py", "goal_completion_analyzer", "目标完成分析"),
    ]
    
    other_results = []
    for file_path, module_name, desc in other_modules:
        other_results.append(test_local_import(file_path, module_name, desc))
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结:")
    print("=" * 60)
    
    total_basic = len(basic_results)
    total_core = len(core_results)
    total_ui = len(ui_results)
    total_callback = len(callback_results)
    total_other = len(other_results)
    
    success_basic = sum(basic_results)
    success_core = sum(core_results)
    success_ui = sum(ui_results)
    success_callback = sum(callback_results)
    success_other = sum(other_results)
    
    print(f"基础包: {success_basic}/{total_basic} 成功")
    print(f"核心模块: {success_core}/{total_core} 成功")
    print(f"UI模块: {success_ui}/{total_ui} 成功")
    print(f"回调模块: {success_callback}/{total_callback} 成功")
    print(f"其他模块: {success_other}/{total_other} 成功")
    
    total_modules = total_basic + total_core + total_ui + total_callback + total_other
    total_success = success_basic + success_core + success_ui + success_callback + success_other
    
    print(f"\n总体: {total_success}/{total_modules} 模块成功导入")
    
    if total_success == total_modules:
        print("✅ 所有模块导入成功！系统应该可以正常启动")
        print("\n💡 如果启动仍然缓慢，可能是以下原因:")
        print("1. 硬件性能不足（建议至少8GB内存）")
        print("2. 首次启动需要编译缓存")
        print("3. 网络连接问题（某些库需要网络验证）")
        print("4. 防病毒软件扫描")
    else:
        print("❌ 部分模块导入失败，请检查错误信息")
        print("\n🔧 建议的解决方案:")
        print("1. 检查Python环境是否完整")
        print("2. 重新安装依赖包: pip install -r requirements.txt")
        print("3. 检查文件完整性")
    
    print("\n⏱️ 总诊断时间:", f"{time.time() - start_time:.2f}秒")

if __name__ == "__main__":
    start_time = time.time()
    main()