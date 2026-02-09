import { useState, useEffect, useCallback } from 'react'
import type { RepoStatus, SyncStatus } from '../types'
import { CheckCircle2, XCircle, Loader2, GitBranch, FileCode, Layers } from 'lucide-react'
import { getSyncStatus, syncRepo, indexRepo } from '../services/api'

interface Props {
  status: RepoStatus
  onSyncStarted?: () => void
}

const STAGE_LABELS: Record<string, string> = {
  pending: 'Queued',
  cloning: 'Cloning repository',
  chunking: 'Chunking files',
  embedding: 'Generating embeddings',
  indexing: 'Uploading to AI Search',
  graphrag: 'Building knowledge graph',
  complete: 'Ready',
  error: 'Error',
}

export function RepoStatusPanel({ status, onSyncStarted }: Props) {
  const isInProgress = !['complete', 'error', 'not_indexed'].includes(status.status)
  const pct = Math.round(status.progress * 100)

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [syncChecking, setSyncChecking] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [reindexing, setReindexing] = useState(false)

  // Parse owner/name from full_name
  const [owner, name] = status.repo_full_name.split('/')

  const checkSync = useCallback(async () => {
    if (!owner || !name || status.status !== 'complete') return
    setSyncChecking(true)
    try {
      const s = await getSyncStatus(owner, name)
      setSyncStatus(s)
    } catch {
      setSyncStatus(null)
    } finally {
      setSyncChecking(false)
    }
  }, [owner, name, status.status])

  // Auto-check sync status when repo becomes complete
  useEffect(() => {
    if (status.status === 'complete') {
      checkSync()
    } else {
      setSyncStatus(null)
    }
  }, [status.status, checkSync])

  const handleSync = async (rebuildGraphrag: boolean) => {
    if (!owner || !name) return
    setSyncing(true)
    try {
      const repoUrl = `https://github.com/${owner}/${name}`
      await syncRepo(repoUrl, rebuildGraphrag)
      onSyncStarted?.()
    } catch (err: any) {
      alert(`Sync failed: ${err?.response?.data?.detail || err.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleReindex = async () => {
    if (!owner || !name) return
    if (!confirm(`🔄 Re-index ${owner}/${name}?\n\nThis will re-clone, re-chunk, re-embed, and rebuild the entire index.\nUseful after improving chunking or embedding logic.`)) return
    setReindexing(true)
    try {
      const repoUrl = `https://github.com/${owner}/${name}`
      await indexRepo(repoUrl, true, true)
      onSyncStarted?.()
    } catch (err: any) {
      alert(`Re-index failed: ${err?.response?.data?.detail || err.message}`)
    } finally {
      setReindexing(false)
    }
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {status.status === 'complete' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
          {status.status === 'error' && <XCircle className="w-5 h-5 text-destructive" />}
          {isInProgress && <Loader2 className="w-5 h-5 animate-spin text-primary" />}
          <span className="font-medium">{status.repo_full_name}</span>
        </div>
        <span className="text-sm text-muted-foreground">{STAGE_LABELS[status.status] || status.status}</span>
      </div>

      {isInProgress && (
        <div className="w-full bg-muted rounded-full h-2 mb-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <p className="text-sm text-muted-foreground">{status.message}</p>

      {(status.files_count > 0 || status.chunks_count > 0) && (
        <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1"><FileCode className="w-3 h-3" /> {status.files_count} files</span>
          <span className="flex items-center gap-1"><Layers className="w-3 h-3" /> {status.chunks_count} chunks</span>
          {status.index_name && <span className="flex items-center gap-1"><GitBranch className="w-3 h-3" /> {status.index_name}</span>}
        </div>
      )}

      {status.error && (
        <p className="text-sm text-destructive mt-2">{status.error}</p>
      )}

      {/* Sync section — only when repo is ready */}
      {status.status === 'complete' && (
        <div className="mt-3 pt-3 border-t">
          <div className="flex items-center justify-between">
            {/* Sync status indicator */}
            <div className="flex items-center gap-2 text-sm">
              {syncChecking ? (
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Checking for updates...
                </span>
              ) : syncStatus?.status === 'up_to_date' ? (
                <span className="flex items-center gap-1.5 text-green-600">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Up to date
                  {syncStatus.last_sync && (
                    <span className="text-xs text-muted-foreground ml-1">
                      · synced {new Date(syncStatus.last_sync).toLocaleString()}
                    </span>
                  )}
                </span>
              ) : syncStatus?.status === 'behind' ? (
                <span className="flex items-center gap-1.5 text-orange-600">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Updates available
                  <span className="text-xs text-muted-foreground">
                    ({syncStatus.indexed_commit?.slice(0, 7)} → {syncStatus.remote_commit?.slice(0, 7)})
                  </span>
                </span>
              ) : syncStatus?.status === 'error' ? (
                <span className="flex items-center gap-1.5 text-red-600 text-xs">
                  <XCircle className="w-3.5 h-3.5" />
                  {syncStatus.message}
                </span>
              ) : null}
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleReindex}
                disabled={reindexing || syncing}
                className="text-xs px-3 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
                title="Re-clone, re-chunk, re-embed, and rebuild the full index + GraphRAG"
              >
                {reindexing ? (
                  <><Loader2 className="w-3 h-3 animate-spin" /> Re-indexing...</>
                ) : (
                  '🔁 Re-index'
                )}
              </button>

              <button
                onClick={checkSync}
                disabled={syncChecking || syncing}
                className="text-xs px-2 py-1 rounded hover:bg-muted transition-colors text-muted-foreground disabled:opacity-50"
                title="Check for updates"
              >
                🔍 Check
              </button>

              {syncStatus?.status === 'behind' && (
                <>
                  <button
                    onClick={() => handleSync(false)}
                    disabled={syncing}
                    className="text-xs px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
                  >
                    {syncing ? (
                      <><Loader2 className="w-3 h-3 animate-spin" /> Syncing...</>
                    ) : (
                      '🔄 Sync Index'
                    )}
                  </button>
                  <button
                    onClick={() => handleSync(true)}
                    disabled={syncing}
                    className="text-xs px-3 py-1.5 rounded-lg bg-orange-50 hover:bg-orange-100 text-orange-700 font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
                    title="Re-index and rebuild GraphRAG knowledge graph"
                  >
                    🔄 Sync + GraphRAG
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
