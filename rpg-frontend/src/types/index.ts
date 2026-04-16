// 类型定义

export type RobotStatus = 'idle' | 'thinking' | 'speaking'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  timestamp: number
  isError?: boolean
  isStreaming?: boolean
  agentName?: string  // 哪个 Agent 发的消息
  agentRole?: string  // Agent 角色
  agentAvatarType?: string  // Agent 头像类型
}

export interface Conversation {
  conversation_id: string
  title: string
  agent_id?: string
  message_count: number
  updated_at: number
}

// ========== 多 Agent 系统类型 ==========

export interface AgentInfo {
  id: string
  name: string
  role: string
  personality: string
  avatar_type: string
}

// ========== Agent 配置类型（每个 Agent 独立配置） ==========

export type AvatarType = 'aiden' | 'wrench'

export interface Provider {
  id: string
  name: string
  provider_type: ProviderType
  base_url: string
  api_key: string
  model_id: string
  model_name: string
  is_active: boolean
}

export interface CreateProviderRequest {
  name: string
  provider_type: ProviderType
  base_url: string
  api_key: string
  model_id: string
  model_name: string
}

export interface UpdateProviderRequest {
  name?: string
  base_url?: string
  api_key?: string
  model_id?: string
  model_name?: string
  is_active?: boolean
}

export interface AgentConfig {
  id: string
  name: string
  role: string
  personality: string
  avatar_type: AvatarType | string
  provider_id: string
  kb_id?: string
  provider?: ProviderInfo
  created_at?: string
  updated_at?: string
  is_active: boolean
  specialty?: string
  expertise?: string
  agent_type?: 'manager' | 'worker'
}

export interface CreateAgentRequest {
  name: string
  role: string
  personality: string
  provider_id: string
  kb_id?: string
}

export interface UpdateAgentRequest {
  name?: string
  role?: string
  personality?: string
  avatar_type?: AvatarType
  provider_type?: ProviderType
  model_id?: string
  model_name?: string
  api_key?: string
  base_url?: string
  kb_id?: string
  is_active?: boolean
}

export interface AgentResponse {
  agent_name: string
  agent_role: string
  content: string
}

export interface ChatResponse {
  responses: AgentResponse[]
}

export interface AgentListResponse {
  agents: AgentInfo[]
}

export interface DocumentStats {
  totalFiles: number
  totalSize: number
}

// Phaser 场景回调接口
export interface ChatSceneCallbacks {
  onPlayerMessage: (text: string) => void
  onNPCAnimationComplete: () => void
}

// ========== 模型配置类型 ==========

export type ProviderType = 'dashscope' | 'openai' | 'anthropic' | 'custom' | 'kimi'

export interface LLMConfig {
  provider: ProviderType
  model_id: string
  model_name: string
  api_key: string
  base_url: string
  api_key_prefix: string
  is_dashscope: boolean
  dashscope_model: string
}

export interface EmbeddingConfig {
  provider: ProviderType
  model_id: string
  model_name: string
  api_key: string
  base_url: string
  api_key_prefix: string
  is_dashscope: boolean
  dashscope_model: string
}

// 默认配置常量
export const DEFAULT_LLM_CONFIG: LLMConfig = {
  provider: 'dashscope',
  model_id: 'qwen-max',
  model_name: 'Qwen Max',
  api_key: '',
  base_url: '',
  api_key_prefix: 'sk-',
  is_dashscope: true,
  dashscope_model: 'qwen-max',
}

export const DEFAULT_EMBEDDING_CONFIG: EmbeddingConfig = {
  provider: 'dashscope',
  model_id: 'text-embedding-v4',
  model_name: 'Text Embedding V4',
  api_key: '',
  base_url: '',
  api_key_prefix: 'sk-',
  is_dashscope: true,
  dashscope_model: 'text-embedding-v4',
}

export interface ModelConfig {
  llm: LLMConfig
  embedding: EmbeddingConfig
  version: string
}

export interface TestConnectionResponse {
  success: boolean
  message: string
}

export interface ProviderModel {
  id: string
  name: string
  description: string
}

// Provider 信息（新的 providers API）
export interface ProviderInfo {
  id: string
  name: string
  provider_type: 'dashscope' | 'anthropic'
  base_url: string
  api_key: string
  model_id: string
  model_name: string
  is_active: boolean
}

// Provider 支持的模型
export interface ProviderSupportedModel {
  id: string
  name: string
}

// Provider 类型信息
export interface ProviderTypeInfo {
  id: ProviderType
  name: string
  description: string
  required_fields: string[]
  optional_fields?: string[]
  supported_models?: ProviderSupportedModel[]
}

// ========== Manager Agent 类型 ==========

export interface ManagerConfig {
  id: string
  name: string
  role: string
  personality: string
  avatar_type: string
  agent_type: 'manager'
  provider_id: string
  kb_id: string
  provider?: ProviderInfo
  is_active: boolean
}

// ========== 工具管理类型 ==========

export interface ToolConfig {
  name: string
  enabled: boolean
  description: string
}

export interface ToolUpdateRequest {
  enabled: boolean
}

export interface ToolsBatchUpdateRequest {
  tools: Record<string, boolean>
}

export interface ToolUpdateResponse {
  success: boolean
  message: string
}

// ========== 知识库类型 ==========

export interface KnowledgeBase {
  kb_id: string
  name: string
  description: string
  embedding_provider: string
  total_documents: number
}

export interface KBDocument {
  filename: string
  source: string
  file_type: string
  chunks: number
}

export interface CreateKBRequest {
  name: string
  description: string
  embedding_provider: 'kimi' | 'openai' | 'fake'
  chunk_size: number
  chunk_overlap: number
}

export interface SearchResult {
  id: string
  content: string
  similarity: number
  metadata: {
    filename?: string
    source?: string
    file_type?: string
  }
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total: number
}

export interface QueryContextResponse {
  question: string
  context: string
  sources: SearchResult[]
  source_count: number
}
