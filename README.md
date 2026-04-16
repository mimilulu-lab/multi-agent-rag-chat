# 🤖 RPG Multi-Agent System

> ⚠️ **早期开发阶段** | 🚧 **持续开发中** | 📝 **API 可能变动**

一个基于 **React + FastAPI** 的多 Agent 协作对话系统，支持 Manager-Worker 架构与 RAG 知识库

![Status](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![React](https://img.shields.io/badge/React-18+-61dafb)

---

## ✨ 核心特性

### 💬 现代化聊天界面
- **React + TypeScript 前端**：简洁现代的侧边栏式聊天界面
- **Agent 形象**：
  - Manager：紫色渐变头像
  - Worker：根据 avatar_type 分配不同渐变头像
- **流式回复**：实时打字机效果展示 Agent 回复
- **历史会话**：支持 48 小时内历史会话管理与恢复

### 🧠 多 Agent 架构
- **Manager-Worker 模式**：智能任务分派与结果整合
- **MsgHub 模式**：传统多 Agent 广播对话
- **独立模型配置**：每个 Agent 可配置不同的 LLM Provider

### 🔧 支持的模型提供商
| 提供商 | 状态 | 备注 |
|--------|------|------|
| DashScope (阿里云) | ✅ 已支持 | qwen 系列 |
| Moonshot (Kimi) | ✅ 已支持 | moonshot-v1 系列 |
| Anthropic | ✅ 已支持 | Claude 系列 |



### 🛠️ 工具系统
- 内置工具：文件操作、浏览器自动化
- 可扩展：支持自定义工具注册

---

## 🏗️ 项目架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React + Vite)                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  React UI 组件                                   │   │
│  │  - 侧边栏导航 (对话 / Agent / Provider / 知识库)  │   │
│  │  - 聊天消息列表 (支持流式输出)                    │   │
│  │  - 历史会话面板                                  │   │
│  │  - Agent / Provider / 知识库 配置面板            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            ↑↓ HTTP
┌─────────────────────────────────────────────────────────┐
│                   后端 (FastAPI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  Chat API   │  │ Agent API   │  │  Provider API   │ │
│  │  /api/chat  │  │ /api/agents │  │ /api/providers  │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ManagerAgent │  │ WorkerAgent │  │   ChatAgent     │ │
│  │  (任务协调)  │  │  (任务执行)  │  │  (普通对话)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↑↓
┌─────────────────────────────────────────────────────────┐
│              基础设施层                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   ChromaDB  │  │   配置文件   │  │    工具系统      │ │
│  │  向量数据库  │  │  (JSON)     │  │  (内置+扩展)     │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+

### 1. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd rpg-frontend
npm install
cd ..
```

### 2. 配置 Provider

首次启动后，在 Web 界面的 **"模型设置"** 页面中添加 LLM Provider（API Key 等）。

Provider 配置默认存储在 `~/.rag_agent/providers.json`。可通过环境变量覆盖存储位置：

```bash
export RAG_AGENT_CONFIG_DIR=/path/to/config
python main.py
```

### 3. 启动服务

**开发模式**（推荐）：
```bash
# 终端 1: 启动后端（开发模式，带热重载）
python main.py --dev

# 终端 2: 启动前端（独立开发服务器）
cd rpg-frontend
npm run dev
```

**生产模式**：
```bash
# 单命令启动（自动构建前端）
python main.py
```

### 4. 访问应用

- 前端界面：http://localhost:5173 （开发模式）或 http://localhost:8000 （生产模式）
- API 文档：http://localhost:8000/docs

---

## 📁 项目结构

```
.
├── agents/                 # Agent 实现
│   ├── manager_agent.py   # Manager 智能体（任务协调）
│   ├── chat_agent.py      # 基础对话智能体
│   └── __init__.py
├── api/                   # FastAPI 接口
│   ├── api_server.py      # 主服务入口
│   ├── agents_api.py      # Agent 配置接口
│   ├── providers_api.py   # Provider 配置接口
│   ├── knowledge_base_api.py  # 知识库接口
│   ├── conversation_api.py    # 会话管理接口
│   └── ...
├── config/                # 配置管理
│   ├── agents_config.py   # Agent 配置
│   ├── manager_config.py  # Manager 配置
│   └── ...
├── providers/             # LLM 提供商管理
│   ├── provider_manager.py
│   ├── dashscope_provider.py
│   ├── anthropic_provider.py
│   ├── kimi_provider.py
│   └── ...
├── tools/                 # 工具系统
│   ├── builtin/           # 内置工具
│   └── extensions/        # 扩展工具
├── rag_knowledge_base/    # RAG 知识库
├── rpg-frontend/          # 前端项目 (React + Vite)
│   ├── src/
│   │   ├── api/           # API 客户端
│   │   ├── pages/         # 页面组件
│   │   ├── types/         # TypeScript 类型定义
│   │   └── App.tsx        # 主应用组件
│   └── package.json
├── data/                  # 本地数据存储 (运行时使用，默认 gitignored)
├── main.py               # 主入口
├── start_server.sh       # 后端启动脚本
├── stop_server.sh        # 后端停止脚本
├── chat_cli.py           # 命令行对话工具（可选）
├── update_agents.py      # 批量更新 Agent Provider 的辅助脚本
├── requirements.txt      # Python 依赖
├── LICENSE               # MIT 许可证
└── .env.example          # 环境变量模板
```

---

## ⚙️ 配置说明

### 创建 Agent

1. 进入 **"Provider 配置"** 页面，添加 LLM 提供商（如 DashScope、OpenAI）
2. 进入 **"Agent 配置"** 页面，创建 Worker Agent
3. 可选：在 **"Manager 配置"** 中启用 Manager 模式

### Manager-Worker 模式

启用后：
- Manager 分析用户请求，拆解为子任务
- 分派给合适的 Worker 执行
- 收集结果并整合回复

不启用时：
- 使用传统 MsgHub 模式
- 所有 Agent 同时收到消息并独立回复

---

## 🔌 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat` | POST | 发送消息，获取 Agent 响应 |
| `/api/chat/stream` | POST | 流式对话接口（SSE） |
| `/api/agents` | GET | 获取所有 Agent 列表 |
| `/api/agents-config` | GET/POST/PUT/DELETE | Agent 配置 CRUD |
| `/api/providers` | GET/POST/PUT/DELETE | Provider 配置 CRUD |
| `/api/knowledge-bases` | GET/POST/DELETE | 知识库管理 |
| `/api/knowledge-bases/{id}/documents` | GET/POST | 知识库文档 |
| `/api/conversations` | GET/POST | 会话列表 / 创建 |
| `/api/conversations/{id}` | GET/DELETE | 会话详情 / 删除 |
| `/api/manager` | GET/PUT | Manager 配置 |
| `/api/system/reinitialize` | POST | 重新初始化系统 |
| `/api/health` | GET | 健康检查 |


本项目处于早期开发阶段，API 和架构可能随时调整。欢迎提交 Issue 和 PR！

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [AgentScope](https://github.com/modelscope/agentscope) - 多 Agent 框架参考
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://react.dev/) - UI 框架

---

> 🎮 **提示**：这是一个实验性项目，旨在探索多 Agent 协作的可视化交互方式。欢迎在 [Issues](../../issues) 中分享你的想法和建议！
