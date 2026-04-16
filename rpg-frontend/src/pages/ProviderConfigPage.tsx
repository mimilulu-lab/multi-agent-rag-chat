import { useState, useEffect } from 'react'
import type { Provider, ProviderType } from '../types'
import { api, ProviderTypeInfo, ProviderModel } from '../api'

interface ProviderFormData {
  name: string
  provider_type: ProviderType
  model_id: string
  model_name: string
  api_key: string
  base_url: string
}

const initialFormData: ProviderFormData = {
  name: '',
  provider_type: 'openai',
  model_id: '',
  model_name: '',
  api_key: '',
  base_url: '',
}

const defaultProviderTypes: ProviderTypeInfo[] = [
  { id: 'kimi', name: 'Kimi (Moonshot)', description: 'Moonshot AI API，OpenAI 兼容', required_fields: ['api_key', 'model_id'] },
  { id: 'openai', name: 'OpenAI', description: 'OpenAI 官方 API', required_fields: ['api_key', 'model_id'], optional_fields: ['base_url'] },
  { id: 'dashscope', name: '阿里云 DashScope', description: '阿里云大模型服务平台', required_fields: ['api_key', 'model_id'] },
  { id: 'anthropic', name: 'Anthropic 协议', description: '支持 Anthropic Claude API 协议的模型', required_fields: ['api_key', 'base_url', 'model_id'] },
  { id: 'custom', name: '自定义 OpenAI 兼容', description: '任何 OpenAI 兼容的 API 服务', required_fields: ['api_key', 'base_url', 'model_id'] },
]

const defaultModels: Record<string, ProviderModel[]> = {
  kimi: [
    { id: 'moonshot-v1-8k', name: 'Moonshot v1 8K', description: '8K 上下文' },
    { id: 'moonshot-v1-32k', name: 'Moonshot v1 32K', description: '32K 上下文' },
    { id: 'moonshot-v1-128k', name: 'Moonshot v1 128K', description: '128K 长文本' },
  ],
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o', description: '最强性能' },
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', description: '高性能' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: '经济选择' },
  ],
  dashscope: [
    { id: 'qwen-max', name: '通义千问 Max', description: '最强性能' },
    { id: 'qwen-plus', name: '通义千问 Plus', description: '均衡选择' },
    { id: 'qwen-turbo', name: '通义千问 Turbo', description: '快速经济' },
  ],
  anthropic: [
    { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', description: '最强性能' },
    { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', description: '均衡选择' },
    { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', description: '快速经济' },
  ],
  custom: [
    { id: 'custom', name: '自定义模型', description: '输入任意模型ID' },
  ],
}

// Provider 图标
const ProviderIcon = ({ type, size = 40 }: { type: string; size?: number }) => {
  const icons: Record<string, string> = {
    kimi: '🌙',
    openai: '🤖',
    dashscope: '☁️',
    anthropic: '🧠',
    custom: '⚙️',
  }

  const gradients: Record<string, string> = {
    kimi: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    openai: 'linear-gradient(135deg, #10a37f 0%, #0d8c6d 100%)',
    dashscope: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%)',
    anthropic: 'linear-gradient(135deg, #d4a574 0%, #c49a6b 100%)',
    custom: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '12px',
        background: gradients[type] || gradients.custom,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: size * 0.5,
        flexShrink: 0,
      }}
    >
      {icons[type] || '⚙️'}
    </div>
  )
}

