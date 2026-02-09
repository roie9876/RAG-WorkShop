/* ------------------------------------------------------------------
   Types for GitHub RAG frontend
   ------------------------------------------------------------------ */

export interface RepoMetadata {
  owner: string
  name: string
  full_name: string
  description: string
  language: string
  languages: Record<string, number>
  topics: string[]
  stars: number
  forks: number
  license: string
}

export interface RepoStatus {
  repo_full_name: string
  status: 'not_indexed' | 'pending' | 'cloning' | 'chunking' | 'embedding' | 'indexing' | 'graphrag' | 'complete' | 'error'
  progress: number
  message: string
  files_count: number
  chunks_count: number
  index_name: string
  error?: string
}

export interface SyncStatus {
  status: 'not_indexed' | 'up_to_date' | 'behind' | 'error'
  message: string
  commit?: string
  indexed_commit?: string
  remote_commit?: string
  last_sync?: string
  indexed_files?: number
  total_chunks?: number
}

export interface SourceChunk {
  id: string
  content: string
  content_type: string
  file_path: string
  language: string
  chunk_type: string
  section_header: string
  parent_class: string
  relevance_score: number
  reranker_score?: number
}

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
  retrieval_metadata: {
    strategy_used: string
    total_chunks: number
    retrieval_time_ms: number
    parameters: Record<string, unknown>
  }
  generation_metadata: {
    model: string
    tokens_used: number
    prompt_tokens: number
    completion_tokens: number
  }
  timing: {
    total_time_ms: number
    retrieval_time_ms: number
    generation_time_ms: number
  }
  combined_results?: {
    search_chunks_count: number
    graphrag_chunks_count: number
    graphrag_response?: string
  }
}

export interface QueryConfig {
  top_k: number
  search_mode: 'vector' | 'text' | 'hybrid' | 'semantic'
  min_score: number
  content_type_filter: 'all' | 'code' | 'docs' | 'config' | 'ci' | 'metadata'
  language_filter: string
  retrieval_strategy: 'auto' | 'hybrid' | 'graphrag' | 'combined'
  graphrag_mode: 'local' | 'global' | 'drift'
  graphrag_community_level: number
  graphrag_response_type: string
}
