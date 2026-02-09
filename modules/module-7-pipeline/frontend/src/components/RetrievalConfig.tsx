import { useState, useEffect } from 'react'
import { Settings, RotateCcw, Shield, Search, Network, Sparkles, Database } from 'lucide-react'
import type { QueryConfig, IndexSummary } from '../types'
import { indexApi } from '../services/api'

interface RetrievalConfigProps {
  config: QueryConfig
  onChange: (config: Partial<QueryConfig>) => void
}

// Recommended min_score values based on search mode
// NOTE: Semantic ranker scores are 0-4, vector scores are 0-1
const getRecommendedMinScore = (searchMode: string, _semanticRanker: boolean): number => {
  switch (searchMode) {
    case 'vector':
      return 0  // Vector scores can be very low, don't filter by default
    case 'semantic':
      return 0  // Let semantic ranker do the ranking, don't pre-filter
    case 'hybrid':
      return 0  // Start with no filtering, user can increase if needed
    case 'text':
      return 0
    default:
      return 0
  }
}

// Get max score based on search mode
const getMaxScore = (searchMode: string, semanticRanker: boolean): number => {
  if (searchMode === 'semantic' || (searchMode === 'hybrid' && semanticRanker)) {
    return 4.0
  }
  if (searchMode === 'vector') {
    return 1.0
  }
  return 10.0 // BM25 can have higher scores
}

// Get step based on search mode
const getScoreStep = (searchMode: string, semanticRanker: boolean): number => {
  if (searchMode === 'semantic' || (searchMode === 'hybrid' && semanticRanker)) {
    return 0.5
  }
  return 0.1
}

