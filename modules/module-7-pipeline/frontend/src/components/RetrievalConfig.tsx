import { Settings, RotateCcw, Shield, Search, Network, Sparkles } from 'lucide-react'
import type { QueryConfig } from '../types'

interface RetrievalConfigProps {
  config: QueryConfig
  onChange: (config: Partial<QueryConfig>) => void
}

// Recommended min_score values based on search mode
const getRecommendedMinScore = (searchMode: string, semanticRanker: boolean): number => {
  switch (searchMode) {
    case 'vector':
      return 0.8
    case 'semantic':
      return 2.5
    case 'hybrid':
      return semanticRanker ? 2.0 : 0
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
  const handleReset = () => {
    onChange({
      // AI Search defaults
      top_k: 5,
      search_mode: 'hybrid',
      semantic_ranker: true,
      min_score: 2.0,
      content_type_filter: 'all',
      // General defaults
      retrieval_strategy: 'iterative',
      enable_validation: true,
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
  const isGraphRAGSelected = config.retrieval_strategy === 'graphrag'
  const isAISearchSelected = config.retrieval_strategy !== 'graphrag'

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
              <option value="graphrag">GraphRAG (Knowledge Graph)</option>
            </select>
            <p className="text-sm text-muted-foreground mt-2">
              {config.retrieval_strategy === 'auto' && '🎯 System will choose the best strategy based on your question'}
              {config.retrieval_strategy === 'hybrid' && '🔍 Uses Azure AI Search with vector + text search'}
              {config.retrieval_strategy === 'iterative' && '🔄 Entity extraction + iterative query refinement'}
              {config.retrieval_strategy === 'agentic' && '🤖 AI Agent with query decomposition & tool calls'}
              {config.retrieval_strategy === 'graphrag' && '🕸️ Graph-based retrieval for relationship questions'}
            </p>
          </div>

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
                Select GraphRAG strategy to enable
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
              <option value="drift">DRIFT (Best Quality)</option>
              <option value="local">Local (Entity-Centric)</option>
              <option value="global">Global (Community Summaries)</option>
            </select>
            <p className="text-sm text-muted-foreground mt-2">
              {config.graphrag_mode === 'drift' && '🎯 Combines local + global for highest quality answers'}
              {config.graphrag_mode === 'local' && '🔍 Finds entity → follows relationships → gathers context'}
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
