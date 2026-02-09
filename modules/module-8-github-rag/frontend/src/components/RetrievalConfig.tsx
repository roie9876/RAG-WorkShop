import type { QueryConfig } from '../types'
import { Settings } from 'lucide-react'

interface Props {
  config: QueryConfig
  onChange: (config: QueryConfig) => void
}

export function RetrievalConfig({ config, onChange }: Props) {
  const update = (partial: Partial<QueryConfig>) => onChange({ ...config, ...partial })

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Settings className="w-5 h-5" />
        Retrieval Configuration
      </h2>

      <div className="space-y-4 text-sm">
        {/* Strategy */}
        <div>
          <label className="font-medium block mb-1">Strategy</label>
          <select
            value={config.retrieval_strategy}
            onChange={e => update({ retrieval_strategy: e.target.value as QueryConfig['retrieval_strategy'] })}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="combined">Combined (AI Search + GraphRAG)</option>
            <option value="hybrid">Hybrid (AI Search only)</option>
            <option value="graphrag">GraphRAG (Knowledge Graph only)</option>
            <option value="auto">Auto-classify</option>
          </select>
        </div>

        {/* Search mode */}
        <div>
          <label className="font-medium block mb-1">Search Mode</label>
          <select
            value={config.search_mode}
            onChange={e => update({ search_mode: e.target.value as QueryConfig['search_mode'] })}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="semantic">Semantic (vector + keyword + reranker)</option>
            <option value="hybrid">Hybrid (vector + keyword)</option>
            <option value="vector">Vector only</option>
            <option value="text">Text/keyword only</option>
          </select>
        </div>

        {/* Top K */}
        <div>
          <label className="font-medium block mb-1">Top K: {config.top_k}</label>
          <input
            type="range"
            min={1}
            max={50}
            value={config.top_k}
            onChange={e => update({ top_k: Number(e.target.value) })}
            className="w-full"
          />
        </div>

        {/* Content type filter */}
        <div>
          <label className="font-medium block mb-1">Content Type</label>
          <select
            value={config.content_type_filter}
            onChange={e => update({ content_type_filter: e.target.value as QueryConfig['content_type_filter'] })}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="all">All</option>
            <option value="code">Code</option>
            <option value="docs">Documentation</option>
            <option value="config">Configuration</option>
            <option value="ci">CI/CD</option>
            <option value="metadata">Metadata</option>
          </select>
        </div>

        {/* Language filter */}
        <div>
          <label className="font-medium block mb-1">Language</label>
          <input
            type="text"
            value={config.language_filter}
            onChange={e => update({ language_filter: e.target.value })}
            placeholder="all, python, typescript, ..."
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </div>

        {/* Min score */}
        <div>
          <label className="font-medium block mb-1">Min Score: {config.min_score}</label>
          <input
            type="range"
            min={0}
            max={4}
            step={0.1}
            value={config.min_score}
            onChange={e => update({ min_score: Number(e.target.value) })}
            className="w-full"
          />
        </div>

        {/* GraphRAG settings */}
        {(config.retrieval_strategy === 'graphrag' || config.retrieval_strategy === 'combined') && (
          <div className="border-t pt-4 space-y-3">
            <p className="font-medium text-muted-foreground">GraphRAG Settings</p>

            <div>
              <label className="font-medium block mb-1">Mode</label>
              <select
                value={config.graphrag_mode}
                onChange={e => update({ graphrag_mode: e.target.value as QueryConfig['graphrag_mode'] })}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              >
                <option value="local">Local (entity-focused)</option>
                <option value="global">Global (community summaries)</option>
                <option value="drift">Drift (local + global)</option>
              </select>
            </div>

            <div>
              <label className="font-medium block mb-1">Community Level: {config.graphrag_community_level}</label>
              <input
                type="range"
                min={0}
                max={5}
                value={config.graphrag_community_level}
                onChange={e => update({ graphrag_community_level: Number(e.target.value) })}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">0 = specific entities, 5 = broad communities</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
