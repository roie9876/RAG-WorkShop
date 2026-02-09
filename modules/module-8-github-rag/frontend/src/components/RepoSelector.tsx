import { useState, useEffect, useCallback } from 'react'
import { listRepos, deleteRepo } from '../services/api'

interface IndexedRepo {
  repo_owner: string
  repo_name: string
  last_sync_timestamp?: string
  indexed_files_count?: number
  total_chunks?: number
  index_name?: string
}

interface Props {
  activeRepo: { owner: string; name: string } | null
  onSelect: (owner: string, name: string) => void
}

export function RepoSelector({ activeRepo, onSelect }: Props) {
  const [repos, setRepos] = useState<IndexedRepo[]>([])
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  const fetchRepos = useCallback(async () => {
    setLoading(true)
    try {
      const { repos: list } = await listRepos()
      setRepos(list as IndexedRepo[])
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  // Refresh list on mount and whenever it opens
  useEffect(() => {
    fetchRepos()
  }, [fetchRepos])

  useEffect(() => {
    if (isOpen) fetchRepos()
  }, [isOpen, fetchRepos])

  const handleSelect = (repo: IndexedRepo) => {
    onSelect(repo.repo_owner, repo.repo_name)
    setIsOpen(false)
  }

  const handleDelete = async (e: React.MouseEvent, repo: IndexedRepo) => {
    e.stopPropagation()
    if (!confirm(`Delete index for ${repo.repo_owner}/${repo.repo_name}?\n\nThis will remove the Azure AI Search index and GraphRAG data.`)) return
    try {
      await deleteRepo(repo.repo_owner, repo.repo_name)
      fetchRepos()
      // If we deleted the active repo, clear it
      if (activeRepo?.owner === repo.repo_owner && activeRepo?.name === repo.repo_name) {
        onSelect('', '') // signal to parent to clear
      }
    } catch (err) {
      console.error('Failed to delete repo:', err)
    }
  }

  const activeLabel = activeRepo ? `${activeRepo.owner}/${activeRepo.name}` : 'Select repository'
  const otherRepos = repos.filter(
    (r) => !(r.repo_owner === activeRepo?.owner && r.repo_name === activeRepo?.name),
  )

  if (repos.length === 0 && !loading) return null

  return (
    <div className="relative">
      {/* Selector button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-card hover:bg-muted transition-colors text-sm max-w-xs"
        title="Switch repository"
      >
        <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
        <span className="font-mono truncate">{activeLabel}</span>
        <svg className={`h-4 w-4 text-gray-400 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
        {repos.length > 1 && (
          <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
            {repos.length}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-1 w-96 bg-card border rounded-xl shadow-lg z-50 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-2.5 bg-muted/50 border-b flex items-center justify-between">
              <h3 className="font-semibold text-sm">📦 Indexed Repositories ({repos.length})</h3>
              <button onClick={() => { fetchRepos() }} className="text-xs text-blue-600 hover:underline">
                Refresh
              </button>
            </div>

            {loading ? (
              <div className="p-4 text-center text-sm text-muted-foreground">Loading...</div>
            ) : repos.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                No repositories indexed yet. Paste a URL above to get started.
              </div>
            ) : (
              <div className="max-h-72 overflow-y-auto">
                {repos.map((repo) => {
                  const isActive = repo.repo_owner === activeRepo?.owner && repo.repo_name === activeRepo?.name
                  return (
                    <div
                      key={`${repo.repo_owner}/${repo.repo_name}`}
                      onClick={() => handleSelect(repo)}
                      className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors border-b last:border-b-0 ${
                        isActive ? 'bg-blue-50 border-l-2 border-l-blue-500' : 'hover:bg-muted/50'
                      }`}
                    >
                      {/* Active indicator */}
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isActive ? 'bg-blue-500' : 'bg-gray-300'}`} />

                      {/* Repo info */}
                      <div className="flex-1 min-w-0">
                        <div className="font-mono text-sm font-medium truncate">
                          {repo.repo_owner}/{repo.repo_name}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                          {repo.indexed_files_count != null && (
                            <span>📄 {repo.indexed_files_count} files</span>
                          )}
                          {repo.total_chunks != null && (
                            <span>🧩 {repo.total_chunks} chunks</span>
                          )}
                          {repo.last_sync_timestamp && (
                            <span>🕐 {new Date(repo.last_sync_timestamp).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>

                      {/* Delete button */}
                      <button
                        onClick={(e) => handleDelete(e, repo)}
                        className="p-1.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-600 transition-colors flex-shrink-0"
                        title="Delete index"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
