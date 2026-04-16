import { useState, useEffect } from 'react'
import type { ManagerConfig, Provider, KnowledgeBase } from '../types'
import { api } from '../api'

export const ManagerConfigPage = () => {
  const [manager, setManager] = useState<ManagerConfig | null>(null)
  const [providers, setProviders] = useState<Provider[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // 表单数据
  const [formData, setFormData] = useState({
    name: '任务管理器',
    role: '项目协调经理',
    personality: '专业、有条理、善于规划和协调，能够准确分析需求并合理分配任务',
    provider_id: '',
    kb_id: '',
    is_active: false,
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      // 加载 Manager 配置
      const managerRes = await api.getManagerConfig()
      console.log('Loaded manager config:', managerRes)
      setManager(managerRes)
      setFormData({
        name: managerRes.name,
        role: managerRes.role,
        personality: managerRes.personality,
        provider_id: managerRes.provider_id || '',
        kb_id: managerRes.kb_id || '',
        is_active: managerRes.is_active,
      })
    } catch (error) {
      console.error('Failed to load manager config:', error)
      setMessage({ type: 'error', text: '加载 Manager 配置失败' })
    }

    // 加载 Providers
    try {
      const providersRes = await api.getProviders()
      setProviders(providersRes)
    } catch (error) {
      console.error('Failed to load providers:', error)
    }

    // 加载知识库
    try {
      const kbRes = await api.getKnowledgeBases()
      setKnowledgeBases(kbRes)
    } catch (error) {
      console.error('Failed to load knowledge bases:', error)
    }

    setLoading(false)
  }

  const handleSave = async () => {
    if (!formData.provider_id) {
      setMessage({ type: 'error', text: '请选择 Provider' })
      return
    }

    setSaving(true)
    setMessage(null)

    try {
      const result = await api.updateManagerConfig({
        name: formData.name,
        role: formData.role,
        personality: formData.personality,
        provider_id: formData.provider_id,
        kb_id: formData.kb_id || undefined,
        is_active: formData.is_active,
      })

      setManager(result)
      setMessage({ type: 'success', text: '配置已保存' })

      // 重新初始化系统
      try {
        await api.reinitializeSystem()
        console.log('System reinitialized successfully')
      } catch (reinitError) {
        console.warn('System reinitialization failed:', reinitError)
      }
    } catch (error: any) {
      console.error('Failed to save manager config:', error)
      setMessage({ type: 'error', text: error.response?.data?.detail || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!formData.provider_id) {
      setMessage({ type: 'error', text: '请先选择 Provider' })
      return
    }

    setTesting(true)
    setMessage(null)

    try {
      const result = await api.testManagerConnection()
      setMessage({
        type: result.success ? 'success' : 'error',
        text: result.message,
      })
    } catch (error: any) {
      setMessage({ type: 'error', text: '测试连接失败' })
    } finally {
      setTesting(false)
    }
  }

  const getProviderName = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId)
    return provider ? `${provider.name} (${provider.model_name || provider.model_id})` : providerId
  }

  const getKBName = (kbId: string) => {
    const kb = knowledgeBases.find(k => k.kb_id === kbId)
    return kb ? kb.name : kbId
  }

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        加载中...
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '4px' }}>Manager Agent 配置</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Manager 是系统的任务协调者，负责分析需求并分派给 Worker Agents
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: '10px 20px',
            background: 'var(--primary-color)',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.7 : 1,
          }}
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>

      {/* 消息提示 */}
      {message && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            background: message.type === 'success' ? '#dcfce7' : '#fef2f2',
            border: `1px solid ${message.type === 'success' ? '#86efac' : '#fecaca'}`,
            color: message.type === 'success' ? '#16a34a' : '#dc2626',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{message.type === 'success' ? '✅' : '❌'} {message.text}</span>
          <button
            onClick={() => setMessage(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              fontSize: '18px',
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* 功能说明 */}
      <div
        style={{
          background: 'var(--primary-light)',
          border: '1px solid var(--primary-color)',
          borderRadius: '12px',
          padding: '16px 20px',
          marginBottom: '24px',
        }}
      >
        <h4 style={{ color: 'var(--primary-color)', marginBottom: '8px', fontSize: '14px' }}>💡 Manager 功能说明</h4>
        <ul style={{ fontSize: '13px', lineHeight: '1.8', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
          <li>Manager 是系统级默认 Agent，不可删除</li>
          <li>启用 Manager 后，系统会自动进入 Manager-Worker 协作模式</li>
          <li>Manager 会分析用户请求，拆解任务并分派给合适的 Worker</li>
          <li>Manager 可以直接使用知识库进行 RAG 检索</li>
          <li>如果没有配置 Worker，Manager 会直接处理所有请求</li>
        </ul>
      </div>

      {/* 配置卡片 */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '24px', border: '1px solid var(--border-color)' }}>
        {/* 启用开关 */}
        <div style={{ marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={e => setFormData({ ...formData, is_active: e.target.checked })}
              style={{ width: '20px', height: '20px' }}
            />
            <span style={{ fontSize: '16px', fontWeight: 600 }}>
              启用 Manager Agent
            </span>
          </label>
          <p style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            启用后，Manager 将作为任务协调者，自动分派任务给 Worker Agents
          </p>
        </div>

        {/* 基本信息 */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--primary-color)' }}>基本信息</h4>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
              Manager 名称 *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="例如：任务管理器"
              style={{
                width: '100%',
                padding: '10px 14px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                fontSize: '14px',
              }}
            />
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>
              角色 *
            </label>
            <input
              type="text"
              value={formData.role}
              onChange={e => setFormData({ ...formData, role: e.target.value })}
              placeholder="例如：项目协调经理"
              style={{
                width: '100%',
                padding: '10px 14px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                fontSize: '14px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>
              性格描述 *
            </label>
            <textarea
              value={formData.personality}
              onChange={e => setFormData({ ...formData, personality: e.target.value })}
              placeholder="描述 Manager 的性格特点..."
              rows={2}
              style={{
                width: '100%',
                padding: '10px 14px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                fontSize: '14px',
                resize: 'vertical',
              }}
            />
          </div>
        </div>

        {/* Provider 配置 */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--primary-color)' }}>模型配置</h4>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
              选择 Provider *
            </label>
            <select
              value={formData.provider_id}
              onChange={e => setFormData({ ...formData, provider_id: e.target.value })}
              style={{
                width: '100%',
                padding: '10px 14px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                fontSize: '14px',
              }}
            >
              <option value="">请选择 Provider</option>
              {providers.map(provider => (
                <option key={provider.id} value={provider.id}>
                  {provider.name} - {provider.model_name || provider.model_id}
                </option>
              ))}
            </select>
          </div>

          {formData.provider_id && (
            <div
              style={{
                marginBottom: '12px',
                padding: '10px',
                background: 'var(--bg-main)',
                borderRadius: '8px',
                fontSize: '13px',
              }}
            >
              {(() => {
                const p = providers.find(pr => pr.id === formData.provider_id)
                return p ? (
                  <>
                    <div><strong>类型:</strong> {p.provider_type}</div>
                    <div><strong>模型:</strong> {p.model_name || p.model_id}</div>
                  </>
                ) : null
              })()}
            </div>
          )}

          <div>
            <button
              onClick={handleTest}
              disabled={testing || !formData.provider_id}
              style={{
                padding: '10px 20px',
                background: 'transparent',
                color: testing || !formData.provider_id ? 'var(--text-muted)' : 'var(--text-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                fontSize: '14px',
                cursor: testing || !formData.provider_id ? 'not-allowed' : 'pointer',
              }}
            >
              {testing ? '测试中...' : '测试连接'}
            </button>
          </div>
        </div>

        {/* 知识库配置 */}
        <div>
          <h4 style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--primary-color)' }}>知识库配置 (RAG)</h4>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>
              关联知识库
            </label>
            <select
              value={formData.kb_id}
              onChange={e => setFormData({ ...formData, kb_id: e.target.value })}
              style={{
                width: '100%',
                padding: '10px 14px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                fontSize: '14px',
              }}
            >
              <option value="">不关联知识库</option>
              {knowledgeBases.map(kb => (
                <option key={kb.kb_id} value={kb.kb_id}>
                  {kb.name} ({kb.total_documents} 文档)
                </option>
              ))}
            </select>
            <p style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
              关联知识库后，Manager 可以直接从知识库中检索信息来回答问题
            </p>
          </div>

          {formData.kb_id && (
            <div
              style={{
                padding: '12px',
                background: '#dcfce7',
                borderRadius: '8px',
                fontSize: '13px',
                color: '#16a34a',
              }}
            >
              ✅ 已关联知识库: {getKBName(formData.kb_id)}
            </div>
          )}
        </div>
      </div>

      {/* 当前状态 */}
      <div
        style={{
          marginTop: '24px',
          padding: '16px 20px',
          background: formData.is_active ? '#dcfce7' : '#f1f5f9',
          border: `1px solid ${formData.is_active ? '#86efac' : 'var(--border-color)'}`,
          borderRadius: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>{formData.is_active ? '✅' : '⏸️'}</span>
          <div>
            <div style={{ fontWeight: 600, color: formData.is_active ? '#16a34a' : 'var(--text-primary)' }}>
              当前状态: {formData.is_active ? '已启用' : '已禁用'}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {formData.is_active
                ? `Manager 将作为任务协调者运行${formData.kb_id ? '，并支持知识库检索' : ''}`
                : '系统将使用传统 MsgHub 模式运行'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
