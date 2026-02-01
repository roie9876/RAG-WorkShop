import React from 'react'
import ReactMarkdown from 'react-markdown'
import { FileText, Image, Table, ExternalLink } from 'lucide-react'
import type { QueryResponse, SourceChunk } from '../types'

interface AnswerDisplayProps {
  response: QueryResponse
  isLoading: boolean
}

export function AnswerDisplay({ response, isLoading }: AnswerDisplayProps) {
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
        <ReactMarkdown>{linkedAnswer}</ReactMarkdown>
      </div>

      {/* Figures in Answer */}
      {response.sources
        .filter((s) => s.content_type === 'figure')
        .map((source) => (
          <FigureDisplay key={source.id} source={source} />
        ))}

      {/* Sources */}
      <div className="mt-6 pt-4 border-t">
        <h3 className="text-sm font-semibold mb-3">Sources</h3>
        <div className="space-y-2">
          {response.sources.map((source, idx) => (
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
