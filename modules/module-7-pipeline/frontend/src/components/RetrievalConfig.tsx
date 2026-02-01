import { Settings, RotateCcw, Shield } from 'lucide-react'
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
      top_k: 5,
      search_mode: 'hybrid',
      semantic_ranker: true,
      min_score: 2.0,
      content_type_filter: 'all',
      retrieval_strategy: 'iterative',
      enable_validation: true,
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

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Retrieval Config
        </h2>
        <button
          onClick={handleReset}
          className="p-1 hover:bg-muted rounded transition-colors"
          title="Reset to defaults"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Top K */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium">Top K</label>
            <span className="text-sm text-muted-foreground">{config.top_k}</span>
          </div>
          <input
            type="range"
            min="1"
            max="20"
            value={config.top_k}
            onChange={(e) => onChange({ top_k: parseInt(e.target.value) })}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>1</span>
            <span>20</span>
          </div>
        </div>

        {/* Search Mode */}
        <div>
          <label className="text-sm font-medium block mb-2">Search Mode</label>
          <select
            value={config.search_mode}
            onChange={(e) => handleSearchModeChange(e.target.value as QueryConfig['search_mode'])}
            className="w-full p-2 rounded-lg border bg-background"
          >
            <option value="hybrid">Hybrid (Vector + Text)</option>
            <option value="vector">Vector Only</option>
            <option value="text">Text Only (BM25)</option>
            <option value="semantic">Semantic</option>
          </select>
        </div>

        {/* Semantic Ranker */}
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Semantic Ranker</label>
          <button
            onClick={handleSemanticRankerChange}
            className={`
              relative w-11 h-6 rounded-full transition-colors
              ${config.semantic_ranker ? 'bg-primary' : 'bg-muted'}
            `}
          >
            <span
              className={`
                absolute top-1 left-1 w-4 h-4 rounded-full bg-white
                transition-transform
                ${config.semantic_ranker ? 'translate-x-5' : 'translate-x-0'}
              `}
            />
          </button>
        </div>

        {/* Min Score */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium">Min Score</label>
            <span className="text-sm text-muted-foreground">
              {config.min_score.toFixed(1)}
              {isSemanticScoring && <span className="text-xs ml-1">(semantic 0-4)</span>}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max={maxScore}
            step={scoreStep}
            value={config.min_score}
            onChange={(e) => onChange({ min_score: parseFloat(e.target.value) })}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>0</span>
            <span>{maxScore}</span>
          </div>
          {isSemanticScoring && (
            <p className="text-xs text-muted-foreground mt-1">
              Semantic: 0-1 poor, 1-2 fair, 2-3 good, 3-4 excellent
            </p>
          )}
        </div>

        {/* Content Type Filter */}
        <div>
          <label className="text-sm font-medium block mb-2">Content Filter</label>
          <select
            value={config.content_type_filter}
            onChange={(e) => onChange({ content_type_filter: e.target.value as QueryConfig['content_type_filter'] })}
            className="w-full p-2 rounded-lg border bg-background"
          >
            <option value="all">All Content</option>
            <option value="text">Text Only</option>
            <option value="table">Tables Only</option>
            <option value="figure">Figures Only</option>
          </select>
        </div>

        {/* Retrieval Strategy */}
        <div>
          <label className="text-sm font-medium block mb-2">Strategy</label>
          <select
            value={config.retrieval_strategy}
            onChange={(e) => onChange({ retrieval_strategy: e.target.value as QueryConfig['retrieval_strategy'] })}
            className="w-full p-2 rounded-lg border bg-background"
          >
            <option value="auto">Auto (Recommended)</option>
            <option value="hybrid">Hybrid</option>
            <option value="iterative">Iterative (Entity-Aware)</option>
            <option value="agentic">Agentic</option>
            <option value="graphrag">GraphRAG</option>
          </select>
          <p className="text-xs text-muted-foreground mt-1">
            {config.retrieval_strategy === 'auto' && 'System will choose the best strategy'}
            {config.retrieval_strategy === 'hybrid' && 'Standard vector + text search'}
            {config.retrieval_strategy === 'iterative' && 'Entity extraction + query rewriting loop'}
            {config.retrieval_strategy === 'agentic' && 'AI Agent with query decomposition'}
            {config.retrieval_strategy === 'graphrag' && 'Graph-based for relationships'}
          </p>
        </div>

        {/* Answer Validation */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-500" />
            <label className="text-sm font-medium">Answer Validation</label>
          </div>
          <button
            onClick={() => onChange({ enable_validation: !config.enable_validation })}
            className={`
              relative w-11 h-6 rounded-full transition-colors
              ${config.enable_validation ? 'bg-green-500' : 'bg-muted'}
            `}
          >
            <span
              className={`
                absolute top-1 left-1 w-4 h-4 rounded-full bg-white
                transition-transform
                ${config.enable_validation ? 'translate-x-5' : 'translate-x-0'}
              `}
            />
          </button>
        </div>
        <p className="text-xs text-muted-foreground">
          Filter irrelevant chunks & validate answer quality
        </p>
      </div>
    </div>
  )
}
