import { useState, useEffect } from 'react'
import type { AgentConfig, Provider, KnowledgeBase } from '../types'
import { api } from '../api'

interface AgentFormData {
  name: string
  role: string
  personality: string
  provider_id: string
  kb_id: string
  specialty: string
  expertise: string
}

interface ManagerFormData {
  name: string
  role: string
  personality: string
  provider_id: string
  kb_id: string
  is_active: boolean
}

const initialAgentFormData: AgentFormData = {
  name: '',
  role: '',
  personality: '',
  provider_id: '',
  kb_id: '',
  specialty: '',
  expertise: '',
}

const initialManagerFormData: ManagerFormData = {
  name: '任务管理器',
  role: '项目协调经理',
  personality: '专业、有条理、善于规划和协调，能够准确分析需求并合理分配任务',
  provider_id: '',
  kb_id: '',
  is_active: false,
}

// 头像颜色
const avatarColors: Record<string, string> = {
  'manager': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'aiden': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'wrench': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'default': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
}

const Avatar = ({ name, type = 'default', size = 48 }: { name: string; type?: string; size?: number }) => {
  const bg = avatarColors[type] || avatarColors.default
  const initial = name.charAt(0).toUpperCase()

  return (
    <div
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

export const AgentConfigPage = () => {
  const [agents, setAgents] = useState<AgentConfig[]>([])
  const [manager, setManager] = useState<AgentConfig | null>(null)
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [showAgentForm, setShowAgentForm] = useState(false)
  const [showManagerForm, setShowManagerForm] = useState(false)
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null)
  const [agentFormData, setAgentFormData] = useState<AgentFormData>(initialAgentFormData)
  const [managerFormData, setManagerFormData] = useState<ManagerFormData>(initialManagerFormData)
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [saving, setSaving] = useState(false)
  const [reinitializing, setReinitializing] = useState(false)
  const [testingManager, setTestingManager] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [agentsRes, providersRes, kbsRes] = await Promise.all([
        api.getAgentConfigs(true),
        api.getProviders(),
        api.getKnowledgeBases()
      ])
      setKnowledgeBases(kbsRes)

      const managerAgent = agentsRes.find((a: AgentConfig) => a.id === 'manager_default')
      const workerAgents = agentsRes.filter((a: AgentConfig) => a.id !== 'manager_default')

      if (managerAgent) {
        setManager(managerAgent)
        setManagerFormData({
          name: managerAgent.name,
          role: managerAgent.role,
          personality: managerAgent.personality,
          provider_id: managerAgent.provider_id || '',
          kb_id: managerAgent.kb_id || '',
          is_active: managerAgent.is_active,
        })
      }
      setAgents(workerAgents)
      setProviders(providersRes)
    } catch (error) {
      console.error('Failed to load data:', error)
      alert('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAddAgentClick = () => {
    if (providers.length === 0) {
      alert('请先配置 Provider（模型），再创建 Agent')
      return
    }
    setEditingAgent(null)
    setAgentFormData({
      ...initialAgentFormData,
      provider_id: providers[0]?.id || '',
    })
    setShowAgentForm(true)
  }

  const handleEditAgentClick = (agent: AgentConfig) => {
    setEditingAgent(agent)
    setAgentFormData({
      name: agent.name,
      role: agent.role,
      personality: agent.personality,
      provider_id: agent.provider_id,
      kb_id: agent.kb_id || '',
      specialty: agent.specialty || '',
      expertise: agent.expertise || '',
    })
    setShowAgentForm(true)
  }

  const handleEditManagerClick = () => {
    if (manager) {
      setManagerFormData({
        name: manager.name,
        role: manager.role,
        personality: manager.personality,
        provider_id: manager.provider_id || '',
        kb_id: manager.kb_id || '',
        is_active: manager.is_active,
      })
    }
    setShowManagerForm(true)
  }

  const handleCloseAgentForm = () => {
    setShowAgentForm(false)
    setEditingAgent(null)
    setAgentFormData(initialAgentFormData)
  }

  const handleCloseManagerForm = () => {
    setShowManagerForm(false)
  }

  const handleSaveAgent = async () => {
    if (!agentFormData.name || !agentFormData.role || !agentFormData.personality || !agentFormData.provider_id) {
      alert('请填写所有必填字段')
      return
    }

    setSaving(true)
    try {
      const saveData = {
        name: agentFormData.name,
        role: agentFormData.role,
        personality: agentFormData.personality,
        provider_id: agentFormData.provider_id,
        kb_id: agentFormData.kb_id || undefined,
        specialty: agentFormData.specialty,
        expertise: agentFormData.expertise,
      }

      if (editingAgent) {
        await api.updateAgentConfig(editingAgent.id, saveData)
      } else {
        await api.createAgentConfig(saveData)
      }

      await loadData()
      await api.reinitializeSystem()
      window.dispatchEvent(new CustomEvent('agentUpdated'))
      handleCloseAgentForm()
    } catch (error: any) {
      console.error('Failed to save agent:', error)
      alert(`保存失败: ${error.response?.data?.detail || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveManager = async () => {
    if (!managerFormData.name || !managerFormData.role || !managerFormData.personality || !managerFormData.provider_id) {
      alert('请填写所有必填字段')
      return
    }

    setSaving(true)
    try {
      await api.updateManagerConfig({
        name: managerFormData.name,
        role: managerFormData.role,
        personality: managerFormData.personality,
        provider_id: managerFormData.provider_id,
        kb_id: managerFormData.kb_id || undefined,
        is_active: managerFormData.is_active,
      })

      await loadData()
      await api.reinitializeSystem()
      window.dispatchEvent(new CustomEvent('agentUpdated'))
      handleCloseManagerForm()
    } catch (error: any) {
      console.error('Failed to save manager:', error)
      alert(`保存失败: ${error.response?.data?.detail || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleTestManager = async () => {
    if (!managerFormData.provider_id) {
      alert('请先选择 Provider')
      return
    }

    setTestingManager(true)
    try {
      await api.updateManagerConfig({ provider_id: managerFormData.provider_id })
      const result = await api.testManagerConnection()
      alert(result.message)
    } catch (error: any) {
      alert('测试连接失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      setTestingManager(false)
    }
  }

  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm('确定要删除这个 Agent 吗？')) return

    try {
      await api.deleteAgentConfig(agentId)
      await loadData()
      await api.reinitializeSystem()
      window.dispatchEvent(new CustomEvent('agentUpdated'))
    } catch (error) {
      console.error('Failed to delete agent:', error)
      alert('删除失败')
    }
  }

  const handleReinitialize = async () => {
    if (!confirm('重新初始化系统会重新加载所有 Agent 配置，确定继续吗？')) return

    setReinitializing(true)
    try {
      const result = await api.reinitializeSystem()
      alert(`系统已重新初始化，共加载 ${result.agent_count} 个 Agent`)
    } catch (error) {
      console.error('Failed to reinitialize:', error)
      alert('重新初始化失败')
    } finally {
      setReinitializing(false)
    }
  }

  const getProviderName = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId)
    return provider ? `${provider.name}` : providerId
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <div style={{ textAlign: 'center', color: '#64748b' }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>⏳</div>
          <div>加载中...</div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto', height: '100%', overflowY: 'auto' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '4px' }}>Agent 配置</h2>
          <p style={{ color: '#64748b', fontSize: '14px' }}>配置 AI 助手角色和能力</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleReinitialize}
            disabled={reinitializing}
            style={{
              padding: '10px 16px',
              background: '#f1f5f9',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '14px',
              color: '#64748b',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            🔄 {reinitializing ? '初始化中...' : '重新初始化'}
          </button>
          <button
            onClick={handleAddAgentClick}
            style={{
              padding: '10px 16px',
              background: '#4f46e5',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            ➕ 添加 Agent
          </button>
        </div>
      </div>

      {/* Manager 区域 */}
      <div style={{ marginBottom: '32px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          👔 Manager Agent
        </h3>

        {manager && (
          <div
            style={{
              background: 'white',
              borderRadius: '12px',
              border: `1px solid ${manager.is_active ? '#4f46e5' : '#e2e8f0'}`,
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}
          >
            <Avatar name={manager.name} type="manager" size={56} />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{ fontSize: '18px', fontWeight: 600 }}>{manager.name}</span>
                {manager.is_active ? (
                  <span style={{ padding: '2px 8px', background: '#dcfce7', color: '#16a34a', borderRadius: '4px', fontSize: '12px', fontWeight: 500 }}>
                    已启用
                  </span>
                ) : (
                  <span style={{ padding: '2px 8px', background: '#f1f5f9', color: '#64748b', borderRadius: '4px', fontSize: '12px' }}>
                    已停用
                  </span>
                )}
              </div>
              <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '4px' }}>{manager.role}</div>
              <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                使用: {getProviderName(manager.provider_id || '')}
              </div>
            </div>
            <button
              onClick={handleEditManagerClick}
              style={{
                padding: '8px 16px',
                background: '#f1f5f9',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                fontSize: '14px',
                color: '#64748b',
                cursor: 'pointer',
              }}
            >
              配置
            </button>
          </div>
        )}
      </div>

      {/* Worker Agents 区域 */}
      <div>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          🛠️ Worker Agents ({agents.length})
        </h3>

        {agents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', background: '#f8fafc', borderRadius: '12px' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🤖</div>
            <div style={{ fontSize: '16px', color: '#64748b', marginBottom: '8px' }}>还没有 Worker Agent</div>
            <div style={{ fontSize: '14px', color: '#94a3b8' }}>添加 Worker 来处理特定任务</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {agents.map(agent => (
              <div
                key={agent.id}
                style={{
                  background: 'white',
                  borderRadius: '12px',
                  border: '1px solid #e2e8f0',
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                }}
              >
                <Avatar name={agent.name} type={agent.avatar_type} size={48} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                    <span style={{ fontSize: '16px', fontWeight: 600 }}>{agent.name}</span>
                    {agent.is_active && (
                      <span style={{ padding: '2px 8px', background: '#dcfce7', color: '#16a34a', borderRadius: '4px', fontSize: '12px', fontWeight: 500 }}>
                        已启用
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '14px', color: '#64748b' }}>{agent.role}</div>
                  <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '2px' }}>
                    使用: {getProviderName(agent.provider_id)}
                    {agent.kb_id && (
                      <span style={{ marginLeft: '8px', color: '#4f46e5' }}>
                        📚 {knowledgeBases.find(kb => kb.kb_id === agent.kb_id)?.name || '知识库'}
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handleEditAgentClick(agent)}
                    style={{
                      padding: '8px 16px',
                      background: '#f1f5f9',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      fontSize: '14px',
                      color: '#64748b',
                      cursor: 'pointer',
                    }}
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDeleteAgent(agent.id)}
                    style={{
                      padding: '8px 16px',
                      background: '#fef2f2',
                      border: '1px solid #fecaca',
                      borderRadius: '6px',
                      fontSize: '14px',
                      color: '#dc2626',
                      cursor: 'pointer',
                    }}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Agent Form Modal */}
      {showAgentForm && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px' }}>
          <div style={{ background: 'white', borderRadius: '16px', width: '100%', maxWidth: '560px', maxHeight: '95vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600 }}>{editingAgent ? '编辑 Worker' : '添加 Worker'}</h3>
              <button onClick={handleCloseAgentForm} style={{ background: 'none', border: 'none', fontSize: '24px', color: '#94a3b8', cursor: 'pointer' }}>×</button>
            </div>

            <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
              {/* 基本信息 */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px' }}>基本信息</h4>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>名称 *</label>
                  <input
                    type="text"
                    value={agentFormData.name}
                    onChange={e => setAgentFormData({ ...agentFormData, name: e.target.value })}
                    placeholder="例如：狗哥"
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  />
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>角色 *</label>
                  <input
                    type="text"
                    value={agentFormData.role}
                    onChange={e => setAgentFormData({ ...agentFormData, role: e.target.value })}
                    placeholder="例如：技术专家"
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>性格 *</label>
                  <textarea
                    value={agentFormData.personality}
                    onChange={e => setAgentFormData({ ...agentFormData, personality: e.target.value })}
                    placeholder="描述这个 Agent 的性格特点..."
                    rows={3}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', resize: 'vertical' }}
                  />
                </div>
              </div>

              {/* 专长 */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px' }}>专长配置（可选）</h4>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>专业领域</label>
                  <input
                    type="text"
                    value={agentFormData.specialty}
                    onChange={e => setAgentFormData({ ...agentFormData, specialty: e.target.value })}
                    placeholder="例如：数据分析"
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>专长描述</label>
                  <textarea
                    value={agentFormData.expertise}
                    onChange={e => setAgentFormData({ ...agentFormData, expertise: e.target.value })}
                    placeholder="详细描述专长..."
                    rows={2}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', resize: 'vertical' }}
                  />
                </div>
              </div>

              {/* 模型 */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px' }}>模型配置</h4>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>Provider *</label>
                  <select
                    value={agentFormData.provider_id}
                    onChange={e => setAgentFormData({ ...agentFormData, provider_id: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', background: 'white' }}
                  >
                    {providers.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} - {provider.model_name || provider.model_id}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 知识库 */}
              <div style={{ padding: '16px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#0284c7', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  📚 知识库配置 (RAG)
                </h4>

                <div>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>关联知识库</label>
                  <select
                    value={agentFormData.kb_id}
                    onChange={e => setAgentFormData({ ...agentFormData, kb_id: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', background: 'white' }}
                  >
                    <option value="">不关联知识库</option>
                    {knowledgeBases.map(kb => (
                      <option key={kb.kb_id} value={kb.kb_id}>
                        {kb.name} ({kb.total_documents} 文档)
                      </option>
                    ))}
                  </select>
                  <p style={{ marginTop: '6px', fontSize: '12px', color: '#94a3b8' }}>
                    关联知识库后，Agent 可以从知识库中检索信息来回答问题
                  </p>
                </div>
              </div>
            </div>

            <div style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={handleCloseAgentForm}
                style={{ padding: '10px 20px', background: '#f1f5f9', border: 'none', borderRadius: '8px', fontSize: '14px', color: '#64748b', cursor: 'pointer' }}
              >
                取消
              </button>
              <button
                onClick={handleSaveAgent}
                disabled={saving}
                style={{ padding: '10px 20px', background: '#4f46e5', border: 'none', borderRadius: '8px', fontSize: '14px', color: 'white', fontWeight: 500, cursor: 'pointer' }}
              >
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manager Form Modal */}
      {showManagerForm && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px' }}>
          <div style={{ background: 'white', borderRadius: '16px', width: '100%', maxWidth: '560px', maxHeight: '95vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600 }}>配置 Manager</h3>
              <button onClick={handleCloseManagerForm} style={{ background: 'none', border: 'none', fontSize: '24px', color: '#94a3b8', cursor: 'pointer' }}>×</button>
            </div>

            <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
              {/* 启用开关 */}
              <div style={{ marginBottom: '20px', padding: '16px', background: '#f8fafc', borderRadius: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={managerFormData.is_active}
                    onChange={e => setManagerFormData({ ...managerFormData, is_active: e.target.checked })}
                    style={{ width: '18px', height: '18px' }}
                  />
                  <span style={{ fontSize: '15px', fontWeight: 500 }}>启用 Manager Agent</span>
                </label>
                <p style={{ marginTop: '6px', marginLeft: '30px', fontSize: '13px', color: '#64748b' }}>
                  启用后，Manager 将作为任务协调者，自动分派任务给 Workers
                </p>
              </div>

              {/* 基本信息 */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px' }}>基本信息</h4>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>名称 *</label>
                  <input
                    type="text"
                    value={managerFormData.name}
                    onChange={e => setManagerFormData({ ...managerFormData, name: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  />
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>角色 *</label>
                  <input
                    type="text"
                    value={managerFormData.role}
                    onChange={e => setManagerFormData({ ...managerFormData, role: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>性格 *</label>
                  <textarea
                    value={managerFormData.personality}
                    onChange={e => setManagerFormData({ ...managerFormData, personality: e.target.value })}
                    rows={3}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', resize: 'vertical' }}
                  />
                </div>
              </div>

              {/* 模型 */}
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '12px' }}>模型配置</h4>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>Provider *</label>
                  <select
                    value={managerFormData.provider_id}
                    onChange={e => setManagerFormData({ ...managerFormData, provider_id: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', background: 'white' }}
                  >
                    {providers.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} - {provider.model_name || provider.model_id}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={handleTestManager}
                  disabled={testingManager || !managerFormData.provider_id}
                  style={{ padding: '8px 16px', background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', color: '#64748b', cursor: 'pointer' }}
                >
                  {testingManager ? '测试中...' : '测试连接'}
                </button>
              </div>

              {/* 知识库配置 */}
              <div style={{ padding: '16px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#0284c7', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  📚 知识库配置 (RAG)
                </h4>

                <div>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>关联知识库</label>
                  <select
                    value={managerFormData.kb_id}
                    onChange={e => setManagerFormData({ ...managerFormData, kb_id: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', background: 'white' }}
                  >
                    <option value="">不关联知识库</option>
                    {knowledgeBases.map(kb => (
                      <option key={kb.kb_id} value={kb.kb_id}>
                        {kb.name} ({kb.total_documents} 文档)
                      </option>
                    ))}
                  </select>
                  <p style={{ marginTop: '6px', fontSize: '12px', color: '#64748b' }}>
                    关联知识库后，Manager 可以直接从知识库中检索信息来回答问题
                  </p>
                </div>

                {managerFormData.kb_id && (
                  <div style={{ marginTop: '12px', padding: '10px', background: '#dcfce7', borderRadius: '6px', fontSize: '13px', color: '#16a34a' }}>
                    ✅ 已关联知识库: {knowledgeBases.find(kb => kb.kb_id === managerFormData.kb_id)?.name || managerFormData.kb_id}
                  </div>
                )}
              </div>
            </div>

            <div style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={handleCloseManagerForm}
                style={{ padding: '10px 20px', background: '#f1f5f9', border: 'none', borderRadius: '8px', fontSize: '14px', color: '#64748b', cursor: 'pointer' }}
              >
                取消
              </button>
              <button
                onClick={handleSaveManager}
                disabled={saving}
                style={{ padding: '10px 20px', background: '#4f46e5', border: 'none', borderRadius: '8px', fontSize: '14px', color: 'white', fontWeight: 500, cursor: 'pointer' }}
              >
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
