import axios from 'axios'
import type { QueryConfig, QueryResponse, DocumentStatus, IndexSchema, IndexStats } from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Query API
export const queryApi = {
  execute: async (question: string, config: QueryConfig): Promise<QueryResponse> => {
    const response = await api.post('/query', {
      question,
      ...config,
    })
    return response.data
  },

  executeStream: async function* (question: string, config: QueryConfig) {
    const response = await fetch('/api/query/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, ...config }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) return

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value)
      const lines = text.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') return
          try {
            yield JSON.parse(data)
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  },
}

// Documents API
export const documentsApi = {
  upload: async (file: File, enableGraphragIndex: boolean = true): Promise<DocumentStatus> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('enable_graphrag_index', String(enableGraphragIndex))

    const response = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getStatus: async (docId: string): Promise<DocumentStatus> => {
    const response = await api.get(`/documents/${docId}/status`)
    return response.data
  },

  list: async (): Promise<{ documents: DocumentStatus[]; total: number }> => {
    const response = await api.get('/documents')
    return response.data
  },

  delete: async (docId: string): Promise<void> => {
    await api.delete(`/documents/${docId}`)
  },

  reindex: async (docId: string): Promise<DocumentStatus> => {
    const response = await api.post(`/documents/${docId}/reindex`)
    return response.data
  },
}

// GraphRAG API
export interface GraphRAGStatus {
  success: boolean
  status: {
    ready: boolean
    input_documents: number
    output_exists: boolean
    entities_count: number
    relationships_count: number
    communities_count: number
    has_parquet: boolean
    is_indexing?: boolean
    indexing_progress?: string
  }
}

export const graphragApi = {
  getStatus: async (): Promise<GraphRAGStatus> => {
    const response = await api.get('/graphrag/status')
    return response.data
  },

  startIndexing: async (timeout: number = 600): Promise<{ success: boolean; result: unknown }> => {
    const response = await api.post('/graphrag/index', { timeout })
    return response.data
  },

  clearIndex: async (): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/graphrag/clear')
    return response.data
  },
}

// Index API
export const indexApi = {
  getSchema: async (): Promise<IndexSchema> => {
    const response = await api.get('/index/schema')
    return response.data
  },

  getStats: async (): Promise<IndexStats> => {
    const response = await api.get('/index/stats')
    return response.data
  },

  deleteIndex: async (): Promise<void> => {
    await api.delete('/index/reset')
  },
}

// Config API
export const configApi = {
  get: async (): Promise<{ query: QueryConfig; index: Record<string, unknown> }> => {
    const response = await api.get('/config')
    return response.data
  },

  update: async (config: QueryConfig): Promise<QueryConfig> => {
    const response = await api.post('/config', config)
    return response.data
  },

  reset: async (): Promise<QueryConfig> => {
    const response = await api.post('/config/reset')
    return response.data
  },
}

// Blob API
export const blobApi = {
  getSasUrl: async (blobPath: string, permission: 'read' | 'write' = 'read'): Promise<string> => {
    const response = await api.get(`/blob/sas/${blobPath}`, {
      params: { permission },
    })
    return response.data.url
  },
}

export default api
