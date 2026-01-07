#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化启动脚本 - 简化版本
直接使用原始app.py但增加进度显示
"""

import os
import sys
import time
import threading
import webbrowser

def print_progress(step, description, duration=None):
    """显示进度信息"""
    if duration:
        print(f"✅ {step} - {description} ({duration:.1f}ms)")
    else:
        print(f"🔄 {step} - {description}...")

def create_directories():
    """创建必要的目录"""
    start_time = time.time()
    dirs = ["uploads", "reports", "exports", "static"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
    duration = (time.time() - start_time) * 1000
    print_progress("📁", "创建必要目录", duration)

def check_environment():
    """检查运行环境"""
    start_time = time.time()
    
    # 检查Python版本
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 检查关键依赖
    key_modules = [
        "dash", "pandas", "numpy", "plotly", 
        "dash_bootstrap_components", "matplotlib", "reportlab"
    ]
    
    missing_modules = []
    for module in key_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("❌ 缺少依赖模块:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\n请运行: pip install -r requirements.txt")
        return False
    
    duration = (time.time() - start_time) * 1000
    print_progress("🔧", "环境检查", duration)
    return True

def start_application():
    """启动应用程序"""
    print("\n" + "="*60)
    print("🚀 成绩分析系统启动中...")
    print("="*60)
    
    # 环境检查
    if not check_environment():
        return
    
    # 创建目录
    create_directories()
    
    # 导入主应用（这需要一些时间）
    start_time = time.time()
    print_progress("📦", "导入主应用模块")
    
    try:
        # 优化matplotlib设置
        import matplotlib
        matplotlib.use('Agg')  # 非交互式后端
        
        # 导入主应用
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import app, data_store, find_free_port
        
        duration = (time.time() - start_time) * 1000
        print_progress("✅", "应用模块导入完成", duration)
        
        # 寻找端口并启动
        print_progress("🌐", "准备启动服务器")
        port = find_free_port()
        url = f"http://127.0.0.1:{port}"
        
        # 延迟打开浏览器
        def open_browser():
            time.sleep(3)  # 等待3秒让服务器启动
            try:
                webbrowser.open(url)
                print(f"\n✅ 浏览器已打开: {url}")
            except Exception as e:
                print(f"⚠️ 无法自动打开浏览器: {e}")
                print(f"请手动访问: {url}")
        
        # 启动浏览器线程
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        print(f"\n🎯 访问地址: {url}")
        print("📝 按 Ctrl+C 停止系统")
        print("="*60)
        
        # 启动应用
        start_time = time.time()
        app.run(host="127.0.0.1", port=port, debug=False)
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    total_start = time.time()
    
    try:
        start_application()
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
    except Exception as e:
        print(f"\n💥 系统错误: {e}")
        import traceback
        traceback.print_exc()
    
    total_time = time.time() - total_start
    print(f"⏱️ 总运行时间: {total_time:.2f}秒")