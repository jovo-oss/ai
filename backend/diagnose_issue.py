"""
快速诊断：测试smart-parse接口是否使用了新代码
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_api_endpoint():
    """测试API端点是否响应"""
    print("=" * 60)
    print("🔍 诊断：检查smart-parse接口")
    print("=" * 60)

    try:
        # 测试接口是否存在
        response = requests.get(f"{API_BASE}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务正常运行 (FastAPI文档可访问)")
            return True
        else:
            print(f"❌ 后端服务异常 (状态码: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
        print("\n💡 请确保后端服务已启动:")
        print("   cd c:\\Trae\\PyChat_\\ai_chat_system\\backend")
        print("   uvicorn app.main:app --reload --port 8000")
        return False


def check_code_version():
    """检查代码是否包含新的多策略降级逻辑"""
    print("\n" + "=" * 60)
    print("📝 检查：memory_events.py是否包含新代码")
    print("=" * 60)

    try:
        with open('app/routes/memory_events.py', 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ("多策略降级系统", "多策略降级解析"),
            ("简单表格格式解析器", "parse_simple_table_format"),
            ("文本关键词提取器", "extract_entities_from_text"),
            ("第2级降级提示词", "简单表格格式输出"),
            ("第3级后备策略", "最终后备：纯文本关键词提取"),
        ]

        all_found = True
        for name, keyword in checks:
            if keyword in content:
                print(f"✅ 找到: {name}")
            else:
                print(f"❌ 缺失: {name}")
                all_found = False

        if all_found:
            print("\n✅ 所有新功能都已正确添加到代码中!")
            return True
        else:
            print("\n⚠️ 部分功能缺失，代码可能未完全保存")
            return False

    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False


def main():
    """主诊断流程"""
    print("\n" + "🚀" * 30)
    print("\n📋 Smart-Parse 接口快速诊断工具")
    print("🚀" * 30 + "\n")

    # 检查1：代码是否完整
    code_ok = check_code_version()

    # 检查2：服务是否运行
    service_ok = test_api_endpoint()

    # 总结
    print("\n" + "=" * 60)
    print("📊 诊断结果总结")
    print("=" * 60)

    if code_ok and service_ok:
        print("""
✅ 代码和服务都正常！

💡 如果仍然报错，请执行以下操作：
1. 完全关闭当前的后端服务进程（Ctrl+C）
2. 重新启动服务：
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
3. 等待看到 "Uvicorn running on http://0.0.0.0:8000"
4. 刷新浏览器页面（Ctrl+F5 强制刷新）
5. 重新点击"智能解析"

📝 启动后你应该在后端终端看到类似这样的日志：
======================================================================
🚀 [智能解析] 开始多策略降级解析
   聊天记录数: XX 条
   模式: auto
======================================================================
[第1级] 📋 尝试标准JSON解析...
...
""")
        return 0
    elif not code_ok:
        print("\n⚠️ 代码文件不完整，需要重新保存修改")
        return 1
    elif not service_ok:
        print("\n⚠️ 后端服务未运行或无法访问")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
