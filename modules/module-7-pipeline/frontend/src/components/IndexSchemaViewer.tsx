import { useState, useEffect } from 'react'
import { Database, ChevronDown, ChevronRight, RefreshCw, Trash2 } from 'lucide-react'
import { indexApi } from '../services/api'
import type { IndexSchema, IndexStats } from '../types'

export function IndexSchemaViewer() {
  const [schema, setSchema] = useState<IndexSchema | null>(null)
  const [stats, setStats] = useState<IndexStats | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [showFullJson, setShowFullJson] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [schemaData, statsData] = await Promise.all([
        indexApi.getSchema(),
        indexApi.getStats(),
      ])
      setSchema(schemaData)
      setStats(statsData)
    } catch (err) {
      setError('Failed to load index info')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteIndex = async () => {
    if (!confirm('Delete the search index? This will remove all chunks.')) return
    setLoading(true)
    setError(null)
    try {
      await indexApi.deleteIndex()
      setSchema(null)
      setStats(null)
    } catch (err) {
      setError('Failed to delete index')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-3">
          <Database className="h-6 w-6" />
          Index Schema
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDeleteIndex}
            disabled={loading}
            className="p-2 hover:bg-muted rounded transition-colors disabled:opacity-50"
            title="Delete index"
          >
            <Trash2 className="h-5 w-5" />
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2 hover:bg-muted rounded transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="text-base text-red-500 mb-4">{error}</div>
      )}

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="p-2 rounded bg-muted/50">
            <p className="text-xs text-muted-foreground">Documents</p>
            <p className="text-lg font-semibold">{stats.unique_document_count ?? 0}</p>
          </div>
          <div className="p-2 rounded bg-muted/50">
            <p className="text-xs text-muted-foreground">Chunks</p>
            <p className="text-lg font-semibold">{stats.chunk_count ?? stats.document_count}</p>
          </div>
          <div className="p-2 rounded bg-muted/50">
            <p className="text-xs text-muted-foreground">Content Types</p>
            <div className="flex gap-1 flex-wrap">
              {Object.entries(stats.content_type_counts).map(([type, count]) => (
                <span key={type} className="text-xs">
                  {type}: {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Schema Fields */}
      {schema && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-2 text-sm font-semibold mb-2"
          >
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            Fields ({schema.fields.length})
          </button>

          {expanded && (
            <div className="space-y-1 max-h-48 overflow-auto">
              {schema.fields.map((field) => (
                <div
                  key={field.name}
                  className="flex items-center justify-between p-2 rounded bg-muted/30 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span className={field.key ? 'font-medium text-primary' : ''}>
                      {field.name}
                    </span>
                    {field.key && (
                      <span className="text-xs px-1 py-0.5 rounded bg-primary/10 text-primary">
                        key
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-muted-foreground">
                      {field.type}
                    </span>
                    {field.dimensions && (
                      <span className="text-xs text-muted-foreground">
                        ({field.dimensions}d)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Vector Config */}
          {schema.vector_config && (
            <div className="mt-3 p-2 rounded bg-muted/30">
              <p className="text-xs font-medium mb-1">Vector Search</p>
              <p className="text-xs text-muted-foreground">
                {schema.vector_config.algorithm} ({schema.vector_config.dimensions} dims)
                {schema.vector_config.m && `, m=${schema.vector_config.m}`}
              </p>
            </div>
          )}

          {/* Semantic Config */}
          {schema.semantic_config?.enabled && (
            <div className="mt-2 p-2 rounded bg-muted/30">
              <p className="text-xs font-medium mb-1">Semantic Ranking</p>
              <p className="text-xs text-muted-foreground">
                Title: {schema.semantic_config.title_field || 'N/A'}
              </p>
            </div>
          )}

          {/* Full JSON */}
          <button
            onClick={() => setShowFullJson(!showFullJson)}
            className="mt-3 text-xs text-primary hover:underline"
          >
            {showFullJson ? 'Hide' : 'View'} Full Schema JSON
          </button>

          {showFullJson && (
            <pre className="mt-2 p-2 rounded bg-muted/50 text-xs overflow-auto max-h-48">
              {JSON.stringify(schema, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
