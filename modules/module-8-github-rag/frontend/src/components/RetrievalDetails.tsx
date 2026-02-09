import { useState } from 'react'
import type { QueryResponse, SourceChunk } from '../types'
import { FileCode, ChevronDown, ChevronRight } from 'lucide-react'

interface Props {
  response: QueryResponse
}

const TYPE_COLORS: Record<string, string> = {
  code: 'bg-blue-100 text-blue-800',
  docs: 'bg-green-100 text-green-800',
  config: 'bg-yellow-100 text-yellow-800',
  ci: 'bg-purple-100 text-purple-800',
  metadata: 'bg-gray-100 text-gray-800',
  entity: 'bg-orange-100 text-orange-800',
  relationship: 'bg-pink-100 text-pink-800',
  graphrag_answer: 'bg-indigo-100 text-indigo-800',
}

export function RetrievalDetails({ response }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <FileCode className="w-5 h-5" />
        Retrieved Sources ({response.sources.length})
      </h2>

      <div className="space-y-2">
        {response.sources.map((chunk, i) => (
          <ChunkItem
            key={chunk.id || i}
            chunk={chunk}
            index={i + 1}
            isExpanded={expandedId === chunk.id}
            onToggle={() => setExpandedId(expandedId === chunk.id ? null : chunk.id)}
          />
        ))}
      </div>
    </div>
  )
}

function ChunkItem({ chunk, index, isExpanded, onToggle }: {
  chunk: SourceChunk
  index: number
  isExpanded: boolean
  onToggle: () => void
}) {
  const colorClass = TYPE_COLORS[chunk.content_type] || 'bg-gray-100 text-gray-800'

  return (
    <div className="border rounded-md">
      <button onClick={onToggle} className="w-full flex items-center gap-2 p-3 text-left hover:bg-muted/50">
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <span className="text-xs font-mono text-muted-foreground w-6">[{index}]</span>
        <span className={`text-xs px-1.5 py-0.5 rounded ${colorClass}`}>{chunk.content_type}</span>
        {chunk.language && <span className="text-xs text-muted-foreground">{chunk.language}</span>}
        <span className="text-sm font-mono truncate flex-1">{chunk.file_path}</span>
        {chunk.relevance_score > 0 && (
          <span className="text-xs text-muted-foreground">{chunk.relevance_score.toFixed(3)}</span>
        )}
      </button>

      {isExpanded && (
        <div className="p-3 border-t bg-muted/30">
          {chunk.section_header && chunk.section_header !== chunk.file_path && (
            <p className="text-xs text-muted-foreground mb-2">Section: {chunk.section_header}</p>
          )}
          {chunk.parent_class && (
            <p className="text-xs text-muted-foreground mb-2">Class: {chunk.parent_class}</p>
          )}
          <pre className="text-xs overflow-x-auto whitespace-pre-wrap font-mono bg-background p-3 rounded">
            {chunk.content}
          </pre>
        </div>
      )}
    </div>
  )
}
