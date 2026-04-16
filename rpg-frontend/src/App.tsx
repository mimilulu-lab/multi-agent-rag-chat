import { useEffect, useState, useCallback, useRef } from 'react'
import { api } from './api'
import type { ChatMessage, AgentInfo, Conversation } from './types'
import { AgentConfigPage } from './pages/AgentConfigPage'
import { ProviderConfigPage } from './pages/ProviderConfigPage'
import { KnowledgeBasePage } from './pages/KnowledgeBasePage'

type Page = 'chat' | 'agents' | 'providers' | 'knowledge'

// 图标组件
const ChatIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
)

const AgentIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 16v-4M12 8h.01"/>
  </svg>
)

const SettingsIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3"/>
    <path d="M12 1v6m0 6v10m4.22-14.22l4.24 4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24 4.24l-4.24-4.24M6.34 6.34L2.1 2.1"/>
  </svg>
)

const DatabaseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <ellipse cx="12" cy="5" rx="9" ry="3"/>
    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
  </svg>
)

const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)

const MenuIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
)

// 头像颜色映射（按 avatar_type）
const avatarColors: Record<string, string> = {
  'manager': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'aiden': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'wrench': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
}

// 头像组件
const Avatar = ({ name, avatarType, size = 40 }: { name: string; avatarType?: string; size?: number }) => {
  const bg = avatarColors[avatarType || 'manager'] || avatarColors['manager']
  const initial = name.charAt(0).toUpperCase()

  return (
    <div
      className="avatar"
      style={{
        width: size,
        height: size,
        background: bg,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: size * 0.4,
        fontWeight: 'bold',
        flexShrink: 0,
      }}
    >
      {initial}
    </div>
  )
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentPage, setCurrentPage] = useState<Page>('chat')
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [loadingConversations, setLoadingConversations] = useState(false)
  const [conversationsExpanded, setConversationsExpanded] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 获取 Agent 列表
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const agentList = await api.getAgents()
        setAgents(agentList)
      } catch (err) {
        console.error('Failed to fetch agents:', err)
      }
    }
    fetchAgents()
  }, [currentPage])

  // 加载历史会话列表
  const loadConversations = useCallback(async (agentId?: string) => {
    setLoadingConversations(true)
    try {
      const result = await api.getConversations(agentId)
      if (result.success) {
        setConversations(result.conversations)
      }
    } catch (err) {
      console.error('Failed to load conversations:', err)
    }
    setLoadingConversations(false)
  }, [])

  useEffect(() => {
    if (currentPage === 'chat') {
      loadConversations()
    }
  }, [currentPage, loadConversations])

  // 加载指定会话的消息
  const loadConversationMessages = useCallback(async (conversationId: string) => {
    try {
      const result = await api.getConversation(conversationId)
      if (result.success && result.conversation) {
        const conv = result.conversation
        const loadedMessages: ChatMessage[] = conv.messages.map((m: any) => {
          const senderAgent = m.agent_name ? agents.find(a => a.name === m.agent_name) : undefined
          return {
            id: m.id,
            role: m.role as 'user' | 'assistant' | 'error',
            content: m.content,
            timestamp: m.timestamp * 1000,
            agentName: m.agent_name,
            agentRole: m.agent_role,
            agentAvatarType: senderAgent?.avatar_type,
            isStreaming: false,
            isError: m.role === 'error',
          }
        })
        setMessages(loadedMessages)
        setActiveConversationId(conv.conversation_id)
        if (conv.agent_id) {
          const agent = agents.find(a => a.id === conv.agent_id)
          if (agent) setSelectedAgent(agent)
          else setSelectedAgent(null)
        } else {
          setSelectedAgent(null)
        }
      }
    } catch (err) {
      console.error('Failed to load conversation messages:', err)
    }
  }, [agents])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 处理发送消息 - 流式输出
  const handleSend = useCallback(async () => {
    if (!inputText.trim() || isProcessing) return

    const text = inputText.trim()
    setInputText('')

    // 确保有活跃的会话
    let conversationId = activeConversationId
    if (!conversationId) {
      try {
        const result = await api.createConversation(
          text.slice(0, 20) + (text.length > 20 ? '...' : ''),
          selectedAgent?.id
        )
        if (result.success) {
          conversationId = result.conversation.conversation_id
          setActiveConversationId(conversationId)
          setConversations(prev => [result.conversation, ...prev])
        }
      } catch (err) {
        console.error('Failed to create conversation:', err)
      }
    }

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMessage])
    setIsProcessing(true)

    const streamingMessages = new Map<string, string>()

    api.chatStream(
      text,
      (chunk) => {
        switch (chunk.type) {
          case 'start':
          case 'agent_start':
            if (chunk.agent_name) {
              const messageId = `msg_${Date.now()}_${chunk.index}_${Math.random().toString(36).substr(2, 9)}`
              streamingMessages.set(chunk.agent_name, messageId)

              const senderAgent = agents.find(a => a.name === chunk.agent_name)
              const newMessage: ChatMessage = {
                id: messageId,
                role: 'assistant',
                content: '',
                timestamp: Date.now(),
                agentName: chunk.agent_name,
                agentRole: chunk.agent_role,
                agentAvatarType: senderAgent?.avatar_type,
                isStreaming: true
              }
              setMessages(prev => [...prev, newMessage])
            }
            break

          case 'chunk':
            if (chunk.agent_name && chunk.content) {
              const messageId = streamingMessages.get(chunk.agent_name)
              if (messageId) {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === messageId
                      ? { ...msg, content: msg.content + chunk.content }
                      : msg
                  )
                )
              }
            }
            break

          case 'done':
          case 'agent_done':
            if (chunk.agent_name) {
              const messageId = streamingMessages.get(chunk.agent_name)
              if (messageId) {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === messageId
                      ? { ...msg, isStreaming: false }
                      : msg
                  )
                )
              }
            }
            break

          case 'all_done':
            setIsProcessing(false)
            // 刷新会话列表以更新时间和消息数
            if (conversationId) {
              loadConversations(selectedAgent?.id)
            }
            break

          case 'error':
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'error',
              content: chunk.message || '请求失败',
              timestamp: Date.now(),
              isError: true
            }])
            setIsProcessing(false)
            break
        }
      },
      (error) => {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'error',
          content: error,
          timestamp: Date.now(),
          isError: true
        }])
        setIsProcessing(false)
      },
      selectedAgent?.id,  // 传递选中的 Agent ID
      conversationId || undefined  // 传递会话 ID
    )
  }, [inputText, isProcessing, selectedAgent?.id, activeConversationId, loadConversations])

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 获取 Manager 信息
  const managerAgent = agents.find(a => a.avatar_type === 'manager')

  // 格式化相对时间
  const formatTime = (timestamp: number) => {
    const now = Date.now()
    const diff = now - timestamp * 1000
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return `${Math.floor(hours / 24)}天前`
  }

  // 处理选择 Worker Agent
  const handleSelectAgent = async (agent: AgentInfo) => {
    if (agent.avatar_type === 'manager') {
      setSelectedAgent(null)
    } else {
      setSelectedAgent(agent)
    }
    setCurrentPage('chat')

    // 加载该 Agent 的最新会话
    try {
      const result = await api.getConversations(agent.avatar_type === 'manager' ? undefined : agent.id)
      if (result.success && result.conversations.length > 0) {
        // 找到匹配的会话：manager 对应团队会话(agent_id为null)，worker 对应自己的会话
        const targetConv = result.conversations.find(c =>
          agent.avatar_type === 'manager' ? !c.agent_id : c.agent_id === agent.id
        )
        if (targetConv) {
          await loadConversationMessages(targetConv.conversation_id)
        } else {
          setMessages([])
          setActiveConversationId(null)
        }
      } else {
        setMessages([])
        setActiveConversationId(null)
      }
    } catch (err) {
      console.error('Failed to load agent conversation:', err)
      setMessages([])
      setActiveConversationId(null)
    }
  }

  // 新建会话
  const handleNewConversation = async () => {
    try {
      const result = await api.createConversation('新对话', selectedAgent?.id)
      if (result.success) {
        setActiveConversationId(result.conversation.conversation_id)
        setMessages([])
        setConversations(prev => [result.conversation, ...prev])
        setCurrentPage('chat')
      }
    } catch (err) {
      console.error('Failed to create conversation:', err)
    }
  }

  // 删除会话
  const handleDeleteConversation = async (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    if (!confirm('确定要删除这个会话吗？')) return
    try {
      await api.deleteConversation(conversationId)
      setConversations(prev => prev.filter(c => c.conversation_id !== conversationId))
      if (activeConversationId === conversationId) {
        setActiveConversationId(null)
        setMessages([])
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err)
    }
  }

  // 获取当前显示的 Agent
  const currentAgent = selectedAgent || managerAgent

  // 图标组件
  const ChevronDownIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  )

  const PlusIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  )

  // 可折叠历史会话面板
  const ConversationSection = () => (
    <div className="conversation-section">
      <div
        className="conversation-header"
        onClick={() => setConversationsExpanded(!conversationsExpanded)}
      >
        <span className="conversation-title">历史会话</span>
        <span className={`conversation-chevron ${conversationsExpanded ? 'expanded' : ''}`}>
          <ChevronDownIcon />
        </span>
      </div>
      {conversationsExpanded && (
        <div className="conversation-list-container">
          <button className="new-conversation-btn" onClick={handleNewConversation}>
            <PlusIcon />
            <span>新建会话</span>
          </button>
          {loadingConversations ? (
            <div className="conversation-loading">加载中...</div>
          ) : conversations.length === 0 ? (
            <div className="conversation-empty">暂无历史会话</div>
          ) : (
            <div className="conversation-list">
              {conversations.map(conv => (
                <div
                  key={conv.conversation_id}
                  className={`conversation-item ${activeConversationId === conv.conversation_id ? 'active' : ''}`}
                  onClick={() => loadConversationMessages(conv.conversation_id)}
                >
                  <div className="conversation-item-main">
                    <span className="conversation-item-title">{conv.title}</span>
                    <span className="conversation-item-meta">
                      {conv.message_count} 条 · {formatTime(conv.updated_at)}
                    </span>
                  </div>
                  <button
                    className="conversation-delete-btn"
                    onClick={(e) => handleDeleteConversation(e, conv.conversation_id)}
                    title="删除会话"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <div className="app">
      {/* 左侧边栏 */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-icon">🤖</span>
            <h1>AI 助手</h1>
          </div>
        </div>

        {/* AI 助手信息 */}
        <div className="assistant-info">
          <div className="assistant-avatar-large">
            <Avatar name={currentAgent?.name || 'AI'} avatarType={currentAgent?.avatar_type} size={64} />
          </div>
          <h3 className="assistant-name">{currentAgent?.name || 'AI 助手'}</h3>
          <p className="assistant-role">{currentAgent?.role || '智能助手'}</p>
          <div className={`status-badge ${isProcessing ? 'busy' : 'online'}`}>
            <span className="status-dot"></span>
            {isProcessing ? '思考中...' : '在线'}
          </div>
          {selectedAgent && (
            <p style={{ fontSize: '12px', color: 'var(--primary-color)', marginTop: '8px' }}>
              正在与 {selectedAgent.name} 对话
            </p>
          )}
        </div>

        {/* 导航菜单 */}
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${currentPage === 'chat' ? 'active' : ''}`}
            onClick={() => setCurrentPage('chat')}
          >
            <ChatIcon />
            <span>对话</span>
          </button>
          <button
            className={`nav-item ${currentPage === 'agents' ? 'active' : ''}`}
            onClick={() => setCurrentPage('agents')}
          >
            <AgentIcon />
            <span>Agent 配置</span>
          </button>
          <button
            className={`nav-item ${currentPage === 'providers' ? 'active' : ''}`}
            onClick={() => setCurrentPage('providers')}
          >
            <SettingsIcon />
            <span>模型设置</span>
          </button>
          <button
            className={`nav-item ${currentPage === 'knowledge' ? 'active' : ''}`}
            onClick={() => setCurrentPage('knowledge')}
          >
            <DatabaseIcon />
            <span>知识库</span>
          </button>
        </nav>

        {/* 可折叠的历史会话 */}
        <ConversationSection />

        {/* 团队成员 */}
        <div className="team-section">
          <h4>团队成员 ({agents.length})</h4>
          <div className="team-list">
            {agents.map(agent => {
              const isManagerSelected = agent.avatar_type === 'manager' && selectedAgent === null
              const isWorkerSelected = selectedAgent?.id === agent.id
              const isActive = isManagerSelected || isWorkerSelected

              return (
                <div
                  key={agent.id}
                  className={`team-member ${isActive ? 'active' : ''} ${agent.avatar_type === 'manager' ? 'manager' : 'worker'}`}
                  onClick={() => handleSelectAgent(agent)}
                  style={{
                    cursor: 'pointer',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    transition: 'all 0.2s',
                    background: isActive ? 'var(--primary-light)' : 'transparent',
                    border: isActive ? '1px solid var(--primary-color)' : '1px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'var(--bg-main)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent'
                    }
                  }}
                >
                  <Avatar name={agent.name} avatarType={agent.avatar_type} size={32} />
                  <div className="member-info">
                    <span className="member-name">{agent.name}</span>
                    <span className="member-role">{agent.role}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="main-content">
        {/* 顶部标题栏 */}
        <header className="top-header">
          <button
            className="menu-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <MenuIcon />
          </button>
          <h2 className="page-title">
            {currentPage === 'chat' && '💬 对话'}
            {currentPage === 'agents' && '👥 Agent 配置'}
            {currentPage === 'providers' && '⚙️ 模型设置'}
            {currentPage === 'knowledge' && '📚 知识库'}
          </h2>
        </header>

        {/* 页面内容 */}
        <div className="content-area">
          {currentPage === 'chat' && (
            <div className="chat-container">
              {/* Worker 直接对话提示条 */}
              {selectedAgent && (
                <div className="worker-mode-banner">
                  <div className="worker-mode-info">
                    <span className="worker-mode-icon">🎯</span>
                    <span>正在与 <strong>{selectedAgent.name}</strong> 直接对话</span>
                  </div>
                  <button
                    className="back-to-manager-btn"
                    onClick={async () => {
                      setSelectedAgent(null)
                      try {
                        const result = await api.getConversations()
                        const teamConv = result.conversations.find(c => !c.agent_id)
                        if (teamConv) {
                          await loadConversationMessages(teamConv.conversation_id)
                        } else {
                          setMessages([])
                          setActiveConversationId(null)
                        }
                      } catch (err) {
                        setMessages([])
                        setActiveConversationId(null)
                      }
                    }}
                  >
                    ← 返回团队模式
                  </button>
                </div>
              )}

              {/* 消息列表 */}
              <div className="messages-area">
                {messages.length === 0 ? (
                  <div className="welcome-screen">
                    <div className="welcome-icon">
                      <Avatar name={currentAgent?.name || 'AI'} avatarType={currentAgent?.avatar_type} size={80} />
                    </div>
                    <h2>你好！我是 {currentAgent?.name || 'AI 助手'}</h2>
                    <p>{selectedAgent ? `我是${currentAgent?.name}，${currentAgent?.role}。有什么可以帮你的吗？` : '有什么可以帮你的吗？'}</p>
                    {selectedAgent && (
                      <p style={{ fontSize: '14px', color: 'var(--primary-color)', marginTop: '8px' }}>
                        💡 正在与 Worker Agent 直接对话
                      </p>
                    )}
                    <div className="quick-actions">
                      <button onClick={() => setInputText('你好，请介绍一下你们团队')}>
                        👋 介绍团队
                      </button>
                      <button onClick={() => setInputText('帮我写一段Python代码')}>
                        🐍 写代码
                      </button>
                      <button onClick={() => setInputText('设计一个登录功能')}>
                        🎨 设计功能
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="messages-list">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}
                      >
                        {msg.role === 'user' ? (
                          <div className="message-user">
                            <div className="message-bubble user">
                              <p>{msg.content}</p>
                            </div>
                            <Avatar name="我" avatarType="manager" size={36} />
                          </div>
                        ) : (
                          <div className="message-assistant">
                            <Avatar name={msg.agentName || 'AI'} avatarType={msg.agentAvatarType} size={36} />
                            <div className="message-content">
                              <div className="message-header">
                                <span className="agent-name">{msg.agentName || 'AI'}</span>
                                <span className="agent-role">{msg.agentRole}</span>
                              </div>
                              <div className="message-bubble assistant">
                                <p>
                                  {msg.content}
                                  {msg.isStreaming && <span className="cursor">▋</span>}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* 输入区域 */}
              <div className="input-area">
                <div className="input-box">
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={isProcessing ? `${currentAgent?.name || 'AI'} 思考中...` : selectedAgent ? `与 ${currentAgent?.name} 对话，按 Enter 发送...` : '输入消息，按 Enter 发送...'}
                    disabled={isProcessing}
                    rows={1}
                  />
                  <button
                    className="send-btn"
                    onClick={handleSend}
                    disabled={!inputText.trim() || isProcessing}
                  >
                    <SendIcon />
                  </button>
                </div>
                <p className="input-hint">
                  {isProcessing ? '正在生成回复...' : 'Enter 发送，Shift+Enter 换行'}
                </p>
              </div>
            </div>
          )}

          {currentPage === 'agents' && <AgentConfigPage />}
          {currentPage === 'providers' && <ProviderConfigPage />}
          {currentPage === 'knowledge' && <KnowledgeBasePage />}
        </div>
      </main>
    </div>
  )
}

export default App