export function RetrievalConfig({ config, onChange }: RetrievalConfigProps) {
  const [indexes, setIndexes] = useState<IndexSummary[]>([])
  const [indexError, setIndexError] = useState<string | null>(null)

  useEffect(() => {
    indexApi.listIndexes()
      .then((data) => {
        setIndexes(data)
        setIndexError(null)
      })
      .catch((err) => {
        console.error('Failed to fetch indexes:', err)
        setIndexError('Failed to load indexes')
        setIndexes([])
      })
  }, [])
  const handleReset = () => {
    onChange({
      // Target index (empty = server default)
      index_name: '',
      // AI Search defaults
      top_k: 26,
      search_mode: 'semantic',
      semantic_ranker: true,
      min_score: 0.0,
      content_type_filter: 'all',
      // General defaults
      retrieval_strategy: 'combined',
      enable_validation: true,
      // Combined defaults
      combined_base_strategy: 'iterative',
      // GraphRAG defaults
      graphrag_mode: 'drift',
      graphrag_community_level: 2,
      graphrag_response_type: 'Multiple Paragraphs',
    })
  }

  // Update min_score when search mode changes
  const handleSearchModeChange = (newMode: QueryConfig['search_mode']) => {
    const recommendedScore = getRecommendedMinScore(newMode, config.semantic_ranker)
    onChange({ 
      search_mode: newMode,
      min_score: recommendedScore
    })
  }

  // Update min_score when semantic ranker changes
  const handleSemanticRankerChange = () => {
    const newSemanticRanker = !config.semantic_ranker
    const recommendedScore = getRecommendedMinScore(config.search_mode, newSemanticRanker)
    onChange({ 
      semantic_ranker: newSemanticRanker,
      min_score: recommendedScore
    })
  }

  const maxScore = getMaxScore(config.search_mode, config.semantic_ranker)
  const scoreStep = getScoreStep(config.search_mode, config.semantic_ranker)
  const isSemanticScoring = config.search_mode === 'semantic' || (config.search_mode === 'hybrid' && config.semantic_ranker)
  const isGraphRAGSelected = config.retrieval_strategy === 'graphrag' || config.retrieval_strategy === 'combined'
  const isAISearchSelected = config.retrieval_strategy !== 'graphrag'
  const isCombinedSelected = config.retrieval_strategy === 'combined'

  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-3">
          <Settings className="h-6 w-6" />
          Retrieval Config
        </h2>
        <button
          onClick={handleReset}
          className="p-2 hover:bg-muted rounded transition-colors"
          title="Reset to defaults"
        >
          <RotateCcw className="h-5 w-5" />
        </button>
      </div>

      <div className="space-y-6">
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* GENERAL SETTINGS */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-lg font-semibold border-b pb-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            <span>General Settings</span>
          </div>

          {/* Target Search Index */}
          <div>
            <label className="text-base font-medium mb-3 flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              Target Search Index
              {indexes.length > 0 && (
                <span className="text-xs text-muted-foreground font-normal">
                  ({indexes.length} available)
                </span>
              )}
            </label>
            {indexError && (
              <p className="text-sm text-red-500 mb-2">⚠️ {indexError}</p>
            )}
            {indexes.length === 0 && !indexError && (
              <p className="text-sm text-yellow-500 mb-2">⏳ Loading indexes...</p>
            )}
            <div className="space-y-1.5 max-h-52 overflow-y-auto rounded-lg border p-2">
              {/* Default option */}
              <label
                className={`flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-colors ${
                  !config.index_name
                    ? 'bg-blue-500/15 border border-blue-500/40'
                    : 'hover:bg-muted border border-transparent'
                }`}
              >
                <input
                  type="radio"
                  name="target_index"
                  value=""
                  checked={!config.index_name}
                  onChange={() => onChange({ index_name: '' })}
                  className="accent-blue-500"
                />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium">module7-rag-index</span>
                  <span className="text-xs text-muted-foreground ml-2">(default)</span>
                </div>
              </label>
              {/* Dynamic indexes */}
              {indexes
                .filter((idx) => idx.name !== 'module7-rag-index')
                .map((idx) => (
                  <label
                    key={idx.name}
                    className={`flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-colors ${
                      config.index_name === idx.name
                        ? 'bg-blue-500/15 border border-blue-500/40'
                        : 'hover:bg-muted border border-transparent'
                    }`}
                  >
                    <input
                      type="radio"
                      name="target_index"
                      value={idx.name}
                      checked={config.index_name === idx.name}
                      onChange={() => onChange({ index_name: idx.name })}
                      className="accent-blue-500"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium truncate">{idx.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        {idx.document_count} docs
                      </span>
                    </div>
                  </label>
                ))}
            </div>
            {config.index_name && (
              <p className="text-sm text-blue-500 mt-2">
                🎯 Queries will target: <strong>{config.index_name}</strong>
              </p>
            )}
          </div>

          {/* Retrieval Strategy */}
          <div>
            <label className="text-base font-medium block mb-3">Retrieval Strategy</label>
            <select
              value={config.retrieval_strategy}
              onChange={(e) => onChange({ retrieval_strategy: e.target.value as QueryConfig['retrieval_strategy'] })}
              className="w-full p-3 rounded-lg border bg-background text-base"
            >
              <option value="auto">Auto (Recommended)</option>
              <option value="hybrid">Hybrid (AI Search)</option>
              <option value="iterative">Iterative (Entity-Aware)</option>
              <option value="agentic">Agentic (AI Agent)</option>
              <option value="agentic_search">Agentic Search (Azure Native)</option>
              <option value="graphrag">GraphRAG (Knowledge Graph)</option>
              <option value="combined">Combined (AI Search + GraphRAG)</option>
            </select>
            <p className="text-sm text-muted-foreground mt-2">
              {config.retrieval_strategy === 'auto' && '🎯 System will choose the best strategy based on your question'}
              {config.retrieval_strategy === 'hybrid' && '🔍 Uses Azure AI Search with vector + text search'}
              {config.retrieval_strategy === 'iterative' && '🔄 Entity extraction + iterative query refinement'}
              {config.retrieval_strategy === 'agentic' && '🤖 AI Agent with query decomposition & tool calls'}
              {config.retrieval_strategy === 'agentic_search' && '⚡ Azure AI Search native multi-query (requires S1+ tier)'}
              {config.retrieval_strategy === 'graphrag' && '🕸️ Graph-based retrieval for relationship questions'}
              {config.retrieval_strategy === 'combined' && '🔀 Runs AI Search + GraphRAG in parallel, merges answers'}
            </p>
          </div>

          {/* Combined Base Strategy Picker */}
          {isCombinedSelected && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <label className="text-base font-medium block mb-2">AI Search Strategy (to combine with GraphRAG)</label>
              <select
                value={config.combined_base_strategy}
                onChange={(e) => onChange({ combined_base_strategy: e.target.value as QueryConfig['combined_base_strategy'] })}
                className="w-full p-3 rounded-lg border bg-background text-base"
              >
                <option value="hybrid">Hybrid (Vector + Text)</option>
                <option value="iterative">Iterative (Entity-Aware)</option>
                <option value="agentic">Agentic (AI Agent)</option>
                <option value="agentic_search">Agentic Search (Azure Native)</option>
              </select>
              <p className="text-sm text-amber-600 dark:text-amber-400 mt-2">
                🔀 This strategy will run in parallel with GraphRAG. Both answers shown before merge.
              </p>
            </div>
          )}

          {/* Answer Validation */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-green-500" />
              <label className="text-base font-medium">Answer Validation</label>
            </div>
            <button
              onClick={() => onChange({ enable_validation: !config.enable_validation })}
              className={`
                relative w-14 h-7 rounded-full transition-colors
                ${config.enable_validation ? 'bg-green-500' : 'bg-muted'}
              `}
            >
              <span
                className={`
                  absolute top-1 left-1 w-5 h-5 rounded-full bg-white
                  transition-transform
                  ${config.enable_validation ? 'translate-x-7' : 'translate-x-0'}
                `}
              />
            </button>
          </div>
          <p className="text-sm text-muted-foreground">
            Filter irrelevant chunks & validate answer quality
          </p>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* AZURE AI SEARCH PARAMETERS */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div className={`space-y-4 p-4 rounded-lg border-2 transition-all ${
          isAISearchSelected 
            ? 'border-blue-500 bg-blue-500/5' 
            : 'border-muted opacity-50'
        }`}>
          <div className="flex items-center gap-2 text-lg font-semibold">
            <Search className="h-5 w-5 text-blue-500" />
            <span>Azure AI Search Parameters</span>
            {!isAISearchSelected && (
              <span className="text-xs bg-muted px-2 py-1 rounded ml-auto">
                Not used with GraphRAG
              </span>
            )}
            {isCombinedSelected && (
              <span className="text-xs bg-amber-500/20 text-amber-600 px-2 py-1 rounded ml-auto">
                Combined mode
              </span>
            )}
          </div>
          
          {isAISearchSelected && (
            <p className="text-sm text-blue-600 dark:text-blue-400">
              These parameters control Azure AI Search retrieval (vector, text, hybrid, semantic modes)
            </p>
          )}

          {/* Top K */}
          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-base font-medium">Top K (Results)</label>
              <span className="text-base text-muted-foreground">{config.top_k}</span>
            </div>
            <input
              type="range"
              min="1"
              max="50"
              value={config.top_k}
              onChange={(e) => onChange({ top_k: parseInt(e.target.value) })}
              disabled={!isAISearchSelected}
              className="w-full h-3 bg-muted rounded-lg appearance-none cursor-pointer disabled:opacity-50"
            />
            <div className="flex justify-between text-sm text-muted-foreground mt-2">
              <span>1</span>
              <span>50</span>
            </div>
          </div>

          {/* Search Mode */}
          <div>
            <label className="text-base font-medium block mb-3">Search Mode</label>
            <select
              value={config.search_mode}
              onChange={(e) => handleSearchModeChange(e.target.value as QueryConfig['search_mode'])}
              disabled={!isAISearchSelected}
              className="w-full p-3 rounded-lg border bg-background text-base disabled:opacity-50"
            >
              <option value="hybrid">Hybrid (Vector + Text)</option>
              <option value="vector">Vector Only</option>
              <option value="text">Text Only (BM25)</option>
              <option value="semantic">Semantic</option>
            </select>
          </div>

          {/* Semantic Ranker */}
          <div className="flex items-center justify-between">
            <label className="text-base font-medium">Semantic Ranker (L2)</label>
            <button
              onClick={handleSemanticRankerChange}
              disabled={!isAISearchSelected}
              className={`
                relative w-14 h-7 rounded-full transition-colors disabled:opacity-50
                ${config.semantic_ranker ? 'bg-blue-500' : 'bg-muted'}
              `}
            >
              <span
                className={`
                  absolute top-1 left-1 w-5 h-5 rounded-full bg-white
                  transition-transform
                  ${config.semantic_ranker ? 'translate-x-7' : 'translate-x-0'}
                `}
              />
            </button>
          </div>

          {/* Min Score */}
          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-base font-medium">Min Score</label>
              <span className="text-base text-muted-foreground">
                {config.min_score.toFixed(1)}
                {isSemanticScoring && <span className="text-sm ml-1">(semantic 0-4)</span>}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max={maxScore}
              step={scoreStep}
              value={config.min_score}
              onChange={(e) => onChange({ min_score: parseFloat(e.target.value) })}
              disabled={!isAISearchSelected}
              className="w-full h-3 bg-muted rounded-lg appearance-none cursor-pointer disabled:opacity-50"
            />
            <div className="flex justify-between text-sm text-muted-foreground mt-2">
              <span>0</span>
              <span>{maxScore}</span>
            </div>
            {isSemanticScoring && isAISearchSelected && (
              <p className="text-sm text-muted-foreground mt-2">
                Semantic: 0-1 poor, 1-2 fair, 2-3 good, 3-4 excellent
              </p>
            )}
          </div>

          {/* Content Type Filter */}
          <div>
            <label className="text-base font-medium block mb-3">Content Filter</label>
            <select
              value={config.content_type_filter}
              onChange={(e) => onChange({ content_type_filter: e.target.value as QueryConfig['content_type_filter'] })}
              disabled={!isAISearchSelected}
              className="w-full p-3 rounded-lg border bg-background text-base disabled:opacity-50"
            >
              <option value="all">All Content</option>
              <option value="text">Text Only</option>
              <option value="table">Tables Only</option>
              <option value="figure">Figures Only</option>
            </select>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* GRAPHRAG PARAMETERS */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div className={`space-y-4 p-4 rounded-lg border-2 transition-all ${
          isGraphRAGSelected 
            ? 'border-purple-500 bg-purple-500/5' 
            : 'border-muted opacity-50'
        }`}>
          <div className="flex items-center gap-2 text-lg font-semibold">
            <Network className="h-5 w-5 text-purple-500" />
            <span>GraphRAG Parameters</span>
            {!isGraphRAGSelected && (
              <span className="text-xs bg-muted px-2 py-1 rounded ml-auto">
                Select GraphRAG or Combined strategy to enable
              </span>
            )}
            {isCombinedSelected && (
              <span className="text-xs bg-amber-500/20 text-amber-600 px-2 py-1 rounded ml-auto">
                Combined mode
              </span>
            )}
          </div>

          {isGraphRAGSelected && (
            <p className="text-sm text-purple-600 dark:text-purple-400">
              These parameters control graph-based retrieval (knowledge graph traversal)
            </p>
          )}

          {/* GraphRAG Mode */}
          <div>
            <label className="text-base font-medium block mb-3">Search Mode</label>
            <select
              value={config.graphrag_mode}
              onChange={(e) => onChange({ graphrag_mode: e.target.value as QueryConfig['graphrag_mode'] })}
              disabled={!isGraphRAGSelected}
              className="w-full p-3 rounded-lg border bg-background text-base disabled:opacity-50"
            >
              <option value="local">Local (Fast, Recommended)</option>
              <option value="drift">DRIFT (Deep Analysis, Slower)</option>
              <option value="global">Global (Community Summaries)</option>
            </select>
            <p className="text-sm text-muted-foreground mt-2">
              {config.graphrag_mode === 'local' && '⚡ Fast: finds entity → follows relationships → gathers context (~1 LLM call)'}
              {config.graphrag_mode === 'drift' && '🎯 Deep: combines local + global with iterative refinement (multiple LLM calls, slower)'}
              {config.graphrag_mode === 'global' && '🌍 Uses pre-computed community summaries for big-picture questions'}
            </p>
          </div>

          {/* Community Level */}
          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-base font-medium">Community Level</label>
              <span className="text-base text-muted-foreground">{config.graphrag_community_level}</span>
            </div>
            <input
              type="range"
              min="0"
              max="5"
              step="1"
              value={config.graphrag_community_level}
              onChange={(e) => onChange({ graphrag_community_level: parseInt(e.target.value) })}
              disabled={!isGraphRAGSelected}
              className="w-full h-3 bg-muted rounded-lg appearance-none cursor-pointer disabled:opacity-50"
            />
            <div className="flex justify-between text-sm text-muted-foreground mt-2">
              <span>0 (Specific)</span>
              <span>5 (Broad)</span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Lower = more specific entities, Higher = broader community context
            </p>
          </div>

          {/* Response Type */}
          <div>
            <label className="text-base font-medium block mb-3">Response Format</label>
            <select
              value={config.graphrag_response_type}
              onChange={(e) => onChange({ graphrag_response_type: e.target.value as QueryConfig['graphrag_response_type'] })}
              disabled={!isGraphRAGSelected}
              className="w-full p-3 rounded-lg border bg-background text-base disabled:opacity-50"
            >
              <option value="Multiple Paragraphs">Detailed (Multiple Paragraphs)</option>
              <option value="Single Paragraph">Concise (Single Paragraph)</option>
              <option value="Single Sentence">Brief (Single Sentence)</option>
              <option value="List of 3-7 Points">Bullet Points (3-7 items)</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
