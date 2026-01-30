// API Response Types

export interface QueryConfig {
  top_k: number
  search_mode: 'vector' | 'text' | 'hybrid' | 'semantic'
  semantic_ranker: boolean
  min_score: number
  content_type_filter: 'all' | 'text' | 'table' | 'figure'
  retrieval_strategy: 'auto' | 'hybrid' | 'agentic' | 'graphrag'
}

export interface SourceChunk {
  id: string
  content: string
  content_type: string
  relevance_score: number
  page_numbers: number[]
  source_document: string
  source_document_sas_url?: string
  section_header?: string
  image_sas_url?: string
}

export interface SubQuery {
  query: string
  results_count: number
}

export interface QueryDecomposition {
  original_query: string
  sub_queries: SubQuery[]
}

export interface ToolCall {
  tool_name: string
  arguments: Record<string, unknown>
  result_summary: string
}

export interface MultiHopStep {
  iteration: number
  query: string
  reasoning: string
  tool_calls: ToolCall[]
}

export interface RetrievalMetadata {
  strategy_used: string
  total_chunks_retrieved: number
  retrieval_time_ms: number
  parameters: QueryConfig
  query_decomposition?: QueryDecomposition
  activity_log?: Array<{
    step: number
    action: string
    details?: string
    query?: string
    results?: number
  }>
  multi_hop_trace?: MultiHopStep[]
  content_type_distribution: Record<string, number>
}

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
  retrieval_metadata: RetrievalMetadata
  generation_metadata: {
    model: string
    tokens_used: number
  }
}

export interface DocumentStatus {
  id: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  uploaded_at: string
  processed_at?: string
  chunks_created?: number
  figures_extracted?: number
  error_message?: string
}

export interface IndexField {
  name: string
  type: string
  searchable: boolean
  filterable: boolean
  sortable: boolean
  facetable: boolean
  key: boolean
  analyzer?: string
  dimensions?: number
}

export interface IndexSchema {
  name: string
  fields: IndexField[]
  vector_config?: {
    algorithm: string
    dimensions: number
    m?: number
    ef_construction?: number
    ef_search?: number
  }
  semantic_config?: {
    enabled: boolean
    title_field?: string
    content_fields: string[]
  }
}

export interface IndexStats {
  document_count: number
  storage_size_bytes: number
  last_updated?: string
  content_type_counts: Record<string, number>
}
