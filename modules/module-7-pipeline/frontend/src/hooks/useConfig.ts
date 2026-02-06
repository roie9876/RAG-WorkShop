import { useState, useEffect, useCallback } from 'react'
import { configApi } from '../services/api'
import type { QueryConfig } from '../types'

const DEFAULT_CONFIG: QueryConfig = {
  // AI Search parameters
  top_k: 5,
  search_mode: 'hybrid',
  semantic_ranker: true,
  min_score: 2.0,
  content_type_filter: 'all',
  // General settings
  retrieval_strategy: 'iterative',
  enable_validation: true,
  // GraphRAG parameters
  graphrag_mode: 'local',
  graphrag_community_level: 2,
  graphrag_response_type: 'Multiple Paragraphs',
}

export function useConfig() {
  const [config, setConfig] = useState<QueryConfig>(DEFAULT_CONFIG)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    // Load initial config from server
    const loadConfig = async () => {
      try {
        const response = await configApi.get()
        setConfig(response.query)
      } catch {
        // Use defaults if server unavailable
        setConfig(DEFAULT_CONFIG)
      }
    }
    loadConfig()
  }, [])

  const updateConfig = useCallback(async (newConfig: QueryConfig) => {
    setIsLoading(true)
    try {
      const updated = await configApi.update(newConfig)
      setConfig(updated)
    } catch {
      // Update locally anyway
      setConfig(newConfig)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const resetConfig = useCallback(async () => {
    setIsLoading(true)
    try {
      const reset = await configApi.reset()
      setConfig(reset)
    } catch {
      setConfig(DEFAULT_CONFIG)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    config,
    updateConfig,
    resetConfig,
    isLoading,
  }
}
