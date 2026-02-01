import { useState, useRef, useEffect } from 'react'
import { Search, Loader2 } from 'lucide-react'

interface QueryInputProps {
  onSubmit: (question: string) => void
  isLoading: boolean
}

export function QueryInput({ onSubmit, isLoading }: QueryInputProps) {
  const [question, setQuestion] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Detect RTL text
  const isRTL = /[\u0590-\u05FF\u0600-\u06FF]/.test(question)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [question])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (question.trim() && !isLoading) {
      onSubmit(question.trim())
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
        <Search className="h-6 w-6" />
        Ask a Question
      </h2>

      <form onSubmit={handleSubmit}>
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="What would you like to know about your documents?"
            className={`
              w-full min-h-[100px] max-h-[250px] p-5 pr-14 text-lg
              rounded-lg border bg-background
              resize-none focus:outline-none focus:ring-2 focus:ring-primary
              ${isRTL ? 'text-right' : 'text-left'}
            `}
            dir={isRTL ? 'rtl' : 'ltr'}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!question.trim() || isLoading}
            className={`
              absolute bottom-4 right-4 p-3 rounded-lg
              bg-primary text-primary-foreground
              disabled:opacity-50 disabled:cursor-not-allowed
              hover:bg-primary/90 transition-colors
            `}
          >
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <Search className="h-6 w-6" />
            )}
          </button>
        </div>

        <div className="mt-3 flex justify-between items-center text-sm text-muted-foreground">
          <span>Press Enter to submit, Shift+Enter for new line</span>
          {isRTL && <span>RTL mode detected</span>}
        </div>
      </form>
    </div>
  )
}
