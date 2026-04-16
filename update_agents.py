#!/usr/bin/env python3
"""
更新Agent配置，使用Kimi Provider
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "agents_config.json")

def update_agents():
    """更新所有Agent使用kimi_main provider"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = 0
    for agent in data.get("agents", []):
        if agent.get("provider_id") != "kimi_main":
            agent["provider_id"] = "kimi_main"
            updated += 1
            print(f"✅ 更新 {agent['name']} -> 使用 kimi_main")

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n总共更新 {updated} 个Agent")

if __name__ == "__main__":
    update_agents()
