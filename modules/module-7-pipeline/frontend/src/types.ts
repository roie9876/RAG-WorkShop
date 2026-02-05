// API Response Types

export interface QueryConfig {
  // AI Search Parameters
  top_k: number
  search_mode: 'vector' | 'text' | 'hybrid' | 'semantic'
  semantic_ranker: boolean
  min_score: number
  content_type_filter: 'all' | 'text' | 'table' | 'figure'
  
  // General Parameters
  retrieval_strategy: 'auto' | 'hybrid' | 'agentic' | 'agentic_search' | 'iterative' | 'graphrag'
  enable_validation?: boolean
  
  // GraphRAG Parameters
  graphrag_mode: 'local' | 'global' | 'drift'
  graphrag_community_level: number
  graphrag_response_type: 'Multiple Paragraphs' | 'Single Paragraph' | 'Single Sentence' | 'List of 3-7 Points'
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

export interface IterativeStep {
  iteration: number
  search_queries: string[]
  results_count: number
  entities_found: Record<string, string>
  reasoning: string
}

export interface IterativeTrace {
  total_iterations: number
  steps: IterativeStep[]
  all_entities: Record<string, string>
  aspects_covered: string[]
  aspects_missing: string[]
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
  iterative_trace?: IterativeTrace
  content_type_distribution: Record<string, number>
}

// Validation Types
export interface ChunkValidationDetail {
  chunk_id: string
  is_relevant: boolean
  relevance_score: number
  entity_conflict: boolean
  conflict_details?: string
  reasoning: string
}

export interface FilteredChunkInfo {
  chunk_id: string
  reason: string
  relevance_score: number
  entity_conflict: boolean
}

export interface ValidationIssue {
  severity: 'info' | 'warning' | 'error'
  type: string
  description: string
}

export interface AnswerQualityReport {
  overall_quality: number
  is_grounded: boolean
  completeness_score: number
  aspects_answered: string[]
  aspects_missing: string[]
  confidence: 'low' | 'medium' | 'high'
  issues: ValidationIssue[]
  recommendations: string[]
}

export interface ValidationReport {
  validation_enabled: boolean
  total_chunks_retrieved: number
  chunks_kept: number
  chunks_filtered: number
  filtered_chunks: FilteredChunkInfo[]
  chunk_validations: ChunkValidationDetail[]
  answer_quality?: AnswerQualityReport
  overall_score: number
  validation_passed: boolean
  retry_suggested: boolean
  retry_query?: string
  warnings: string[]
}

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
  retrieval_metadata: RetrievalMetadata
  generation_metadata: {
    model: string
    tokens_used: number
  }
  validation_report?: ValidationReport
}

export interface DocumentStatus {
  id: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  uploaded_at: string
  blob_path?: string
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

export interface IndexedDocument {
  filename: string
  doc_id: string
  chunk_count: number
}

export interface IndexStats {
  document_count: number  // Total chunks (backwards compatibility)
  chunk_count: number  // Same as document_count
  unique_document_count: number  // Actual number of unique documents
  indexed_documents: IndexedDocument[]  // List of documents with chunk counts
  storage_size_bytes: number
  last_updated?: string
  content_type_counts: Record<string, number>
}
