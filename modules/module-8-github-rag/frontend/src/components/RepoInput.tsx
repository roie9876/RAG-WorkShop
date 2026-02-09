import { useState } from 'react'
import { indexRepo } from '../services/api'
import type { RepoStatus } from '../types'
import { Github, Loader2, ArrowRight } from 'lucide-react'

interface Props {
  onIndexed: (owner: string, name: string) => void
  onReady: (status: RepoStatus) => void
}

export function RepoInput({ onIndexed, onReady }: Props) {
  const [url, setUrl] = useState('')
  const [enableGraphrag, setEnableGraphrag] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setIsSubmitting(true)
    setError('')

    try {
      const result = await indexRepo(url.trim(), enableGraphrag)

      // Parse owner/name from the response or URL
      const fullName = result.repo_full_name || ''
      const [owner, name] = fullName.split('/')

      if (result.status === 'already_indexed') {
        onReady({
          repo_full_name: fullName,
          status: 'complete',
          progress: 1,
          message: `Already indexed (${result.indexed_files} files, ${result.total_chunks} chunks)`,
          files_count: result.indexed_files || 0,
          chunks_count: result.total_chunks || 0,
          index_name: result.index_name || '',
        })
        onIndexed(owner, name)
      } else {
        onIndexed(owner, name)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to index repository')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <Github className="w-5 h-5" />
        <h2 className="text-lg font-semibold">Index a Repository</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo  or  owner/repo"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            disabled={isSubmitting}
          />
          <button
            type="submit"
            disabled={isSubmitting || !url.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
            Index
          </button>
        </div>

        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={enableGraphrag}
            onChange={e => setEnableGraphrag(e.target.checked)}
            className="rounded"
          />
          Enable GraphRAG (knowledge graph – recommended but takes longer)
        </label>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </form>
    </div>
  )
}
