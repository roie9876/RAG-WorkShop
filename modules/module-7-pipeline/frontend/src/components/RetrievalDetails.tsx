import { useState } from 'react'
import { ChevronDown, ChevronRight, Activity, Zap, Clock, Target, GitBranch } from 'lucide-react'
import { QueryFlowchart } from './QueryFlowchart'
import type { RetrievalMetadata } from '../types'

interface RetrievalDetailsProps {
  metadata: RetrievalMetadata
}

export function RetrievalDetails({ metadata }: RetrievalDetailsProps) {
  const [expanded, setExpanded] = useState(false)
  const [showFlowchart, setShowFlowchart] = useState(false)
  const [showActivityLog, setShowActivityLog] = useState(false)

  const hasAgenticData = metadata.query_decomposition || metadata.multi_hop_trace

  return (
    <div className="rounded-lg border bg-card p-4">
      {/* Header with Summary */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between"
      >
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Retrieval Details
        </h2>
        {expanded ? (
          <ChevronDown className="h-5 w-5" />
        ) : (
          <ChevronRight className="h-5 w-5" />
        )}
      </button>

      {/* Always Visible Summary */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-yellow-500" />
          <div>
            <p className="text-xs text-muted-foreground">Strategy</p>
            <p className="text-sm font-medium capitalize">{metadata.strategy_used}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-blue-500" />
          <div>
            <p className="text-xs text-muted-foreground">Chunks</p>
            <p className="text-sm font-medium">{metadata.total_chunks_retrieved}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-green-500" />
          <div>
            <p className="text-xs text-muted-foreground">Time</p>
            <p className="text-sm font-medium">{metadata.retrieval_time_ms}ms</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-purple-500" />
          <div>
            <p className="text-xs text-muted-foreground">Sub-queries</p>
            <p className="text-sm font-medium">
              {metadata.query_decomposition?.sub_queries.length || 1}
            </p>
          </div>
        </div>
      </div>

      {/* Content Type Distribution */}
      <div className="mt-4 flex gap-2">
        {Object.entries(metadata.content_type_distribution).map(([type, count]) => (
          <span
            key={type}
            className="text-xs px-2 py-1 rounded-full bg-muted"
          >
            {type}: {count}
          </span>
        ))}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-4 pt-4 border-t space-y-4">
          {/* Parameters Used */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Parameters Used</h3>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div className="p-2 rounded bg-muted/50">
                <span className="text-muted-foreground">Top K:</span>{' '}
                <span className="font-medium">{metadata.parameters.top_k}</span>
              </div>
              <div className="p-2 rounded bg-muted/50">
                <span className="text-muted-foreground">Mode:</span>{' '}
                <span className="font-medium">{metadata.parameters.search_mode}</span>
              </div>
              <div className="p-2 rounded bg-muted/50">
                <span className="text-muted-foreground">Semantic:</span>{' '}
                <span className="font-medium">
                  {metadata.parameters.semantic_ranker ? 'On' : 'Off'}
                </span>
              </div>
            </div>
          </div>

          {/* Query Decomposition (Agentic) */}
          {hasAgenticData && (
            <div>
              <button
                onClick={() => setShowFlowchart(!showFlowchart)}
                className="flex items-center gap-2 text-sm font-semibold mb-2"
              >
                {showFlowchart ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                Query Decomposition Flowchart
              </button>
              {showFlowchart && (
                <div className="h-64 border rounded-lg bg-muted/30">
                  <QueryFlowchart
                    decomposition={metadata.query_decomposition}
                    multiHopTrace={metadata.multi_hop_trace}
                  />
                </div>
              )}
            </div>
          )}

          {/* Sub-queries List */}
          {metadata.query_decomposition && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Sub-queries</h3>
              <div className="space-y-2">
                {metadata.query_decomposition.sub_queries.map((sq, idx) => (
                  <div key={idx} className="p-2 rounded bg-muted/50 text-sm">
                    <span className="font-medium">{idx + 1}.</span> {sq.query}
                    <span className="text-muted-foreground ml-2">
                      ({sq.results_count} results)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Activity Log */}
          {metadata.activity_log && metadata.activity_log.length > 0 && (
            <div>
              <button
                onClick={() => setShowActivityLog(!showActivityLog)}
                className="flex items-center gap-2 text-sm font-semibold mb-2"
              >
                {showActivityLog ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                Activity Log ({metadata.activity_log.length} steps)
              </button>
              {showActivityLog && (
                <div className="max-h-48 overflow-auto">
                  <pre className="text-xs p-3 rounded bg-muted/50 overflow-x-auto">
                    {JSON.stringify(metadata.activity_log, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
