import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import type { KnowledgeBase, SearchResult, KBDocument } from '../types'

// 图标组件
const DatabaseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <ellipse cx="12" cy="5" rx="9" ry="3"/>
    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
  </svg>
)

const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.35-4.35"/>
  </svg>
)

const UploadIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/>
    <line x1="12" x2="12" y1="3" y2="15"/>
  </svg>
)

const PlusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19"/>
    <line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)

const TrashIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
)

const FileIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
    <polyline points="14 2 14 8 20 8"/>
  </svg>
)

// 知识库卡片颜色
const kbColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
]

export const KnowledgeBasePage = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [documents, setDocuments] = useState<KBDocument[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 创建表单状态
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    embedding_provider: 'fake' as 'kimi' | 'openai' | 'fake',
    chunk_size: 500,
    chunk_overlap: 50,
  })

  // 加载知识库列表
  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  // 加载选中知识库的文档列表
  useEffect(() => {
    if (selectedKB) {
      loadDocuments(selectedKB.kb_id)
    } else {
      setDocuments([])
    }
  }, [selectedKB?.kb_id])

  const loadDocuments = async (kbId: string) => {
    setLoadingDocs(true)
    try {
      const result = await api.getDocuments(kbId)
      if (result.success) {
        setDocuments(result.documents)
      }
    } catch (error) {
      console.error('Failed to load documents:', error)
    }
    setLoadingDocs(false)
  }

  const loadKnowledgeBases = async () => {
    setLoading(true)
    try {
      const kbs = await api.getKnowledgeBases()
      setKnowledgeBases(kbs)
    } catch (error) {
      console.error('Failed to load knowledge bases:', error)
      alert('加载知识库列表失败')
    }
    setLoading(false)
  }

  // 创建知识库
  const handleCreate = async () => {
    if (!createForm.name.trim()) {
      alert('请输入知识库名称')
      return
    }

    try {
      await api.createKnowledgeBase(createForm)
      setShowCreateModal(false)
      setCreateForm({
        name: '',
        description: '',
        embedding_provider: 'fake',
        chunk_size: 500,
        chunk_overlap: 50,
      })
      await loadKnowledgeBases()
    } catch (error) {
      console.error('Failed to create knowledge base:', error)
      alert('创建知识库失败')
    }
  }

  // 删除知识库
  const handleDelete = async (kbId: string) => {
    if (!confirm('确定要删除这个知识库吗？此操作不可恢复。')) return

    try {
      await api.deleteKnowledgeBase(kbId)
      if (selectedKB?.kb_id === kbId) {
        setSelectedKB(null)
      }
      await loadKnowledgeBases()
    } catch (error) {
      console.error('Failed to delete knowledge base:', error)
      alert('删除知识库失败')
    }
  }

  // 搜索
  const handleSearch = async () => {
    if (!selectedKB || !searchQuery.trim()) return

    setSearching(true)
    try {
      const result = await api.searchKnowledgeBase(selectedKB.kb_id, searchQuery, 5)
      setSearchResults(result.results)
    } catch (error) {
      console.error('Search failed:', error)
      alert('搜索失败')
    }
    setSearching(false)
  }

  // 文件上传
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedKB) return

    setUploading(true)
    try {
      const result = await api.uploadDocument(selectedKB.kb_id, file)
      if (result.success) {
        alert(`上传成功！处理了 ${result.documents} 个文档，${result.chunks} 个文本块`)
        await loadKnowledgeBases()
        // 刷新选中的知识库
        const updated = await api.getKnowledgeBases()
        const kb = updated.find(k => k.kb_id === selectedKB.kb_id)
        if (kb) {
          setSelectedKB(kb)
          await loadDocuments(kb.kb_id)
        }
      }
    } catch (error) {
      console.error('Upload failed:', error)
      alert('上传失败')
    }
    setUploading(false)

    // 清空文件输入
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        加载中...
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '4px' }}>知识库管理</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            管理 RAG 知识库，上传文档并进行检索
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
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
            gap: '8px',
          }}
        >
          <PlusIcon /> 创建知识库
        </button>
      </div>

      {/* 两栏布局 */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
        {/* 左侧：知识库列表 */}
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
            我的知识库 ({knowledgeBases.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {knowledgeBases.map((kb, index) => (
              <div
                key={kb.kb_id}
                onClick={() => setSelectedKB(kb)}
                style={{
                  padding: '16px',
                  background: selectedKB?.kb_id === kb.kb_id ? 'var(--primary-light)' : 'white',
                  border: `2px solid ${selectedKB?.kb_id === kb.kb_id ? 'var(--primary-color)' : 'var(--border-color)'}`,
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '10px',
                      background: kbColors[index % kbColors.length],
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '20px',
                    }}
                  >
                    <DatabaseIcon />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h4 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '2px' }}>{kb.name}</h4>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{kb.embedding_provider}</p>
                  </div>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: '1.4' }}>
                  {kb.description || '暂无描述'}
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {kb.total_documents} 个文档
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(kb.kb_id)
                    }}
                    style={{
                      padding: '4px 8px',
                      background: 'transparent',
                      border: 'none',
                      color: '#ef4444',
                      cursor: 'pointer',
                      borderRadius: '4px',
                    }}
                    title="删除"
                  >
                    <TrashIcon />
                  </button>
                </div>
              </div>
            ))}

            {knowledgeBases.length === 0 && (
              <div
                style={{
                  padding: '32px 24px',
                  background: 'white',
                  borderRadius: '12px',
                  border: '1px dashed var(--border-color)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>📚</div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>还没有知识库</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  style={{
                    marginTop: '12px',
                    padding: '8px 16px',
                    background: 'var(--primary-color)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  创建第一个知识库
                </button>
              </div>
            )}
          </div>
        </div>

        {/* 右侧：知识库详情 */}
        <div>
          {selectedKB ? (
            <div>
              {/* 知识库信息卡片 */}
              <div
                style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: '20px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '4px' }}>{selectedKB.name}</h3>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                      {selectedKB.description || '暂无描述'}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary-color)' }}>
                      {selectedKB.total_documents}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>文档数</div>
                  </div>
                </div>

                {/* 操作按钮 */}
                <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    style={{
                      padding: '10px 16px',
                      background: 'var(--primary-color)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '14px',
                      cursor: uploading ? 'not-allowed' : 'pointer',
                      opacity: uploading ? 0.7 : 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <UploadIcon /> {uploading ? '上传中...' : '上传文档'}
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".md,.txt,.pdf,.docx,.doc,.xlsx,.xls,.csv,.pptx,.ppt,.odt,.ods,.odp,.epub,.rtf,.py,.js,.ts,.jsx,.tsx,.java,.cpp,.c,.h,.hpp,.go,.rs,.rb,.php,.html,.css,.json,.xml,.yaml,.yml,.sql,.sh,.swift,.kt"
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                  />
                </div>
              </div>

              {/* 文档列表 */}
              <div
                style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: '20px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '20px',
                }}
              >
                <h4 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '12px' }}>
                  文档列表 ({documents.length})
                </h4>
                {loadingDocs ? (
                  <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>加载中...</p>
                ) : documents.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {documents.map((doc, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          padding: '12px',
                          background: 'var(--bg-main)',
                          borderRadius: '8px',
                          border: '1px solid var(--border-color)',
                        }}
                      >
                        <div style={{ fontSize: '24px' }}>
                          {doc.file_type === '.pdf' ? '📄' :
                           doc.file_type === '.docx' || doc.file_type === '.doc' ? '📝' :
                           doc.file_type === '.xlsx' || doc.file_type === '.xls' || doc.file_type === '.csv' ? '📊' :
                           doc.file_type === '.pptx' || doc.file_type === '.ppt' ? '📽️' :
                           doc.file_type === '.md' ? '📑' :
                           doc.file_type === '.txt' ? '📃' : '📁'}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: '14px',
                              fontWeight: '500',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                            title={doc.filename}
                          >
                            {doc.filename}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {doc.file_type || '未知类型'} · {doc.chunks} 个文本块
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-secondary)' }}>
                    <div style={{ fontSize: '32px', marginBottom: '8px' }}>📂</div>
                    <p style={{ fontSize: '14px' }}>暂无文档</p>
                    <p style={{ fontSize: '12px', marginTop: '4px' }}>点击上方「上传文档」按钮添加文件</p>
                  </div>
                )}
              </div>

              {/* 搜索区域 */}
              <div
                style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: '20px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '20px',
                }}
              >
                <h4 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '12px' }}>检索测试</h4>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="输入查询内容..."
                    style={{
                      flex: 1,
                      padding: '10px 14px',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      fontSize: '14px',
                    }}
                  />
                  <button
                    onClick={handleSearch}
                    disabled={searching || !searchQuery.trim()}
                    style={{
                      padding: '10px 20px',
                      background: 'var(--primary-color)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '14px',
                      cursor: searching ? 'not-allowed' : 'pointer',
                      opacity: searching ? 0.7 : 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <SearchIcon /> {searching ? '搜索中...' : '搜索'}
                  </button>
                </div>

                {/* 搜索结果 */}
                {searchResults.length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <h5 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                      找到 {searchResults.length} 个相关结果
                    </h5>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {searchResults.map((result, index) => (
                        <div
                          key={result.id}
                          style={{
                            padding: '12px',
                            background: 'var(--bg-main)',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                              #{index + 1} {result.metadata?.filename || '未知文件'}
                            </span>
                            <span
                              style={{
                                fontSize: '12px',
                                fontWeight: '500',
                                color: result.similarity > 0.7 ? '#16a34a' : result.similarity > 0.4 ? '#f59e0b' : '#6b7280',
                              }}
                            >
                              相似度: {(result.similarity * 100).toFixed(1)}%
                            </span>
                          </div>
                          <p
                            style={{
                              fontSize: '13px',
                              color: 'var(--text-primary)',
                              lineHeight: '1.5',
                              maxHeight: '100px',
                              overflow: 'hidden',
                            }}
                          >
                            {result.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div
              style={{
                background: 'white',
                borderRadius: '12px',
                padding: '60px 24px',
                border: '1px dashed var(--border-color)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '64px', marginBottom: '16px' }}>📚</div>
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>选择知识库</h3>
              <p style={{ color: 'var(--text-secondary)' }}>从左侧选择一个知识库，或创建新的知识库</p>
            </div>
          )}
        </div>
      </div>

      {/* 创建知识库弹窗 */}
      {showCreateModal && (
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
          onClick={() => setShowCreateModal(false)}
        >
          <div
            style={{
              background: 'white',
              borderRadius: '16px',
              width: '100%',
              maxWidth: '480px',
              maxHeight: '90vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '600' }}>创建知识库</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{
                  width: '32px',
                  height: '32px',
                  border: 'none',
                  background: 'transparent',
                  fontSize: '24px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  borderRadius: '8px',
                }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: '24px' }}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                  名称 *
                </label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  placeholder="例如：技术文档库"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                  描述
                </label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  placeholder="知识库的用途描述..."
                  rows={3}
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

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                  Embedding 提供商 *
                </label>
                <select
                  value={createForm.embedding_provider}
                  onChange={(e) => setCreateForm({ ...createForm, embedding_provider: e.target.value as any })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '14px',
                  }}
                >
                  <option value="fake">🧪 Fake (测试模式，无需 API Key)</option>
                  <option value="kimi">🌙 Kimi (Moonshot)</option>
                  <option value="openai">🤖 OpenAI</option>
                </select>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  测试模式使用随机向量，适合演示和测试
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                    分块大小
                  </label>
                  <input
                    type="number"
                    value={createForm.chunk_size}
                    onChange={(e) => setCreateForm({ ...createForm, chunk_size: parseInt(e.target.value) || 500 })}
                    min={100}
                    max={2000}
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
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                    重叠大小
                  </label>
                  <input
                    type="number"
                    value={createForm.chunk_overlap}
                    onChange={(e) => setCreateForm({ ...createForm, chunk_overlap: parseInt(e.target.value) || 50 })}
                    min={0}
                    max={500}
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      fontSize: '14px',
                    }}
                  />
                </div>
              </div>
            </div>

            <div
              style={{
                padding: '16px 24px',
                borderTop: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '12px',
              }}
            >
              <button
                onClick={() => setShowCreateModal(false)}
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
                onClick={handleCreate}
                style={{
                  padding: '10px 24px',
                  background: 'var(--primary-color)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                }}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
