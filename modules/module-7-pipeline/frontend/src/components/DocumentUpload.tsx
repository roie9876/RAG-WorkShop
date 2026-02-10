import { useCallback, useState, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, CheckCircle, XCircle, Loader2, RefreshCw, Database, Network, Trash2, BarChart3, X } from 'lucide-react'
import { documentsApi, graphragApi, indexApi, type GraphRAGStatus, type TokenUsageResponse } from '../services/api'
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
  const [showTokenUsage, setShowTokenUsage] = useState(false)
  const [tokenUsage, setTokenUsage] = useState<TokenUsageResponse['token_usage'] | null>(null)
  const [loadingTokenUsage, setLoadingTokenUsage] = useState(false)
  
  // Use refs to track polling state without causing re-renders
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const isPollingRef = useRef(false)

  // Fetch AI Search index stats (don't set loading during polling)
  const fetchIndexStats = useCallback(async (showLoading = true) => {
    if (showLoading) setLoadingIndexStats(true)
    try {
      const stats = await indexApi.getStats()
      setIndexStats(stats)
    } catch (error) {
      console.error('Failed to fetch index stats:', error)
    } finally {
      if (showLoading) setLoadingIndexStats(false)
    }
  }, [])

  // Fetch GraphRAG status on mount and periodically (don't set loading during polling)
  const fetchGraphragStatus = useCallback(async (showLoading = true) => {
    // Prevent concurrent fetches
    if (isPollingRef.current) return
    isPollingRef.current = true
    
    if (showLoading) setLoadingGraphragStatus(true)
    try {
      const response = await graphragApi.getStatus()
      console.log('GraphRAG status:', response.status)
      console.log('Progress detail:', response.status.progress_detail)
      // Only update if we got valid data
      if (response.status) {
        setGraphragStatus(response.status)
      }
    } catch (error) {
      console.error('Failed to fetch GraphRAG status:', error)
      // Don't clear the status on error - keep showing last known state
    } finally {
      if (showLoading) setLoadingGraphragStatus(false)
      isPollingRef.current = false
    }
  }, [])

  // Set up polling with stable interval
  useEffect(() => {
    // Initial fetch
    fetchGraphragStatus(true)
    fetchIndexStats(true)
    
    // Start polling function
    const startPolling = () => {
      // Clear any existing interval
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
      
      // Determine polling rate based on current state
      const isCurrentlyIndexing = isIndexing || graphragStatus?.is_indexing
      const pollInterval = isCurrentlyIndexing ? 3000 : 30000
      
      pollingRef.current = setInterval(() => {
        fetchGraphragStatus(false) // Don't show loading spinner during polling
        fetchIndexStats(false)
      }, pollInterval)
    }
    
    startPolling()
    
    // Cleanup on unmount
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, []) // Only run on mount
  
  // Adjust polling rate when indexing state changes
  useEffect(() => {
    const isCurrentlyIndexing = isIndexing || graphragStatus?.is_indexing
    
    // Clear and restart with new interval
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    const pollInterval = isCurrentlyIndexing ? 3000 : 30000
    pollingRef.current = setInterval(() => {
      fetchGraphragStatus(false)
      fetchIndexStats(false)
    }, pollInterval)
    
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [isIndexing, graphragStatus?.is_indexing, fetchGraphragStatus, fetchIndexStats])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    console.log('onDrop triggered, files:', acceptedFiles.map(f => `${f.name} (${f.size} bytes)`))
    if (acceptedFiles.length === 0) return
    
    setUploading(true)

    try {
      // Use batch upload for multiple files
      const response = await documentsApi.uploadBatch(acceptedFiles, enableGraphragIndex)
      
      // Add all uploaded documents to the list
      setDocuments((prev) => [...prev, ...response.documents])
      
      // Start polling for each document's status
      response.documents.forEach((doc) => {
        pollStatus(doc.id)
      })
      
      // Show notification if some files were rejected
      if (response.rejected > 0) {
        console.warn(`${response.rejected} file(s) were rejected (unsupported format)`)
      }
    } catch (error) {
      console.error('Batch upload failed:', error)
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
            fetchIndexStats(false)
            if (enableGraphragIndex) {
              fetchGraphragStatus(false)
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
    if (!confirm('⚠️ Delete Knowledge Graph Index?\n\nThis will remove ALL GraphRAG data including:\n- Exported documents\n- Entities and relationships\n- Community reports\n- Cached LLM responses\n\nYou will need to re-process documents to rebuild.')) {
      return
    }
    setDeletingGraphragIndex(true)
    try {
      const result = await graphragApi.clearIndex()
      if (!result.success) {
        alert('⚠️ Failed to fully clear GraphRAG index. Some files may be locked. Try restarting the server.')
      }
      // Reset token usage cache since cache was deleted
      setTokenUsage(null)
      await fetchGraphragStatus(true)
    } catch (error) {
      console.error('Failed to delete GraphRAG index:', error)
      const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail 
        || (error as Error).message
      alert('Failed to delete GraphRAG index: ' + msg)
    } finally {
      setDeletingGraphragIndex(false)
    }
  }

  // Manual refresh handlers (show loading)
  const handleRefreshIndexStats = () => fetchIndexStats(true)
  const handleRefreshGraphragStatus = () => fetchGraphragStatus(true)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/bmp': ['.bmp'],
      'image/tiff': ['.tiff', '.tif'],
      'image/heif': ['.heif'],
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
    <div className="rounded-xl border bg-card p-8">
      <h2 className="text-2xl font-semibold mb-8 flex items-center gap-3">
        <Upload className="h-7 w-7" />
        Document Upload & Index Status
      </h2>

      {/* Index Status Panels - LARGER */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        {/* Azure AI Search Status */}
        <div className="p-6 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-200 rounded-lg">
                <Database className="h-7 w-7 text-blue-700" />
              </div>
              <span className="text-xl font-semibold text-blue-900">Vector Search Index</span>
            </div>
            <div className="flex items-center gap-2">
              {loadingIndexStats ? (
                <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
              ) : (indexStats?.document_count ?? 0) > 0 ? (
                <span className="px-4 py-1.5 bg-green-100 text-green-700 text-base font-medium rounded-full flex items-center gap-1">
                  <CheckCircle className="h-5 w-5" /> Ready
                </span>
              ) : (
                <span className="px-4 py-1.5 bg-yellow-100 text-yellow-700 text-base font-medium rounded-full flex items-center gap-1">
                  <XCircle className="h-5 w-5" /> Empty
                </span>
              )}
              <button
                onClick={handleRefreshIndexStats}
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
                  <Loader2 className="h-5 w-5 text-red-500 animate-spin" />
                ) : (
                  <Trash2 className="h-5 w-5 text-red-500" />
                )}
              </button>
            </div>
          </div>
          
          <div className="mt-5 space-y-4">
            {/* Documents Count - NEW */}
            <div className="flex items-center justify-between pb-3 border-b border-blue-200">
              <span className="text-base text-blue-600">Indexed Documents</span>
              <span className="text-3xl font-bold text-blue-900">{indexStats?.unique_document_count ?? 0}</span>
            </div>
            
            {/* Document List - NEW */}
            {indexStats?.indexed_documents && indexStats.indexed_documents.length > 0 && (
              <div className="max-h-32 overflow-y-auto space-y-1">
                {indexStats.indexed_documents.map((doc) => (
                  <div key={doc.doc_id || doc.filename} className="flex items-center justify-between px-3 py-2 bg-white/60 rounded-lg text-sm">
                    <div className="flex items-center gap-2 truncate">
                      <File className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      <span className="truncate text-blue-800 font-medium">{doc.filename}</span>
                    </div>
                    <span className="text-blue-600 text-xs flex-shrink-0">{doc.chunk_count} chunks</span>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex items-center justify-between">
              <span className="text-base text-blue-600">Total Chunks</span>
              <span className="text-2xl font-bold text-blue-900">{indexStats?.chunk_count ?? 0}</span>
            </div>
            {indexStats?.content_type_counts && Object.keys(indexStats.content_type_counts).length > 0 && (
              <div className="grid grid-cols-3 gap-3 pt-4 border-t border-blue-200">
                <div className="text-center p-3 bg-white/50 rounded-lg">
                  <div className="text-xl font-semibold text-blue-800">{indexStats.content_type_counts.text ?? 0}</div>
                  <div className="text-sm text-blue-600">📝 Text</div>
                </div>
                <div className="text-center p-3 bg-white/50 rounded-lg">
                  <div className="text-xl font-semibold text-blue-800">{indexStats.content_type_counts.table ?? 0}</div>
                  <div className="text-sm text-blue-600">📊 Tables</div>
                </div>
                <div className="text-center p-3 bg-white/50 rounded-lg">
                  <div className="text-xl font-semibold text-blue-800">{indexStats.content_type_counts.figure ?? 0}</div>
                  <div className="text-sm text-blue-600">🖼️ Figures</div>
                </div>
              </div>
            )}
            <p className="text-sm text-blue-500 pt-2">Powered by Azure AI Search</p>
          </div>
        </div>

        {/* GraphRAG Status */}
        <div className="p-6 rounded-xl bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-200 rounded-lg">
                <Network className="h-7 w-7 text-purple-700" />
              </div>
              <span className="text-xl font-semibold text-purple-900">Knowledge Graph</span>
            </div>
            <div className="flex items-center gap-2">
              {loadingGraphragStatus ? (
                <Loader2 className="h-6 w-6 animate-spin text-purple-500" />
              ) : graphragStatus?.ready ? (
                <span className="px-4 py-1.5 bg-green-100 text-green-700 text-base font-medium rounded-full flex items-center gap-1">
                  <CheckCircle className="h-5 w-5" /> Ready
                </span>
              ) : (isIndexing || graphragStatus?.is_indexing) ? (
                <span className="px-4 py-1.5 bg-orange-100 text-orange-700 text-base font-medium rounded-full flex items-center gap-1">
                  <Loader2 className="h-5 w-5 animate-spin" /> Building...
                </span>
              ) : (
                <span className="px-4 py-1.5 bg-yellow-100 text-yellow-700 text-base font-medium rounded-full flex items-center gap-1">
                  <XCircle className="h-5 w-5" /> Not Built
                </span>
              )}
              <button
                onClick={handleRefreshGraphragStatus}
                className="p-2 rounded-lg hover:bg-purple-200 transition-colors"
                title="Refresh status"
                disabled={loadingGraphragStatus}
              >
                <RefreshCw className={`h-5 w-5 text-purple-600 ${loadingGraphragStatus ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={handleDeleteGraphragIndex}
                className="p-2 rounded-lg hover:bg-red-100 transition-colors"
                title="Delete GraphRAG index"
                disabled={deletingGraphragIndex || (
                  (graphragStatus?.input_documents ?? 0) === 0 && 
                  !graphragStatus?.ready && 
                  !graphragStatus?.is_indexing &&
                  (graphragStatus?.entities_count ?? 0) === 0
                )}
              >
                {deletingGraphragIndex ? (
                  <Loader2 className="h-5 w-5 text-red-500 animate-spin" />
                ) : (
                  <Trash2 className="h-5 w-5 text-red-500" />
                )}
              </button>
            </div>
          </div>
          
          <div className="mt-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-200">
              <span className="text-base text-purple-600">Documents Ready</span>
              <span className="text-3xl font-bold text-purple-900">{graphragStatus?.input_documents ?? 0}</span>
            </div>
            
            {/* Document List */}
            {graphragStatus?.input_document_names && graphragStatus.input_document_names.length > 0 && (
              <div className="max-h-32 overflow-y-auto space-y-1">
                {graphragStatus.input_document_names.map((name) => (
                  <div key={name} className="flex items-center gap-2 px-3 py-2 bg-white/60 rounded-lg text-sm">
                    <File className="h-4 w-4 text-purple-500 flex-shrink-0" />
                    <span className="truncate text-purple-800 font-medium">{name}</span>
                  </div>
                ))}
              </div>
            )}
            
            {graphragStatus?.ready ? (
              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-purple-200">
                <div className="text-center p-3 bg-white/50 rounded-lg">
                  <div className="text-xl font-semibold text-purple-800">{graphragStatus.entities_count ?? 0}</div>
                  <div className="text-sm text-purple-600">🔗 Entities</div>
                </div>
                <div className="text-center p-3 bg-white/50 rounded-lg">
                  <div className="text-xl font-semibold text-purple-800">{graphragStatus.relationships_count ?? 0}</div>
                  <div className="text-sm text-purple-600">↔️ Relations</div>
                </div>
              </div>
            ) : (
              <div className="pt-4 border-t border-purple-200">
                {!graphragStatus?.ready && (graphragStatus?.input_documents ?? 0) > 0 && !isIndexing && !graphragStatus?.is_indexing && (
                  <button
                    onClick={handleStartGraphragIndex}
                    className="w-full py-3 px-5 rounded-lg bg-purple-600 text-white text-lg font-medium hover:bg-purple-700 transition-colors"
                  >
                    🚀 Build Knowledge Graph
                  </button>
                )}
                {(isIndexing || graphragStatus?.is_indexing) && (
                  <div className="space-y-4">
                    {/* Progress Bar */}
                    <div className="w-full bg-purple-200 rounded-full h-4 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-purple-500 to-purple-600 h-4 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${graphragStatus?.progress_detail?.percentage ?? 0}%` }}
                      />
                    </div>
                    
                    {/* Progress Details */}
                    <div className="flex items-center justify-between text-base">
                      <span className="text-purple-700 font-semibold text-lg">
                        {graphragStatus?.progress_detail?.percentage ?? 0}%
                      </span>
                      {graphragStatus?.progress_detail?.eta_minutes !== null && graphragStatus?.progress_detail?.eta_minutes !== undefined && (
                        <span className="text-purple-600 font-medium">
                          ~{graphragStatus.progress_detail.eta_minutes} min remaining
                        </span>
                      )}
                    </div>
                    
                    {/* Current Step */}
                    {graphragStatus?.progress_detail?.current_step && (
                      <div className="text-sm text-purple-600 bg-white/50 rounded-lg p-3">
                        <div className="flex items-center gap-3">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="font-medium">
                            {graphragStatus.progress_detail.current_step.replace(/_/g, ' ')}
                          </span>
                          {graphragStatus.progress_detail.total_items > 0 && (
                            <span className="text-purple-500">
                              ({graphragStatus.progress_detail.current_progress}/{graphragStatus.progress_detail.total_items})
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Steps Progress */}
                    {graphragStatus?.progress_detail?.steps_completed && graphragStatus.progress_detail.steps_completed.length > 0 && (
                      <div className="text-sm text-purple-500">
                        ✅ {graphragStatus.progress_detail.steps_completed.length}/10 steps completed
                      </div>
                    )}
                  </div>
                )}
                {(graphragStatus?.input_documents ?? 0) === 0 && (
                  <p className="text-base text-purple-500 text-center py-3">Upload documents to enable</p>
                )}
              </div>
            )}
            <div className="flex items-center justify-between pt-3">
              <p className="text-sm text-purple-500">Powered by Microsoft GraphRAG</p>
              {graphragStatus?.ready && (
                <button
                  onClick={async () => {
                    setShowTokenUsage(true)
                    if (!tokenUsage) {
                      setLoadingTokenUsage(true)
                      try {
                        const resp = await graphragApi.getTokenUsage()
                        setTokenUsage(resp.token_usage)
                      } catch (e) {
                        console.error('Failed to fetch token usage:', e)
                      } finally {
                        setLoadingTokenUsage(false)
                      }
                    }
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-purple-700 bg-white/70 hover:bg-white rounded-lg transition-colors border border-purple-200"
                >
                  <BarChart3 className="h-4 w-4" />
                  Token Usage
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Token Usage Modal */}
      {showTokenUsage && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowTokenUsage(false)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b bg-gradient-to-r from-purple-50 to-purple-100">
              <div className="flex items-center gap-3">
                <BarChart3 className="h-6 w-6 text-purple-700" />
                <h3 className="text-xl font-semibold text-purple-900">GraphRAG Indexing Token Usage</h3>
              </div>
              <button onClick={() => setShowTokenUsage(false)} className="p-2 hover:bg-purple-200 rounded-lg transition-colors">
                <X className="h-5 w-5 text-purple-600" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto max-h-[calc(85vh-80px)]">
              {loadingTokenUsage ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
                  <span className="ml-3 text-purple-600">Scanning cache files...</span>
                </div>
              ) : tokenUsage ? (
                <div className="space-y-6">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                      <div className="text-sm text-blue-600 font-medium">🧠 LLM Tokens</div>
                      <div className="text-2xl font-bold text-blue-900 mt-1">{tokenUsage.totals.llm_total_tokens.toLocaleString()}</div>
                      <div className="text-xs text-blue-500 mt-1">
                        {tokenUsage.totals.llm_calls.toLocaleString()} calls • 
                        Prompt: {tokenUsage.totals.llm_prompt_tokens.toLocaleString()} • 
                        Completion: {tokenUsage.totals.llm_completion_tokens.toLocaleString()}
                      </div>
                    </div>
                    <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                      <div className="text-sm text-emerald-600 font-medium">📐 Embedding Tokens</div>
                      <div className="text-2xl font-bold text-emerald-900 mt-1">{tokenUsage.totals.embedding_tokens.toLocaleString()}</div>
                      <div className="text-xs text-emerald-500 mt-1">
                        {tokenUsage.totals.embedding_calls.toLocaleString()} calls
                      </div>
                    </div>
                  </div>

                  {/* Grand Total */}
                  <div className="p-4 rounded-xl bg-purple-50 border border-purple-200 text-center">
                    <div className="text-sm text-purple-600 font-medium">Grand Total</div>
                    <div className="text-3xl font-bold text-purple-900">{tokenUsage.totals.grand_total_tokens.toLocaleString()}</div>
                  </div>

                  {/* Category Breakdown */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-3">LLM Usage by Phase</h4>
                    <div className="space-y-2">
                      {Object.entries(tokenUsage.categories)
                        .filter(([key]) => key !== 'text_embedding')
                        .map(([key, cat]) => (
                          <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div>
                              <span className="font-medium text-gray-800">{key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                              <span className="text-xs text-gray-500 ml-2">({cat.calls.toLocaleString()} calls)</span>
                            </div>
                            <span className="font-semibold text-gray-900">{cat.total_tokens.toLocaleString()}</span>
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Per-Document Table */}
                  {tokenUsage.per_document.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Estimated Usage Per Document</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="text-left py-2 px-3 text-gray-600 font-medium">Document</th>
                              <th className="text-right py-2 px-3 text-gray-600 font-medium">Chunks</th>
                              <th className="text-right py-2 px-3 text-blue-600 font-medium">LLM Tokens</th>
                              <th className="text-right py-2 px-3 text-emerald-600 font-medium">Embed Tokens</th>
                              <th className="text-right py-2 px-3 text-purple-600 font-medium">Total</th>
                            </tr>
                          </thead>
                          <tbody>
                            {tokenUsage.per_document.map((doc, i) => (
                              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="py-2 px-3 truncate max-w-[200px]" title={doc.title}>{doc.title}</td>
                                <td className="py-2 px-3 text-right text-gray-600">{doc.chunks}</td>
                                <td className="py-2 px-3 text-right text-blue-700">{doc.estimated_llm_tokens.toLocaleString()}</td>
                                <td className="py-2 px-3 text-right text-emerald-700">{doc.estimated_embedding_tokens.toLocaleString()}</td>
                                <td className="py-2 px-3 text-right font-semibold text-purple-700">{doc.estimated_total_tokens.toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="text-xs text-gray-400 mt-2 italic">* Per-document values are proportional estimates based on chunk count</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">No token usage data available</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* GraphRAG Index Checkbox */}
      <div className="mb-6 flex items-center gap-4 p-4 bg-muted/30 rounded-lg">
        <input
          type="checkbox"
          id="enable-graphrag"
          checked={enableGraphragIndex}
          onChange={(e) => setEnableGraphragIndex(e.target.checked)}
          className="h-6 w-6 rounded border-muted-foreground/25"
        />
        <label htmlFor="enable-graphrag" className="text-base text-muted-foreground cursor-pointer">
          <span className="font-medium">Enable GraphRAG indexing</span> — automatically builds knowledge graph for cross-document reasoning
        </label>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
          ${uploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />
        <Upload className="h-12 w-12 mx-auto mb-5 text-muted-foreground" />
        {isDragActive ? (
          <p className="text-primary text-lg">Drop files here...</p>
        ) : uploading ? (
          <>
            <p className="text-muted-foreground text-lg flex items-center justify-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Uploading files...
            </p>
          </>
        ) : (
          <>
            <p className="text-muted-foreground text-lg">
              Drag & drop files here, or click to browse
            </p>
            <p className="text-base text-muted-foreground/75 mt-2">
              Supports PDF, DOCX, XLSX, PPTX • <span className="font-medium">Multiple files supported</span>
            </p>
          </>
        )}
      </div>

      {/* Uploaded Documents */}
      {documents.length > 0 && (
        <div className="mt-6 space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-4 rounded-lg bg-muted/50"
            >
              <div className="flex items-center gap-4">
                <File className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-base font-medium">{doc.filename}</p>
                  {doc.status === 'completed' && (
                    <p className="text-sm text-muted-foreground">
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
