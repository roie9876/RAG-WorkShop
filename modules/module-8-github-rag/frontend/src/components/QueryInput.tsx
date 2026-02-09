import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'

interface Props {
  onSubmit: (question: string) => void
  isLoading: boolean
}

export function QueryInput({ onSubmit, isLoading }: Props) {
  const [question, setQuestion] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || isLoading) return
    onSubmit(question.trim())
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <Search className="w-5 h-5" />
        Ask a Question
      </h2>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="How does authentication work? · What modules depend on X? · Describe the architecture..."
          className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !question.trim()}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Ask
        </button>
      </form>
    </div>
  )
}
