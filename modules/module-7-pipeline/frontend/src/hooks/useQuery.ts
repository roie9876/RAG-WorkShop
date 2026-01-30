import { useState, useCallback } from 'react'
import { queryApi } from '../services/api'
import type { QueryConfig, QueryResponse } from '../types'

export function useQuery() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const executeQuery = useCallback(
    async (question: string, config: QueryConfig): Promise<QueryResponse> => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await queryApi.execute(question, config)
        return response
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Query failed'
        setError(message)
        throw err
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  return {
    executeQuery,
    isLoading,
    error,
  }
}