export const ProviderConfigPage = () => {
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null)
  const [formData, setFormData] = useState<ProviderFormData>(initialFormData)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await api.getProviders()
      setProviders(res)
    } catch (error) {
      console.error('Failed to load providers:', error)
      alert('加载 Provider 列表失败')
    }
    setLoading(false)
  }

  const handleAddClick = () => {
    setEditingProvider(null)
    setFormData(initialFormData)
    setTestResult(null)
    setShowForm(true)
  }

  const handleEditClick = (provider: Provider) => {
    setEditingProvider(provider)
    setFormData({
      name: provider.name,
      provider_type: provider.provider_type,
      model_id: provider.model_id,
      model_name: provider.model_name,
      api_key: '',
      base_url: provider.base_url,
    })
    setTestResult(null)
    setShowForm(true)
  }

  const handleCloseForm = () => {
    setShowForm(false)
    setEditingProvider(null)
    setFormData(initialFormData)
    setTestResult(null)
  }

  const handleTest = async () => {
    if (!formData.api_key) {
      alert('请先填写 API Key')
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      let result
      if (editingProvider) {
        await api.updateProvider(editingProvider.id, {
          ...formData,
          api_key: formData.api_key || undefined,
        })
        result = await api.testProvider(editingProvider.id)
      } else {
        result = await api.testConnectionTemp({
          provider_type: formData.provider_type,
          api_key: formData.api_key,
          model_id: formData.model_id,
          base_url: formData.base_url || undefined,
        })
      }
      setTestResult(result)
    } catch (error) {
      setTestResult({ success: false, message: '测试失败' })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!formData.name || !formData.api_key || !formData.model_id) {
      alert('请填写所有必填字段')
      return
    }

    let baseUrl = formData.base_url
    if (formData.provider_type === 'dashscope') {
      baseUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    } else if (formData.provider_type === 'kimi') {
      baseUrl = 'https://api.moonshot.cn/v1'
    } else if ((formData.provider_type === 'anthropic' || formData.provider_type === 'custom') && !formData.base_url) {
      alert('Anthropic 协议和自定义提供商需要填写 Base URL')
      return
    }

    const saveData = {
      name: formData.name,
      provider_type: formData.provider_type,
      model_id: formData.model_id,
      model_name: formData.model_name || formData.model_id,
      api_key: formData.api_key,
      base_url: baseUrl,
    }

    setSaving(true)
    try {
      if (editingProvider) {
        await api.updateProvider(editingProvider.id, saveData)
      } else {
        await api.createProvider(saveData)
      }
      await loadData()
      handleCloseForm()
      alert('保存成功')
    } catch (error: any) {
      console.error('Failed to save provider:', error)
      const errorMsg = error.response?.data?.detail || error.message || '保存失败'
      alert(`保存失败: ${errorMsg}`)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (providerId: string) => {
    if (!confirm('确定要删除这个 Provider 吗？\n注意：正在使用此 Provider 的 Agent 将无法正常工作。')) return

    try {
      await api.deleteProvider(providerId)
      await loadData()
    } catch (error) {
      console.error('Failed to delete provider:', error)
      alert('删除失败')
    }
  }

  const currentType = defaultProviderTypes.find(t => t.id === formData.provider_type)
  const currentModels = defaultModels[formData.provider_type] || []

  if (loading) {
    return (
      <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto', textAlign: 'center', color: 'var(--text-secondary)' }}>
        加载中...
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '4px' }}>
            模型服务配置
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            配置 LLM API 服务，供 Agents 使用
          </p>
        </div>
        <button
          onClick={handleAddClick}
          style={{
            padding: '10px 20px',
            background: 'var(--primary-color)',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>+</span> 添加 Provider
        </button>
      </div>

      {/* Provider List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {providers.length === 0 ? (
          <div
            style={{
              background: 'white',
              borderRadius: '12px',
              padding: '48px 24px',
              textAlign: 'center',
              border: '1px dashed var(--border-color)',
            }}
          >
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔌</div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              还没有配置任何 Provider
            </p>
            <button
              onClick={handleAddClick}
              style={{
                padding: '10px 20px',
                background: 'var(--primary-color)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                cursor: 'pointer',
              }}
            >
              添加第一个 Provider
            </button>
          </div>
        ) : (
          providers.map(provider => (
            <div
              key={provider.id}
              style={{
                background: 'white',
                borderRadius: '12px',
                padding: '20px',
                border: `1px solid ${provider.is_active ? 'var(--primary-color)' : 'var(--border-color)'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                transition: 'all 0.2s ease',
              }}
            >
              <ProviderIcon type={provider.provider_type} size={48} />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <h4 style={{ fontSize: '16px', fontWeight: '600' }}>{provider.name}</h4>
                  {provider.is_active && (
                    <span
                      style={{
                        padding: '2px 8px',
                        background: '#dcfce7',
                        color: '#16a34a',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: '500',
                      }}
                    >
                      活跃
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                    {defaultProviderTypes.find(t => t.id === provider.provider_type)?.name || provider.provider_type}
                  </span>
                  <span style={{ color: 'var(--border-color)' }}>|</span>
                  <span style={{ fontSize: '14px', color: 'var(--text-primary)' }}>
                    {provider.model_name || provider.model_id}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleEditClick(provider)}
                  style={{
                    padding: '8px 16px',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f1f5f9'
                    e.currentTarget.style.color = 'var(--text-primary)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent'
                    e.currentTarget.style.color = 'var(--text-secondary)'
                  }}
                >
                  编辑
                </button>
                <button
                  onClick={() => handleDelete(provider.id)}
                  style={{
                    padding: '8px 16px',
                    background: 'transparent',
                    color: '#ef4444',
                    border: '1px solid #fecaca',
                    borderRadius: '8px',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#fef2f2'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent'
                  }}
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Form Modal */}
      {showForm && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '24px',
          }}
          onClick={handleCloseForm}
        >
          <div
            style={{
              background: 'white',
              borderRadius: '16px',
              width: '100%',
              maxWidth: '560px',
              maxHeight: '90vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '600' }}>
                {editingProvider ? '编辑 Provider' : '添加 Provider'}
              </h3>
              <button
                onClick={handleCloseForm}
                style={{
                  width: '32px',
                  height: '32px',
                  border: 'none',
                  background: 'transparent',
                  fontSize: '24px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#f1f5f9'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                ×
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px' }}>
              {/* Provider Type Selection */}
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                  提供商类型 *
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                  {defaultProviderTypes.map(type => (
                    <button
                      key={type.id}
                      onClick={() => setFormData({ ...formData, provider_type: type.id as ProviderType })}
                      style={{
                        padding: '12px',
                        border: `2px solid ${formData.provider_type === type.id ? 'var(--primary-color)' : 'var(--border-color)'}`,
                        background: formData.provider_type === type.id ? 'var(--primary-light)' : 'white',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '2px' }}>
                        {type.name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {type.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Name */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                  显示名称 *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：Kimi 主账号"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Model Selection */}
              {currentModels.length > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                    推荐模型
                  </label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {currentModels.map(model => (
                      <button
                        key={model.id}
                        onClick={() => setFormData({ ...formData, model_id: model.id, model_name: model.name })}
                        style={{
                          padding: '6px 12px',
                          background: formData.model_id === model.id ? 'var(--primary-color)' : 'var(--bg-main)',
                          color: formData.model_id === model.id ? 'white' : 'var(--text-primary)',
                          border: 'none',
                          borderRadius: '6px',
                          fontSize: '13px',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                        }}
                      >
                        {model.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Model ID */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                  模型 ID *
                </label>
                <input
                  type="text"
                  value={formData.model_id}
                  onChange={e => setFormData({ ...formData, model_id: e.target.value })}
                  placeholder="例如：moonshot-v1-8k"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Base URL */}
              {(formData.provider_type === 'anthropic' || formData.provider_type === 'custom') && (
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                    Base URL *
                  </label>
                  <input
                    type="text"
                    value={formData.base_url}
                    onChange={e => setFormData({ ...formData, base_url: e.target.value })}
                    placeholder="https://api.example.com/v1"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      fontSize: '14px',
                      outline: 'none',
                    }}
                  />
                </div>
              )}

              {/* API Key */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                  API Key *
                </label>
                <input
                  type="password"
                  value={formData.api_key}
                  onChange={e => setFormData({ ...formData, api_key: e.target.value })}
                  placeholder={editingProvider ? '留空表示不修改' : '输入 API Key'}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Test Result */}
              {testResult && (
                <div
                  style={{
                    padding: '12px 16px',
                    background: testResult.success ? '#dcfce7' : '#fef2f2',
                    color: testResult.success ? '#16a34a' : '#dc2626',
                    borderRadius: '8px',
                    fontSize: '14px',
                    marginBottom: '16px',
                  }}
                >
                  {testResult.success ? '✅' : '❌'} {testResult.message}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: '16px 24px',
                borderTop: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <button
                onClick={handleTest}
                disabled={testing || !formData.api_key}
                style={{
                  padding: '10px 20px',
                  background: 'transparent',
                  color: testing || !formData.api_key ? 'var(--text-muted)' : 'var(--text-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  fontSize: '14px',
                  cursor: testing || !formData.api_key ? 'not-allowed' : 'pointer',
                }}
              >
                {testing ? '测试中...' : '测试连接'}
              </button>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={handleCloseForm}
                  style={{
                    padding: '10px 20px',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                    cursor: 'pointer',
                  }}
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  style={{
                    padding: '10px 24px',
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
                  {saving ? '保存中...' : '保存'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
