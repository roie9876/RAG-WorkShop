import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FileText, Image, Table, ExternalLink, Combine, Search, Network, Sparkles } from 'lucide-react'
import type { QueryResponse, SourceChunk, CombinedResults } from '../types'

interface AnswerDisplayProps {
  response: QueryResponse
  isLoading: boolean
}

export function AnswerDisplay({ response, isLoading }: AnswerDisplayProps) {
  const isCombined = response.retrieval_metadata.strategy_used === 'combined' && response.combined_results

  if (isCombined && response.combined_results) {
    return <CombinedAnswerDisplay response={response} combinedResults={response.combined_results} />
  }

  return <StandardAnswerDisplay response={response} />
}

function StandardAnswerDisplay({ response }: { response: QueryResponse }) {
  // Detect RTL in answer
  const isRTL = /[\u0590-\u05FF\u0600-\u06FF]/.test(response.answer)
  const normalizedAnswer = response.answer.replace(/\[Source\s+(\d+)\]/g, '[$1]')
  const linkedAnswer = normalizedAnswer.replace(/\[(\d+)\]/g, '[$1](#source-$1)')

  const getContentIcon = (type: string) => {
    switch (type) {
      case 'figure':
        return <Image className="h-4 w-4" />
      case 'table':
        return <Table className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold mb-4">Answer</h2>

      {/* Main Answer */}
      <div
        className={`prose prose-sm max-w-none ${isRTL ? 'text-right' : 'text-left'}`}
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{linkedAnswer}</ReactMarkdown>
      </div>

      {/* Figures in Answer */}
      {response.sources
        .filter((s) => s.content_type === 'figure')
        .map((source) => (
          <FigureDisplay key={source.id} source={source} />
        ))}

      {/* Sources */}
      <SourcesList sources={response.sources} />
    </div>
  )
}

function CombinedAnswerDisplay({ response, combinedResults }: { response: QueryResponse; combinedResults: CombinedResults }) {
  const [activeTab, setActiveTab] = useState<'merged' | 'search' | 'graphrag'>('merged')

  const tabs = [
    { id: 'merged' as const, label: 'Merged Answer', icon: <Sparkles className="h-4 w-4" />, color: 'text-amber-500' },
    { id: 'search' as const, label: `AI Search (${combinedResults.search_strategy})`, icon: <Search className="h-4 w-4" />, color: 'text-blue-500' },
    { id: 'graphrag' as const, label: `GraphRAG (${combinedResults.graphrag_mode})`, icon: <Network className="h-4 w-4" />, color: 'text-purple-500' },
  ]

  const getActiveAnswer = () => {
    switch (activeTab) {
      case 'merged': return response.answer
      case 'search': return combinedResults.search_answer
      case 'graphrag': return combinedResults.graphrag_answer
    }
  }

  const getActiveSources = () => {
    switch (activeTab) {
      case 'merged': return response.sources
      case 'search': return combinedResults.search_sources
      case 'graphrag': return combinedResults.graphrag_sources
    }
  }

  const answer = getActiveAnswer()
  const sources = getActiveSources()
  const isRTL = /[\u0590-\u05FF\u0600-\u06FF]/.test(answer)
  const normalizedAnswer = answer.replace(/\[Source\s+(\d+)\]/g, '[$1]')
  const linkedAnswer = normalizedAnswer.replace(/\[(\d+)\]/g, '[$1](#source-$1)')

  return (
    <div className="rounded-lg border bg-card p-4">
      {/* Combined Header */}
      <div className="flex items-center gap-2 mb-4">
        <Combine className="h-5 w-5 text-amber-500" />
        <h2 className="text-lg font-semibold">Combined Answer</h2>
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Search className="h-3 w-3 text-blue-500" />
            {combinedResults.search_sources.length} chunks · {(combinedResults.search_time_ms / 1000).toFixed(1)}s
          </span>
          <span className="flex items-center gap-1">
            <Network className="h-3 w-3 text-purple-500" />
            {combinedResults.graphrag_sources.length} chunks · {(combinedResults.graphrag_time_ms / 1000).toFixed(1)}s
          </span>
          {combinedResults.graphrag_metadata && (
            <span className="flex items-center gap-1">
              🔗 {combinedResults.graphrag_metadata.entities_found} entities · {combinedResults.graphrag_metadata.relationships_found} rels
            </span>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 mb-4 bg-muted/50 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all
              ${activeTab === tab.id 
                ? 'bg-background shadow-sm border' 
                : 'hover:bg-background/50 text-muted-foreground'
              }
            `}
          >
            <span className={activeTab === tab.id ? tab.color : ''}>{tab.icon}</span>
            {tab.label}
            {tab.id === 'search' && (
              <span className="text-xs bg-blue-500/10 text-blue-600 px-1.5 py-0.5 rounded">
                {combinedResults.search_sources.length}
              </span>
            )}
            {tab.id === 'graphrag' && (
              <span className="text-xs bg-purple-500/10 text-purple-600 px-1.5 py-0.5 rounded">
                {combinedResults.graphrag_sources.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Active Answer */}
      <div
        className={`prose prose-sm max-w-none ${isRTL ? 'text-right' : 'text-left'}`}
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{linkedAnswer}</ReactMarkdown>
      </div>

      {/* Figures in active answer */}
      {sources
        .filter((s) => s.content_type === 'figure')
        .map((source) => (
          <FigureDisplay key={source.id} source={source} />
        ))}

      {/* Sources for active tab */}
      <SourcesList sources={sources} />
    </div>
  )
}

function SourcesList({ sources }: { sources: SourceChunk[] }) {
  const getContentIcon = (type: string) => {
    switch (type) {
      case 'figure':
        return <Image className="h-4 w-4" />
      case 'table':
        return <Table className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <div className="mt-6 pt-4 border-t">
      <h3 className="text-sm font-semibold mb-3">Sources ({sources.length})</h3>
      <div className="space-y-2">
        {sources.map((source, idx) => (
          <div
            key={source.id}
            id={`source-${idx + 1}`}
            className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
          >
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-medium">
              {idx + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                {getContentIcon(source.content_type)}
                <span className="text-sm font-medium truncate">
                  {source.source_document}
                </span>
                {source.page_numbers.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    p. {source.page_numbers.join(', ')}
                  </span>
                )}
                {source.source_document_sas_url && (
                  <a
                    href={source.source_document_sas_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary/80"
                  >
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {source.content}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                  {source.content_type}
                </span>
                <span className="text-xs text-muted-foreground">
                  Score: {source.relevance_score.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FigureDisplay({ source }: { source: SourceChunk }) {
  const [imageStatus, setImageStatus] = React.useState<'loading' | 'loaded' | 'error'>('loading')
  const [isExpanded, setIsExpanded] = React.useState(false)

  return (
    <div className="my-4 p-4 rounded-lg border bg-muted/30">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Image className="h-4 w-4" />
          <span className="text-sm font-medium">
            Figure from {source.source_document}, p.{source.page_numbers.join(', ')}
          </span>
        </div>
        {source.image_sas_url && (
          <a
            href={source.image_sas_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:text-primary/80 flex items-center gap-1"
          >
            <ExternalLink className="h-3 w-3" />
            Open full size
          </a>
        )}
      </div>
      
      {source.image_sas_url ? (
        <div className="relative">
          {imageStatus === 'loading' && (
            <div className="absolute inset-0 flex items-center justify-center bg-muted/50 rounded-lg">
              <div className="animate-pulse text-sm text-muted-foreground">Loading image...</div>
            </div>
          )}
          <img
            src={source.image_sas_url}
            alt={source.content || 'Figure'}
            className={`max-w-full h-auto rounded-lg border cursor-pointer transition-all ${
              isExpanded ? 'max-h-none' : 'max-h-96 object-contain'
            } ${imageStatus === 'loading' ? 'opacity-0' : 'opacity-100'}`}
            onLoad={() => setImageStatus('loaded')}
            onError={() => setImageStatus('error')}
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Click to collapse' : 'Click to expand'}
          />
          {imageStatus === 'error' && (
            <div className="text-xs text-muted-foreground border rounded-lg p-3 bg-muted/50">
              <p>Unable to display image inline.</p>
              <a
                href={source.image_sas_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:text-primary/80 underline"
              >
                Click here to view the image
              </a>
            </div>
          )}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground border rounded-lg p-3">
          Image not available for this figure.
        </div>
      )}
      
      {source.content && (
        <p className="text-xs text-muted-foreground mt-2 italic">
          {source.content.slice(0, 200)}{source.content.length > 200 ? '...' : ''}
        </p>
      )}
      {source.section_header && (
        <p className="text-xs text-muted-foreground mt-1">
          Section: {source.section_header}
        </p>
      )}
    </div>
  )
}
