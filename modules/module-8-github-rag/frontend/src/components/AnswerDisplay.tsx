import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { QueryResponse } from '../types'
import { Clock, Zap, Brain } from 'lucide-react'

interface Props {
  response: QueryResponse
}

export function AnswerDisplay({ response }: Props) {
  const { timing, retrieval_metadata, generation_metadata } = response

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-3">Answer</h2>

      {/* Answer body */}
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{response.answer}</ReactMarkdown>
      </div>

      {/* Metadata bar */}
      <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {timing.total_time_ms}ms total
        </span>
        <span className="flex items-center gap-1">
          <Zap className="w-3 h-3" />
          {timing.retrieval_time_ms}ms retrieval
        </span>
        <span className="flex items-center gap-1">
          <Brain className="w-3 h-3" />
          {generation_metadata.tokens_used} tokens
        </span>
        <span>Strategy: {retrieval_metadata.strategy_used}</span>
        <span>{retrieval_metadata.total_chunks} chunks</span>
      </div>

      {/* Combined results (GraphRAG answer) */}
      {response.combined_results?.graphrag_response && (
        <details className="mt-4">
          <summary className="text-sm font-medium cursor-pointer text-muted-foreground hover:text-foreground">
            GraphRAG Knowledge Graph Answer
          </summary>
          <div className="mt-2 p-3 bg-muted rounded-md text-sm prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{response.combined_results.graphrag_response}</ReactMarkdown>
          </div>
        </details>
      )}
    </div>
  )
}
