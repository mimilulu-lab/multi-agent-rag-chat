# RPG Chat - 前端界面

基于 React + Vite 的现代化多 Agent 协作聊天系统前端。

## ✨ 特性

- 💬 **现代化聊天界面** - 侧边栏式布局，简洁清晰
- 🤖 **多 Agent 头像** - Manager 和 Worker 拥有独立渐变头像
- ⚡ **流式回复** - 实时打字机效果展示 Agent 回复
- 📜 **历史会话** - 支持 48 小时内会话的折叠式管理
- 📁 **配置面板** - Agent 配置、Provider 配置、知识库管理
- 🔄 **Manager / Worker 切换** - 支持团队模式与单 Agent 直接对话

## 🏗️ 架构

```
┌─────────────────────────────────────────────┐
│  前端 (React + Vite)                         │
│  ┌───────────────────────────────────────┐  │
│  │  侧边栏                                │  │
│  │  - AI 助手头像 + 状态                  │  │
│  │  - 导航菜单 (对话 / Agent / Provider)  │  │
│  │  - 历史会话 (可折叠)                   │  │
│  │  - 团队成员列表                        │  │
│  └───────────────────────────────────────┘  │
│                ↑                            │
│  ┌─────────────┴───────────────────────┐    │
│  │  主内容区                             │    │
│  │  - 聊天消息列表                        │    │
│  │  - 输入框 + 快捷操作                  │    │
│  │  - 配置页面 (Agent/Provider/KB)      │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                     ↑↓ HTTP
┌─────────────────────────────────────────────┐
│  后端 (FastAPI)                              │
│  - /api/chat/stream  - 流式对话接口          │
│  - /api/agents       - Agent 配置接口        │
│  - /api/providers    - Provider 配置接口     │
│  - /api/knowledge-bases - 知识库接口         │
│  - /api/conversations   - 会话管理接口       │
│  - /api/health       - 健康检查              │
└─────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式一：后端统一启动（生产模式）

```bash
# 在项目根目录执行，后端会自动构建前端静态文件
python main.py
```

访问：**http://localhost:8000**

### 方式二：开发模式（热更新）

适合开发调试，前后端分开启动：

```bash
# 终端 1：启动后端（仅 API，不构建前端）
python main.py --dev

# 终端 2：启动前端（热更新）
cd rpg-frontend
npm run dev
```

访问 http://localhost:5173

**区别说明：**

| 模式 | 后端角色 | 前端来源 | 访问地址 |
|------|---------|---------|----------|
| 生产模式 | API + 前端静态文件 | `rpg-frontend/dist` | `localhost:8000` |
| 开发模式 | 仅 API | Vite 开发服务器 | `localhost:5173` |

## 📁 项目结构

```
rpg-frontend/
├── src/
│   ├── api/
│   │   └── index.ts          # API 客户端
│   ├── pages/
│   │   ├── AgentConfigPage.tsx
│   │   ├── ProviderConfigPage.tsx
│   │   ├── KnowledgeBasePage.tsx
│   │   ├── ManagerConfigPage.tsx
│   │   └── ToolConfigPage.tsx
│   ├── types/
│   │   └── index.ts          # TypeScript 类型定义
│   ├── App.tsx               # 主应用组件 (聊天 + 侧边栏)
│   ├── index.css             # 全局样式
│   └── main.tsx              # 入口文件
├── package.json
├── package-lock.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
└── index.html
```

## 🎨 主题定制

编辑 `src/index.css`:

```css
:root {
  --primary-color: #4f46e5;
  --primary-hover: #4338ca;
  --bg-sidebar: #ffffff;
  --bg-main: #f8fafc;
  /* ... */
}
```

## 📦 技术栈

- **React 18** - UI 框架
- **Vite** - 构建工具
- **TypeScript** - 类型安全
- **Axios** - HTTP 客户端

## 📝 许可证

与原项目保持一致
