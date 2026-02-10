import { useState } from 'react'
import { ChevronDown, ChevronRight, Activity, Zap, Clock, Target, GitBranch, Search, Tag, Coins, Timer } from 'lucide-react'
import { QueryFlowchart } from './QueryFlowchart'
import type { RetrievalMetadata, QueryResponse } from '../types'

interface RetrievalDetailsProps {
  metadata: RetrievalMetadata
  response?: QueryResponse
}

function formatTime(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = (seconds % 60).toFixed(0)
  return `${minutes}m ${remainingSeconds}s`
}

export function RetrievalDetails({ metadata, response }: RetrievalDetailsProps) {
  const [expanded, setExpanded] = useState(false)
  const [showFlowchart, setShowFlowchart] = useState(false)
  const [showActivityLog, setShowActivityLog] = useState(false)
  const [showIterativeTrace, setShowIterativeTrace] = useState(true)

  const hasAgenticData = metadata.query_decomposition || metadata.multi_hop_trace
  const hasIterativeData = metadata.iterative_trace

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
            <p className="text-sm font-medium capitalize">
              {metadata.strategy_used}
              {metadata.strategy_used === 'combined' && metadata.parameters.combined_base_strategy && (
                <span className="text-xs text-muted-foreground ml-1">
                  ({metadata.parameters.combined_base_strategy})
                </span>
              )}
            </p>
            {(metadata.strategy_used === 'combined' || metadata.strategy_used === 'graphrag') && (
              <p className="text-xs text-violet-500 font-medium capitalize">
                GraphRAG: {metadata.parameters.graphrag_mode || 'local'}
              </p>
            )}
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
            <p className="text-xs text-muted-foreground">
              {hasIterativeData ? 'Iterations' : 'Sub-queries'}
            </p>
            <p className="text-sm font-medium">
              {hasIterativeData 
                ? metadata.iterative_trace?.total_iterations 
                : (metadata.query_decomposition?.sub_queries.length || 1)}
            </p>
          </div>
        </div>
      </div>

      {/* Always-Visible Parameter Badges */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {/* AI Search params */}
        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-700 dark:text-blue-300 border border-blue-500/20">
          🔍 {metadata.parameters.search_mode}{metadata.parameters.semantic_ranker ? ' + semantic' : ''}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-700 dark:text-blue-300 border border-blue-500/20">
          top_k: {metadata.parameters.top_k}
        </span>
        {metadata.parameters.content_type_filter && metadata.parameters.content_type_filter !== 'all' && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20">
            filter: {metadata.parameters.content_type_filter}
          </span>
        )}
        {metadata.parameters.min_score > 0 && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20">
            min_score: {metadata.parameters.min_score}
          </span>
        )}
        {/* GraphRAG params (when applicable) */}
        {(metadata.strategy_used === 'combined' || metadata.strategy_used === 'graphrag') && (
          <>
            <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/20">
              GraphRAG: {metadata.parameters.graphrag_mode || 'local'}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/20">
              community: {metadata.parameters.graphrag_community_level ?? 2}
            </span>
          </>
        )}
        {metadata.strategy_used === 'combined' && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
            base: {metadata.parameters.combined_base_strategy || 'iterative'}
          </span>
        )}
        {/* Combined timing breakdown */}
        {response?.combined_results && (
          <>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400">
              Search: {formatTime(response.combined_results.search_time_ms)}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-600 dark:text-violet-400">
              GraphRAG: {formatTime(response.combined_results.graphrag_time_ms)}
            </span>
          </>
        )}
      </div>

      {/* Tokens & Timing Summary */}
      {response && (
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="flex items-center gap-2">
            <Timer className="h-4 w-4 text-orange-500" />
            <div>
              <p className="text-xs text-muted-foreground">Total Time</p>
              <p className="text-sm font-medium">{formatTime(response.timing?.total_time_ms ?? metadata.retrieval_time_ms)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-500" />
            <div>
              <p className="text-xs text-muted-foreground">Generation</p>
              <p className="text-sm font-medium">{formatTime(response.timing?.generation_time_ms ?? 0)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Coins className="h-4 w-4 text-amber-500" />
            <div>
              <p className="text-xs text-muted-foreground">
                {response.generation_metadata?.graphrag_tokens?.total_tokens ? 'Gen Tokens' : 'Tokens Used'}
              </p>
              <p className="text-sm font-medium">{(response.generation_metadata?.tokens_used ?? 0).toLocaleString()}</p>
            </div>
          </div>
          {response.generation_metadata?.graphrag_tokens?.total_tokens ? (
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-violet-500" />
              <div>
                <p className="text-xs text-muted-foreground">GraphRAG Tokens</p>
                <p className="text-sm font-medium">
                  {response.generation_metadata.graphrag_tokens.total_tokens.toLocaleString()}
                  <span className="text-xs text-muted-foreground ml-1">
                    ({response.generation_metadata.graphrag_tokens.llm_calls} calls)
                  </span>
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-cyan-500" />
              <div>
                <p className="text-xs text-muted-foreground">Prompt / Completion</p>
                <p className="text-sm font-medium">
                  {(response.generation_metadata?.prompt_tokens ?? 0).toLocaleString()}
                  {' / '}
                  {(response.generation_metadata?.completion_tokens ?? 0).toLocaleString()}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* GraphRAG Token Breakdown (shown when GraphRAG tokens exist) */}
      {response?.generation_metadata?.graphrag_tokens?.total_tokens ? (
        <div className="mt-2 flex gap-3 text-xs text-muted-foreground pl-1">
          <span>
            Gen: {(response.generation_metadata.prompt_tokens ?? 0).toLocaleString()}↑ / {(response.generation_metadata.completion_tokens ?? 0).toLocaleString()}↓
          </span>
          <span className="text-border">|</span>
          <span>
            GraphRAG: {response.generation_metadata.graphrag_tokens.prompt_tokens.toLocaleString()}↑ / {response.generation_metadata.graphrag_tokens.completion_tokens.toLocaleString()}↓
          </span>
          <span className="text-border">|</span>
          <span className="font-medium text-foreground">
            Total: {((response.generation_metadata?.tokens_used ?? 0) + response.generation_metadata.graphrag_tokens.total_tokens).toLocaleString()}
          </span>
        </div>
      ) : null}

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
                <span className="text-muted-foreground">Search Mode:</span>{' '}
                <span className="font-medium">{metadata.parameters.search_mode}</span>
              </div>
              <div className="p-2 rounded bg-muted/50">
                <span className="text-muted-foreground">Semantic:</span>{' '}
                <span className="font-medium">
                  {metadata.parameters.semantic_ranker ? 'On' : 'Off'}
                </span>
              </div>
              {metadata.parameters.content_type_filter && metadata.parameters.content_type_filter !== 'all' && (
                <div className="p-2 rounded bg-muted/50">
                  <span className="text-muted-foreground">Content Filter:</span>{' '}
                  <span className="font-medium capitalize">{metadata.parameters.content_type_filter}</span>
                </div>
              )}
              {metadata.parameters.min_score > 0 && (
                <div className="p-2 rounded bg-muted/50">
                  <span className="text-muted-foreground">Min Score:</span>{' '}
                  <span className="font-medium">{metadata.parameters.min_score}</span>
                </div>
              )}
            </div>

            {/* Strategy Details */}
            {(metadata.strategy_used === 'combined' || metadata.strategy_used === 'graphrag') && (
              <div className="mt-2">
                <h4 className="text-xs font-semibold text-muted-foreground mb-1">Strategy Configuration</h4>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  {metadata.strategy_used === 'combined' && (
                    <div className="p-2 rounded bg-violet-500/10 border border-violet-500/20">
                      <span className="text-muted-foreground">Base Strategy:</span>{' '}
                      <span className="font-medium capitalize">{metadata.parameters.combined_base_strategy || 'iterative'}</span>
                    </div>
                  )}
                  <div className="p-2 rounded bg-violet-500/10 border border-violet-500/20">
                    <span className="text-muted-foreground">GraphRAG Mode:</span>{' '}
                    <span className="font-medium capitalize">{metadata.parameters.graphrag_mode || 'local'}</span>
                  </div>
                  <div className="p-2 rounded bg-violet-500/10 border border-violet-500/20">
                    <span className="text-muted-foreground">Community Level:</span>{' '}
                    <span className="font-medium">{metadata.parameters.graphrag_community_level ?? 2}</span>
                  </div>
                  <div className="p-2 rounded bg-violet-500/10 border border-violet-500/20">
                    <span className="text-muted-foreground">Response Type:</span>{' '}
                    <span className="font-medium">{metadata.parameters.graphrag_response_type || 'Multiple Paragraphs'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Iterative Trace (NEW!) */}
          {hasIterativeData && (
            <div className="border rounded-lg p-3 bg-gradient-to-r from-purple-500/10 to-blue-500/10">
              <button
                onClick={() => setShowIterativeTrace(!showIterativeTrace)}
                className="flex items-center gap-2 text-sm font-semibold mb-2 w-full"
              >
                {showIterativeTrace ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                <Search className="h-4 w-4 text-purple-500" />
                Iterative Entity-Aware Retrieval
              </button>
              
              {showIterativeTrace && metadata.iterative_trace && (
                <div className="space-y-3">
                  {/* Entities Found */}
                  {Object.keys(metadata.iterative_trace.all_entities).length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                        <Tag className="h-3 w-3" />
                        Extracted Entities
                      </h4>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(metadata.iterative_trace.all_entities).map(([key, value]) => (
                          <span key={key} className="text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-700 dark:text-purple-300">
                            <span className="font-medium">{key}:</span> {value}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Aspects Coverage */}
                  <div className="flex gap-4">
                    {metadata.iterative_trace.aspects_covered.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-green-600 mb-1">✓ Covered</h4>
                        <div className="flex flex-wrap gap-1">
                          {metadata.iterative_trace.aspects_covered.map((aspect, idx) => (
                            <span key={idx} className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-700 dark:text-green-300">
                              {aspect}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {metadata.iterative_trace.aspects_missing.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-orange-600 mb-1">○ Still Missing</h4>
                        <div className="flex flex-wrap gap-1">
                          {metadata.iterative_trace.aspects_missing.map((aspect, idx) => (
                            <span key={idx} className="text-xs px-2 py-0.5 rounded bg-orange-500/20 text-orange-700 dark:text-orange-300">
                              {aspect}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Iteration Steps */}
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground mb-2">Iteration Steps</h4>
                    <div className="space-y-2">
                      {metadata.iterative_trace.steps.map((step) => (
                        <div key={step.iteration} className="p-2 rounded bg-muted/50 text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-blue-600">
                              Iteration {step.iteration}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {step.results_count} results
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground mb-1">
                            {step.reasoning}
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {step.search_queries.map((q, idx) => (
                              <span key={idx} className="text-xs px-2 py-0.5 rounded bg-blue-500/20">
                                🔍 {q}
                              </span>
                            ))}
                          </div>
                          {Object.keys(step.entities_found).length > 0 && (
                            <div className="mt-1 text-xs text-purple-600">
                              Found: {Object.entries(step.entities_found).map(([k, v]) => `${k}="${v}"`).join(', ')}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

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
