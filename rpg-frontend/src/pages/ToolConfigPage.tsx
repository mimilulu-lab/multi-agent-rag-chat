import { useEffect, useState } from 'react'
import { api } from '../api'
import type { ToolConfig } from '../types'

// 工具图标组件
const ToolIcon = ({ name }: { name: string }) => {
  if (name.includes('file')) {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
    )
  }
  if (name.includes('browser')) {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
    )
  }
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
    </svg>
  )
}

// 开关组件
const Toggle = ({ checked, onChange, disabled = false }: { checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean }) => {
  return (
    <label className={`toggle ${disabled ? 'disabled' : ''}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className="toggle-slider" />
    </label>
  )
}

export function ToolConfigPage() {
  const [tools, setTools] = useState<ToolConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // 初始工具状态（用于比较是否有变更）
  const [initialTools, setInitialTools] = useState<Record<string, boolean>>({})

  useEffect(() => {
    loadTools()
  }, [])

  const loadTools = async () => {
    try {
      setLoading(true)
      const toolList = await api.getTools()
      setTools(toolList)

      // 保存初始状态
      const initial: Record<string, boolean> = {}
      toolList.forEach(tool => {
        initial[tool.name] = tool.enabled
      })
      setInitialTools(initial)
      setHasChanges(false)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '加载工具列表失败' })
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = (toolName: string, enabled: boolean) => {
    setTools(prev =>
      prev.map(tool =>
        tool.name === toolName ? { ...tool, enabled } : tool
      )
    )

    // 检查是否有变更
    const currentEnabled = initialTools[toolName]
    if (currentEnabled !== undefined && currentEnabled !== enabled) {
      setHasChanges(true)
    } else {
      // 检查是否还有其他变更
      const updatedTools = tools.map(t =>
        t.name === toolName ? { ...t, enabled } : t
      )
      const hasOtherChanges = updatedTools.some(t =>
        initialTools[t.name] !== t.enabled
      )
      setHasChanges(hasOtherChanges)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setMessage(null)

      // 构建批量更新请求
      const toolsUpdate: Record<string, boolean> = {}
      tools.forEach(tool => {
        toolsUpdate[tool.name] = tool.enabled
      })

      const response = await api.updateToolsBatch(toolsUpdate)

      if (response.success) {
        setMessage({ type: 'success', text: response.message })

        // 更新初始状态
        const newInitial: Record<string, boolean> = {}
        tools.forEach(tool => {
          newInitial[tool.name] = tool.enabled
        })
        setInitialTools(newInitial)
        setHasChanges(false)
      } else {
        setMessage({ type: 'error', text: response.message })
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    // 恢复到初始状态
    setTools(prev =>
      prev.map(tool => ({
        ...tool,
        enabled: initialTools[tool.name] ?? tool.enabled
      }))
    )
    setHasChanges(false)
    setMessage(null)
  }

  // 按类别分组工具
  const fileTools = tools.filter(t => t.name.includes('file'))
  const browserTools = tools.filter(t => t.name.includes('browser'))
  const otherTools = tools.filter(t => !t.name.includes('file') && !t.name.includes('browser'))

  const renderToolGroup = (title: string, toolList: ToolConfig[]) => {
    if (toolList.length === 0) return null

    return (
      <div className="tool-group">
        <h3 className="tool-group-title">{title}</h3>
        <div className="tool-list">
          {toolList.map(tool => (
            <div key={tool.name} className={`tool-item ${tool.enabled ? 'enabled' : 'disabled'}`}>
              <div className="tool-icon">
                <ToolIcon name={tool.name} />
              </div>
              <div className="tool-info">
                <div className="tool-name">{tool.name}</div>
                <div className="tool-description">{tool.description || '暂无描述'}</div>
              </div>
              <div className="tool-status">
                <span className={`status-badge ${tool.enabled ? 'enabled' : 'disabled'}`}>
                  {tool.enabled ? '已启用' : '已禁用'}
                </span>
                <Toggle
                  checked={tool.enabled}
                  onChange={(checked) => handleToggle(tool.name, checked)}
                  disabled={saving}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="tool-config-page">
      <div className="page-header">
        <div className="page-title">
          <div className="page-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
          </div>
          <div className="title-content">
            <h1>工具管理</h1>
            <p className="subtitle">管理所有 Agent 可用的工具，启用或禁用特定功能</p>
          </div>
        </div>
        <div className="page-actions">
          {hasChanges && (
            <span className="unsaved-indicator">有未保存的更改</span>
          )}
          <button
            className="btn btn-secondary"
            onClick={handleReset}
            disabled={!hasChanges || saving}
          >
            重置
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? '保存中...' : '保存更改'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`alert alert-${message.type}`}>
          <span className="alert-icon">
            {message.type === 'success' ? '✅' : '❌'}
          </span>
          {message.text}
          <button className="alert-close" onClick={() => setMessage(null)}>×</button>
        </div>
      )}

      <div className="tool-config-content">
        {loading ? (
          <div className="loading-state">
            <div className="spinner" />
            <span>加载工具列表...</span>
          </div>
        ) : (
          <>
            {renderToolGroup('📁 文件操作工具', fileTools)}
            {renderToolGroup('🌐 浏览器自动化工具', browserTools)}
            {renderToolGroup('🔧 其他工具', otherTools)}

            {tools.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">🔧</div>
                <h3>暂无可用工具</h3>
                <p>系统尚未注册任何工具</p>
              </div>
            )}
          </>
        )}
      </div>

      <div className="tool-config-footer">
        <div className="info-box">
          <h4>💡 工具使用说明</h4>
          <ul>
            <li>所有 Agent 共享同一套工具配置</li>
            <li>禁用工具后，所有 Agent 将无法使用该功能</li>
            <li>更改保存后立即生效，无需重启服务</li>
            <li>建议根据实际需求和安全考虑启用/禁用工具</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
