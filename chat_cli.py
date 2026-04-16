#!/usr/bin/env python3
"""
简单的命令行对话工具
"""
import requests
import json
import sys

API_URL = "http://localhost:8000/api/chat"

def chat(message):
    """发送消息并显示回复"""
    try:
        response = requests.post(
            API_URL,
            json={"message": message},
            timeout=60
        )
        data = response.json()

        if "detail" in data:
            print(f"❌ 错误: {data['detail']}")
            return

        print("\n" + "="*60)
        for resp in data.get("responses", []):
            print(f"\n🤖 {resp['agent_name']} ({resp['agent_role']})")
            print("-" * 40)
            print(resp['content'])
        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    print("💬 RPG Agent 对话系统")
    print("输入 'quit' 退出\n")

    while True:
        user_input = input("你: ").strip()

        if user_input.lower() in ['quit', 'exit', 'q']:
            print("再见！👋")
            break

        if not user_input:
            continue

        chat(user_input)
