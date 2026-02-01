import { useCallback, useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, CheckCircle, XCircle, Loader2, RefreshCw, Database, Network, Trash2 } from 'lucide-react'
import { documentsApi, graphragApi, indexApi, type GraphRAGStatus } from '../services/api'
import type { DocumentStatus, IndexStats } from '../types'

export function DocumentUpload() {
  const [documents, setDocuments] = useState<DocumentStatus[]>([])
  const [uploading, setUploading] = useState(false)
  const [enableGraphragIndex, setEnableGraphragIndex] = useState(true)
  const [deletingVectorIndex, setDeletingVectorIndex] = useState(false)
  const [deletingGraphragIndex, setDeletingGraphragIndex] = useState(false)
  const [graphragStatus, setGraphragStatus] = useState<GraphRAGStatus['status'] | null>(null)
  const [loadingGraphragStatus, setLoadingGraphragStatus] = useState(false)
  const [isIndexing, setIsIndexing] = useState(false)
  const [indexStats, setIndexStats] = useState<IndexStats | null>(null)
  const [loadingIndexStats, setLoadingIndexStats] = useState(false)

  // Fetch AI Search index stats
  const fetchIndexStats = useCallback(async () => {
    setLoadingIndexStats(true)
    try {
      const stats = await indexApi.getStats()
      setIndexStats(stats)
    } catch (error) {
      console.error('Failed to fetch index stats:', error)
    } finally {
      setLoadingIndexStats(false)
    }
  }, [])

  // Fetch GraphRAG status on mount and periodically
  const fetchGraphragStatus = useCallback(async () => {
    setLoadingGraphragStatus(true)
    try {
      const response = await graphragApi.getStatus()
      setGraphragStatus(response.status)
    } catch (error) {
      console.error('Failed to fetch GraphRAG status:', error)
    } finally {
      setLoadingGraphragStatus(false)
    }
  }, [])

  useEffect(() => {
    fetchGraphragStatus()
    fetchIndexStats()
    // Poll every 30 seconds
    const interval = setInterval(() => {
      fetchGraphragStatus()
      fetchIndexStats()
    }, 30000)
    return () => clearInterval(interval)
  }, [fetchGraphragStatus, fetchIndexStats])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true)

    for (const file of acceptedFiles) {
      try {
        const status = await documentsApi.upload(file, enableGraphragIndex)
        setDocuments((prev) => [...prev, status])

        // Poll for status updates
        pollStatus(status.id)
      } catch (error) {
        console.error('Upload failed:', error)
      }
    }

    setUploading(false)
  }, [enableGraphragIndex])

  const pollStatus = async (docId: string) => {
    const checkStatus = async () => {
      try {
        const status = await documentsApi.getStatus(docId)
        setDocuments((prev) =>
          prev.map((d) => (d.id === docId ? status : d))
        )

        if (status.status === 'pending' || status.status === 'processing') {
          setTimeout(checkStatus, 2000) // Poll every 2 seconds
        } else if (status.status === 'completed') {
          // Refresh both indexes after document processing completes
          setTimeout(() => {
            fetchIndexStats()
            if (enableGraphragIndex) {
              fetchGraphragStatus()
            }
          }, 3000)
        }
      } catch (error) {
        console.error('Status check failed:', error)
      }
    }
    checkStatus()
  }

  const handleReindex = async (docId: string) => {
    try {
      const updated = await documentsApi.reindex(docId)
      setDocuments((prev) => prev.map((d) => (d.id === docId ? updated : d)))
      pollStatus(docId)
    } catch (error) {
      console.error('Reindex failed:', error)
    }
  }

  const handleStartGraphragIndex = async () => {
    setIsIndexing(true)
    try {
      await graphragApi.startIndexing(1800) // 30 min timeout
      // Poll for status updates
      const pollGraphrag = setInterval(async () => {
        const response = await graphragApi.getStatus()
        setGraphragStatus(response.status)
        if (response.status.ready) {
          clearInterval(pollGraphrag)
          setIsIndexing(false)
        }
      }, 10000) // Poll every 10 seconds
    } catch (error) {
      console.error('GraphRAG indexing failed:', error)
      setIsIndexing(false)
    }
  }

  const handleDeleteVectorIndex = async () => {
    if (!confirm('⚠️ Delete Vector Search Index?\n\nThis will remove ALL chunks (text, tables, figures) from Azure AI Search.\n\nYou will need to re-upload documents to rebuild the index.')) {
      return
    }
    setDeletingVectorIndex(true)
    try {
      await indexApi.deleteIndex()
      setIndexStats(null)
      setDocuments([])
      await fetchIndexStats()
    } catch (error) {
      console.error('Failed to delete vector index:', error)
      alert('Failed to delete index: ' + (error as Error).message)
    } finally {
      setDeletingVectorIndex(false)
    }
  }

  const handleDeleteGraphragIndex = async () => {
    if (!confirm('⚠️ Delete Knowledge Graph Index?\n\nThis will remove all GraphRAG data including:\n- Exported documents\n- Entities and relationships\n- Community reports\n\nYou will need to re-process documents to rebuild.')) {
      return
    }
    setDeletingGraphragIndex(true)
    try {
      await graphragApi.clearIndex()
      await fetchGraphragStatus()
    } catch (error) {
      console.error('Failed to delete GraphRAG index:', error)
      alert('Failed to delete GraphRAG index: ' + (error as Error).message)
    } finally {
      setDeletingGraphragIndex(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    },
    multiple: true,
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Loader2 className="h-4 w-4 text-gray-400" />
    }
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <Upload className="h-6 w-6" />
        Document Upload & Index Status
      </h2>

      {/* Index Status Panels - LARGER */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Azure AI Search Status */}
        <div className="p-5 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-200 rounded-lg">
                <Database className="h-6 w-6 text-blue-700" />
              </div>
              <span className="text-lg font-semibold text-blue-900">Vector Search Index</span>
            </div>
            <div className="flex items-center gap-2">
              {loadingIndexStats ? (
                <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              ) : (indexStats?.document_count ?? 0) > 0 ? (
                <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full flex items-center gap-1">
                  <CheckCircle className="h-4 w-4" /> Ready
                </span>
              ) : (
                <span className="px-3 py-1 bg-yellow-100 text-yellow-700 text-sm font-medium rounded-full flex items-center gap-1">
                  <XCircle className="h-4 w-4" /> Empty
                </span>
              )}
              <button
                onClick={fetchIndexStats}
                className="p-2 rounded-lg hover:bg-blue-200 transition-colors"
                title="Refresh status"
                disabled={loadingIndexStats}
              >
                <RefreshCw className={`h-4 w-4 text-blue-600 ${loadingIndexStats ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={handleDeleteVectorIndex}
                className="p-2 rounded-lg hover:bg-red-100 transition-colors"
                title="Delete index"
                disabled={deletingVectorIndex || (indexStats?.document_count ?? 0) === 0}
              >
                {deletingVectorIndex ? (
                  <Loader2 className="h-4 w-4 text-red-500 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4 text-red-500" />
                )}
              </button>
            </div>
          </div>
          
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-600">Total Chunks</span>
              <span className="text-2xl font-bold text-blue-900">{indexStats?.document_count ?? 0}</span>
            </div>
            {indexStats?.content_type_counts && Object.keys(indexStats.content_type_counts).length > 0 && (
              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-blue-200">
                <div className="text-center p-2 bg-white/50 rounded-lg">
                  <div className="text-lg font-semibold text-blue-800">{indexStats.content_type_counts.text ?? 0}</div>
                  <div className="text-xs text-blue-600">📝 Text</div>
                </div>
                <div className="text-center p-2 bg-white/50 rounded-lg">
                  <div className="text-lg font-semibold text-blue-800">{indexStats.content_type_counts.table ?? 0}</div>
                  <div className="text-xs text-blue-600">📊 Tables</div>
                </div>
                <div className="text-center p-2 bg-white/50 rounded-lg">
                  <div className="text-lg font-semibold text-blue-800">{indexStats.content_type_counts.figure ?? 0}</div>
                  <div className="text-xs text-blue-600">🖼️ Figures</div>
                </div>
              </div>
            )}
            <p className="text-xs text-blue-500 pt-2">Powered by Azure AI Search</p>
          </div>
        </div>

        {/* GraphRAG Status */}
        <div className="p-5 rounded-xl bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-200 rounded-lg">
                <Network className="h-6 w-6 text-purple-700" />
              </div>
              <span className="text-lg font-semibold text-purple-900">Knowledge Graph</span>
            </div>
            <div className="flex items-center gap-2">
              {loadingGraphragStatus ? (
                <Loader2 className="h-5 w-5 animate-spin text-purple-500" />
              ) : graphragStatus?.ready ? (
                <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full flex items-center gap-1">
                  <CheckCircle className="h-4 w-4" /> Ready
                </span>
              ) : isIndexing ? (
                <span className="px-3 py-1 bg-orange-100 text-orange-700 text-sm font-medium rounded-full flex items-center gap-1">
                  <Loader2 className="h-4 w-4 animate-spin" /> Building...
                </span>
              ) : (
                <span className="px-3 py-1 bg-yellow-100 text-yellow-700 text-sm font-medium rounded-full flex items-center gap-1">
                  <XCircle className="h-4 w-4" /> Not Built
                </span>
              )}
              <button
                onClick={fetchGraphragStatus}
                className="p-2 rounded-lg hover:bg-purple-200 transition-colors"
                title="Refresh status"
                disabled={loadingGraphragStatus}
              >
                <RefreshCw className={`h-4 w-4 text-purple-600 ${loadingGraphragStatus ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={handleDeleteGraphragIndex}
                className="p-2 rounded-lg hover:bg-red-100 transition-colors"
                title="Delete GraphRAG index"
                disabled={deletingGraphragIndex || ((graphragStatus?.input_documents ?? 0) === 0 && !graphragStatus?.ready)}
              >
                {deletingGraphragIndex ? (
                  <Loader2 className="h-4 w-4 text-red-500 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4 text-red-500" />
                )}
              </button>
            </div>
          </div>
          
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-600">Documents Ready</span>
              <span className="text-2xl font-bold text-purple-900">{graphragStatus?.input_documents ?? 0}</span>
            </div>
            {graphragStatus?.ready ? (
              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-purple-200">
                <div className="text-center p-2 bg-white/50 rounded-lg">
                  <div className="text-lg font-semibold text-purple-800">{graphragStatus.entities_count ?? 0}</div>
                  <div className="text-xs text-purple-600">🔗 Entities</div>
                </div>
                <div className="text-center p-2 bg-white/50 rounded-lg">
                  <div className="text-lg font-semibold text-purple-800">{graphragStatus.relationships_count ?? 0}</div>
                  <div className="text-xs text-purple-600">↔️ Relations</div>
                </div>
              </div>
            ) : (
              <div className="pt-3 border-t border-purple-200">
                {!graphragStatus?.ready && (graphragStatus?.input_documents ?? 0) > 0 && !isIndexing && (
                  <button
                    onClick={handleStartGraphragIndex}
                    className="w-full py-2 px-4 rounded-lg bg-purple-600 text-white font-medium hover:bg-purple-700 transition-colors"
                  >
                    🚀 Build Knowledge Graph
                  </button>
                )}
                {isIndexing && (
                  <div className="text-center py-2">
                    <Loader2 className="h-5 w-5 animate-spin text-purple-600 mx-auto mb-1" />
                    <p className="text-sm text-purple-600">Building graph... (may take 30-60 min)</p>
                  </div>
                )}
                {(graphragStatus?.input_documents ?? 0) === 0 && (
                  <p className="text-sm text-purple-500 text-center py-2">Upload documents to enable</p>
                )}
              </div>
            )}
            <p className="text-xs text-purple-500 pt-2">Powered by Microsoft GraphRAG</p>
          </div>
        </div>
      </div>

      {/* GraphRAG Index Checkbox */}
      <div className="mb-5 flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
        <input
          type="checkbox"
          id="enable-graphrag"
          checked={enableGraphragIndex}
          onChange={(e) => setEnableGraphragIndex(e.target.checked)}
          className="h-5 w-5 rounded border-muted-foreground/25"
        />
        <label htmlFor="enable-graphrag" className="text-sm text-muted-foreground cursor-pointer">
          <span className="font-medium">Enable GraphRAG indexing</span> — automatically builds knowledge graph for cross-document reasoning
        </label>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-10 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
          ${uploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />
        <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
        {isDragActive ? (
          <p className="text-primary">Drop files here...</p>
        ) : (
          <>
            <p className="text-muted-foreground">
              Drag & drop files here, or click to browse
            </p>
            <p className="text-sm text-muted-foreground/75 mt-1">
              Supports PDF, DOCX, XLSX, PPTX
            </p>
          </>
        )}
      </div>

      {/* Uploaded Documents */}
      {documents.length > 0 && (
        <div className="mt-4 space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <File className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{doc.filename}</p>
                  {doc.status === 'completed' && (
                    <p className="text-xs text-muted-foreground">
                      {doc.chunks_created} chunks, {doc.figures_extracted} figures
                    </p>
                  )}
                  {doc.status === 'failed' && (
                    <p className="text-xs text-red-500">{doc.error_message}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {doc.status === 'completed' && (
                  <button
                    onClick={() => handleReindex(doc.id)}
                    className="p-1 rounded hover:bg-muted"
                    title="Reindex document"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                )}
                {getStatusIcon(doc.status)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
