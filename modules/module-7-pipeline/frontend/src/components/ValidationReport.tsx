import { useState } from 'react'
import { 
  ChevronDown, 
  ChevronRight, 
  Shield, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Filter,
  Target,
  RefreshCw
} from 'lucide-react'
import type { ValidationReport } from '../types'

interface ValidationReportProps {
  report: ValidationReport
  onRetry?: (query: string) => void
}

export function ValidationReportPanel({ report, onRetry }: ValidationReportProps) {
  const [expanded, setExpanded] = useState(true)
  const [showFilteredChunks, setShowFilteredChunks] = useState(false)
  const [showChunkValidations, setShowChunkValidations] = useState(false)

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getConfidenceColor = (confidence: string) => {
    if (confidence === 'high') return 'bg-green-500/20 text-green-700'
    if (confidence === 'medium') return 'bg-yellow-500/20 text-yellow-700'
    return 'bg-red-500/20 text-red-700'
  }

  return (
    <div className={`rounded-lg border p-4 ${report.validation_passed ? 'bg-green-500/5 border-green-500/20' : 'bg-orange-500/5 border-orange-500/20'}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between"
      >
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Shield className={`h-5 w-5 ${report.validation_passed ? 'text-green-500' : 'text-orange-500'}`} />
          Answer Validation
          {report.validation_passed ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          )}
        </h2>
        {expanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
      </button>

      {/* Summary Stats */}
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-2 rounded bg-muted/50">
          <p className="text-xs text-muted-foreground">Overall Score</p>
          <p className={`text-lg font-bold ${getScoreColor(report.overall_score)}`}>
            {report.overall_score.toFixed(0)}%
          </p>
        </div>
        <div className="p-2 rounded bg-muted/50">
          <p className="text-xs text-muted-foreground">Chunks Filtered</p>
          <p className="text-lg font-bold">
            {report.chunks_filtered}/{report.total_chunks_retrieved}
          </p>
        </div>
        {report.answer_quality && (
          <>
            <div className="p-2 rounded bg-muted/50">
              <p className="text-xs text-muted-foreground">Completeness</p>
              <p className={`text-lg font-bold ${getScoreColor(report.answer_quality.completeness_score)}`}>
                {report.answer_quality.completeness_score.toFixed(0)}%
              </p>
            </div>
            <div className="p-2 rounded bg-muted/50">
              <p className="text-xs text-muted-foreground">Confidence</p>
              <span className={`text-sm px-2 py-0.5 rounded ${getConfidenceColor(report.answer_quality.confidence)}`}>
                {report.answer_quality.confidence}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-4 space-y-4">
          {/* Warnings */}
          {report.warnings.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-orange-500" />
                Warnings
              </h3>
              <div className="space-y-1">
                {report.warnings.map((warning, idx) => (
                  <div key={idx} className="text-sm p-2 rounded bg-orange-500/10 text-orange-700 dark:text-orange-300">
                    {warning}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filtered Chunks */}
          {report.chunks_filtered > 0 && (
            <div>
              <button
                onClick={() => setShowFilteredChunks(!showFilteredChunks)}
                className="flex items-center gap-2 text-sm font-semibold"
              >
                {showFilteredChunks ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                <Filter className="h-4 w-4 text-red-500" />
                Filtered Chunks ({report.chunks_filtered})
              </button>
              {showFilteredChunks && (
                <div className="mt-2 space-y-2 max-h-48 overflow-auto">
                  {report.filtered_chunks.map((fc) => (
                    <div key={fc.chunk_id} className="p-2 rounded bg-red-500/10 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs">{fc.chunk_id}</span>
                        {fc.entity_conflict && (
                          <span className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-700">
                            Entity Conflict
                          </span>
                        )}
                      </div>
                      <p className="text-muted-foreground text-xs mt-1">{fc.reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Answer Quality Details */}
          {report.answer_quality && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Target className="h-4 w-4 text-blue-500" />
                Answer Quality Analysis
              </h3>

              {/* Grounding Check */}
              <div className="flex items-center gap-2">
                {report.answer_quality.is_grounded ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
                <span className="text-sm">
                  {report.answer_quality.is_grounded 
                    ? 'Answer is grounded in source chunks' 
                    : 'Answer may contain unsupported claims'}
                </span>
              </div>

              {/* Aspects Covered */}
              {report.answer_quality.aspects_answered.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-green-600 mb-1">✓ Aspects Answered</h4>
                  <div className="flex flex-wrap gap-1">
                    {report.answer_quality.aspects_answered.map((aspect, idx) => (
                      <span key={idx} className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-700">
                        {aspect}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Aspects Missing */}
              {report.answer_quality.aspects_missing.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-orange-600 mb-1">○ Aspects Missing</h4>
                  <div className="flex flex-wrap gap-1">
                    {report.answer_quality.aspects_missing.map((aspect, idx) => (
                      <span key={idx} className="text-xs px-2 py-0.5 rounded bg-orange-500/20 text-orange-700">
                        {aspect}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Issues */}
              {report.answer_quality.issues.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-red-600 mb-1">Issues Found</h4>
                  <div className="space-y-1">
                    {report.answer_quality.issues.map((issue, idx) => (
                      <div 
                        key={idx} 
                        className={`text-xs p-2 rounded ${
                          issue.severity === 'error' ? 'bg-red-500/10 text-red-700' : 'bg-yellow-500/10 text-yellow-700'
                        }`}
                      >
                        <span className="font-semibold">{issue.type}:</span> {issue.description}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {report.answer_quality.recommendations.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-blue-600 mb-1">Recommendations</h4>
                  <ul className="text-xs space-y-1 text-muted-foreground">
                    {report.answer_quality.recommendations.map((rec, idx) => (
                      <li key={idx}>• {rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Retry Suggestion */}
          {report.retry_suggested && report.retry_query && onRetry && (
            <div className="p-3 rounded bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-700">Suggested Retry Query</p>
                  <p className="text-xs text-blue-600 mt-1">{report.retry_query}</p>
                </div>
                <button
                  onClick={() => onRetry(report.retry_query!)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-blue-500 text-white text-sm hover:bg-blue-600 transition-colors"
                >
                  <RefreshCw className="h-4 w-4" />
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Chunk Validations (Collapsed by default) */}
          <div>
            <button
              onClick={() => setShowChunkValidations(!showChunkValidations)}
              className="flex items-center gap-2 text-sm font-semibold text-muted-foreground"
            >
              {showChunkValidations ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              All Chunk Validations ({report.chunk_validations.length})
            </button>
            {showChunkValidations && (
              <div className="mt-2 space-y-1 max-h-48 overflow-auto">
                {report.chunk_validations.map((cv) => (
                  <div 
                    key={cv.chunk_id} 
                    className={`p-2 rounded text-xs ${
                      cv.is_relevant && !cv.entity_conflict 
                        ? 'bg-green-500/10' 
                        : 'bg-red-500/10'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono">{cv.chunk_id}</span>
                      <div className="flex gap-2">
                        <span className={`px-1.5 py-0.5 rounded ${cv.is_relevant ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                          {(cv.relevance_score * 100).toFixed(0)}% relevant
                        </span>
                        {cv.entity_conflict && (
                          <span className="px-1.5 py-0.5 rounded bg-red-500/20">conflict</span>
                        )}
                      </div>
                    </div>
                    {cv.conflict_details && (
                      <p className="text-muted-foreground mt-1">{cv.conflict_details}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
