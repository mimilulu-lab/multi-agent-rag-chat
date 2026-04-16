#!/usr/bin/env python3
"""
RPG Agent 系统主入口
启动命令: python main.py [--dev]
"""
import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RPG Chat API Server")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式：不构建前端，仅提供 API 服务"
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="构建前端后启动（生产模式）"
    )
    args = parser.parse_args()

    print("🚀 启动 RPG Agent 系统...")
    if args.dev:
        print("🔧 开发模式")
    else:
        print("📦 生产模式（将构建前端）")

    uvicorn.run(
        "api.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=args.dev,
    )
