import { useState, useCallback, useRef, useEffect } from 'react'
import { RepoInput } from './components/RepoInput'
import { RepoStatusPanel } from './components/RepoStatusPanel'
import { QueryInput } from './components/QueryInput'
import { AnswerDisplay } from './components/AnswerDisplay'
import { RetrievalDetails } from './components/RetrievalDetails'
import { RetrievalConfig } from './components/RetrievalConfig'
import { RepoSelector } from './components/RepoSelector'
import { SystemControls } from './components/SystemControls'
import { executeQuery, getRepoStatus } from './services/api'
import type { QueryResponse, QueryConfig, RepoStatus } from './types'
import { Github } from 'lucide-react'

const DEFAULT_CONFIG: QueryConfig = {
  top_k: 25,
  search_mode: 'semantic',
  min_score: 0,
  content_type_filter: 'all',
  language_filter: 'all',
  retrieval_strategy: 'combined',
  graphrag_mode: 'local',
  graphrag_community_level: 2,
  graphrag_response_type: 'Multiple Paragraphs',
}

function App() {
  const [activeRepo, setActiveRepo] = useState<{ owner: string; name: string } | null>(null)
  const [repoStatus, setRepoStatus] = useState<RepoStatus | null>(null)
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [config, setConfig] = useState<QueryConfig>(DEFAULT_CONFIG)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Poll repo status while indexing
  useEffect(() => {
    if (!activeRepo) return
    if (repoStatus && (repoStatus.status === 'complete' || repoStatus.status === 'error' || repoStatus.status === 'not_indexed')) return

    const poll = async () => {
      try {
        const s = await getRepoStatus(activeRepo.owner, activeRepo.name)
        setRepoStatus(s)
        if (s.status === 'complete' || s.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch { /* ignore */ }
    }

    pollRef.current = setInterval(poll, 2000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [activeRepo, repoStatus?.status])

  const handleSelectRepo = useCallback(async (owner: string, name: string) => {
    if (!owner || !name) {
      setActiveRepo(null)
      setRepoStatus(null)
      setQueryResponse(null)
      return
    }
    setActiveRepo({ owner, name })
    setQueryResponse(null)
    try {
      const s = await getRepoStatus(owner, name)
      setRepoStatus(s)
    } catch {
      setRepoStatus({ repo_full_name: `${owner}/${name}`, status: 'complete', progress: 1, message: 'Ready', files_count: 0, chunks_count: 0, index_name: '' })
    }
  }, [])

  const handleRepoIndexed = useCallback((owner: string, name: string) => {
    setActiveRepo({ owner, name })
    setRepoStatus({ repo_full_name: `${owner}/${name}`, status: 'pending', progress: 0, message: 'Starting...', files_count: 0, chunks_count: 0, index_name: '' })
    setQueryResponse(null)
  }, [])

  const handleRepoReady = useCallback((status: RepoStatus) => {
    setRepoStatus(status)
  }, [])

  const handleQuery = useCallback(async (question: string) => {
    if (!activeRepo) return
    setIsLoading(true)
    try {
      const response = await executeQuery(question, activeRepo.owner, activeRepo.name, config)
      setQueryResponse(response)
    } catch (err: any) {
      setQueryResponse({
        answer: `Error: ${err?.response?.data?.detail || err.message}`,
        sources: [],
        retrieval_metadata: { strategy_used: 'error', total_chunks: 0, retrieval_time_ms: 0, parameters: {} },
        generation_metadata: { model: '', tokens_used: 0, prompt_tokens: 0, completion_tokens: 0 },
        timing: { total_time_ms: 0, retrieval_time_ms: 0, generation_time_ms: 0 },
      })
    } finally {
      setIsLoading(false)
    }
  }, [activeRepo, config])

  const handleSyncStarted = useCallback(() => {
    if (!activeRepo) return
    // Reset status to trigger polling
    setRepoStatus({
      repo_full_name: `${activeRepo.owner}/${activeRepo.name}`,
      status: 'pending',
      progress: 0,
      message: 'Syncing with remote...',
      files_count: 0,
      chunks_count: 0,
      index_name: '',
    })
    setQueryResponse(null)
  }, [activeRepo])

  const isRepoReady = repoStatus?.status === 'complete'

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center gap-3">
          <Github className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">GitHub RAG</h1>
            <p className="text-sm text-muted-foreground">Chat with any repository · Azure AI Search + GraphRAG</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <RepoSelector activeRepo={activeRepo} onSelect={handleSelectRepo} />
            <SystemControls />
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: main flow */}
          <div className="lg:col-span-2 space-y-6">
            <RepoInput onIndexed={handleRepoIndexed} onReady={handleRepoReady} />

            {repoStatus && <RepoStatusPanel status={repoStatus} onSyncStarted={handleSyncStarted} />}

            {isRepoReady && (
              <>
                <QueryInput onSubmit={handleQuery} isLoading={isLoading} />
                {queryResponse && <AnswerDisplay response={queryResponse} />}
                {queryResponse && queryResponse.sources.length > 0 && (
                  <RetrievalDetails response={queryResponse} />
                )}
              </>
            )}
          </div>

          {/* Right: config */}
          <div className="space-y-6">
            <RetrievalConfig config={config} onChange={setConfig} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-4 text-center text-sm text-muted-foreground">
        RAG Workshop · Module 8 · GitHub Repository RAG
      </footer>
    </div>
  )
}

export default App
