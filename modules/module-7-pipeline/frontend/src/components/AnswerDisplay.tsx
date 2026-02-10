import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { FileText, Image, Table, ExternalLink, Combine, Search, Network, Sparkles, ChevronDown, ChevronRight } from 'lucide-react'
import type { QueryResponse, SourceChunk, CombinedResults } from '../types'

/** Shared remark/rehype plugins for all ReactMarkdown instances */
const remarkPlugins = [remarkGfm, remarkMath]
const rehypePlugins = [rehypeKatex]

/**
 * Convert LLM-style LaTeX delimiters to standard $ / $$ delimiters
 * that remark-math understands.
 *
 * Patterns handled:
 *   \( ... \)  →  $...$      (inline)
 *   \[ ... \]  →  $$...$$    (display)
 *   ( O(T^2 \cdot D) )  — bare parens with LaTeX inside → $...$
 */
function normalizeMath(text: string): string {
  // \( ... \)  →  $ ... $
  let result = text.replace(/\\\((.+?)\\\)/g, (_m, inner) => `$${inner.trim()}$`)
  // \[ ... \]  →  $$ ... $$
  result = result.replace(/\\\[(.+?)\\\]/gs, (_m, inner) => `$$${inner.trim()}$$`)

  // ---- Fix 1: Split-dollar formulas ----
  // "$O$N^2 d_k"   → "$O(N^2 \\cdot d_k)$"
  // "$O$H N^2 d_k" → "$O(H \\cdot N^2 \\cdot d_k)$"
  // "$O$H N^2 d_k$$" → "$O(H \\cdot N^2 \\cdot d_k)$"   (strip trailing $$)
  result = result.replace(
    /\$([A-Za-z]{1,4})\$\s*([A-Za-z0-9^_{}\s·×*\\]+(?:[^$\n,.:;]{2,}))\$*/g,
    (_match, head: string, tail: string) => {
      // Only merge if the tail looks like math (has ^, _, digits after letters)
      if (!/[\^_\d]/.test(tail)) return _match
      const cleaned = tail.trim()
        .replace(/\$+$/g, '')            // strip trailing $ or $$
        .replace(/\s+/g, ' ')            // normalize spaces
      // Build the merged formula — add parens if head looks like a function (O)
      const parts = cleaned.split(/\s+/)
      const joined = parts.join(' \\cdot ')
      const body = /^[A-Z]$/.test(head)
        ? `${head}(${joined})`
        : `${head} \\cdot ${joined}`
      return `$${body}$`
    }
  )

  // ---- Fix 2: Bare Big-O notation ----
  // O(N^2), O(n^2 · d), O(T^2) not inside $...$ → wrap in $...$
  result = result.replace(
    /(\$\$[^$]+\$\$|\$[^$]+\$)|(?<!\$)\b(O\([^)]+\))(?!\$)/g,
    (_match, dollarBlock, bigO) => {
      if (dollarBlock) return dollarBlock
      const cleaned = bigO.replace(/\s*[·×*]\s*/g, ' \\cdot ')
      return `$${cleaned}$`
    }
  )

  // ---- Fix 3: Bare single-letter math variables ----
  // Q, K, V, N, H, T, D standing alone (not inside $...$, not part of a word)
  result = result.replace(
    /(\$\$[^$]+\$\$|\$[^$]+\$)|(?<=[\s(,])([QKVNHTD])(?=[\s),.:;!?]|$)/gm,
    (_match, dollarBlock, letter) => {
      if (dollarBlock) return dollarBlock
      if (!letter) return _match
      return `$${letter}$`
    }
  )

  // ---- Fix 4: Bare subscript / superscript expressions ----
  // d_k, d_v, N^2, T^2 not inside $...$
  result = result.replace(
    /(\$\$[^$]+\$\$|\$[^$]+\$)|(?<=[\s(,])([A-Za-z](?:_[A-Za-z0-9{}]+|\^[A-Za-z0-9{}]+))(?=[\s),.:;!?]|$)/gm,
    (_match, dollarBlock, expr) => {
      if (dollarBlock) return dollarBlock
      if (!expr) return _match
      return `$${expr}$`
    }
  )

  // ---- Fix 5: Bare parens with LaTeX commands inside ----
  // ( ... \cdot ... ) → $...$
  result = result.replace(
    /(\$\$[^$]+\$\$|\$[^$]+\$)|(\(\s*([^()]*(?:\\(?:cdot|times|frac|text|mathcal|mathrm|log|sqrt|sum|prod|int|infty|leq|geq|neq|approx|left|right)[^()]*|\^[^()]*|_[^()]*)[^()]*)\s*\))/g,
    (_match, dollarBlock, _parenBlock, inner) => {
      if (dollarBlock) return dollarBlock
      return `$${inner.trim()}$`
    }
  )

  // ---- Fix 6: Bare LaTeX commands outside $...$ ----
  // e.g. "1/\sqrt{d_k}" or "\frac{a}{b}" or "\sqrt{x}" not inside dollars
  result = result.replace(
    /(\$\$[^$]+\$\$|\$[^$]+\$)|(?<!\$)((?:[A-Za-z0-9]+[/])?\\(?:sqrt|frac|mathrm|mathcal|text|log|sum|prod|int|mathbb)(?:\{[^}]*\})+(?:[/^_][A-Za-z0-9{}\\]+)*)(?!\$)/g,
    (_match, dollarBlock, expr) => {
      if (dollarBlock) return dollarBlock
      if (!expr) return _match
      return `$${expr}$`
    }
  )

  // ---- Fix 7: Broken display math ----
  // Short $$x$$ that should be inline → $x$
  result = result.replace(/\$\$([^$]{1,30})\$\$/g, (_m, inner) => {
    if (inner.trim().length < 20 && !inner.includes('\\frac') && !inner.includes('\n')) {
      return `$${inner.trim()}$`
    }
    return _m
  })

  return result
}

/**
 * Normalize all citation formats into individually linked references.
 * Handles: [Source 1], [Source 1, 3, 5], [1], [1, 3, 5], [1][3][5]
 * Produces: [[1]](#source-1) [[3]](#source-3) [[5]](#source-5)
 * The double-brackets prevent ReactMarkdown from consuming them as link text.
 */
function linkCitations(text: string, prefix = ''): string {
  // Step 0: Normalize LaTeX math delimiters for KaTeX rendering
  let result = normalizeMath(text)

  // Step 1: Normalize "[Source N]" → "[N]"
  result = result.replace(/\[Source\s+(\d+)\]/g, '[$1]')

  // Step 2: Expand comma-separated groups "[1, 3, 5]" or "[1,3,5]" → "[1] [3] [5]"
  result = result.replace(/\[([\d,\s]+)\]/g, (_match, inner: string) => {
    const nums = inner.split(/[,\s]+/).filter((n: string) => n.length > 0)
    if (nums.length === 0) return _match
    return nums.map((n: string) => `[${n}]`).join('')
  })

  // Step 3: Convert individual "[N]" → linked superscript
  result = result.replace(/\[(\d+)\]/g, `[[$1]](#${prefix}source-$1)`)

  return result
}

interface AnswerDisplayProps {
  response: QueryResponse
  isLoading: boolean
}

export function AnswerDisplay({ response }: AnswerDisplayProps) {
  const isCombined = response.retrieval_metadata.strategy_used === 'combined' && response.combined_results

  if (isCombined && response.combined_results) {
    return <CombinedAnswerDisplay response={response} combinedResults={response.combined_results} />
  }

  return <StandardAnswerDisplay response={response} />
}

function StandardAnswerDisplay({ response }: { response: QueryResponse }) {
  // Detect RTL in answer
  const isRTL = /[\u0590-\u05FF\u0600-\u06FF]/.test(response.answer)
  const linkedAnswer = linkCitations(response.answer)

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold mb-4">Answer</h2>

      {/* Main Answer */}
      <div
        className={`prose prose-sm max-w-none ${isRTL ? 'text-right' : 'text-left'}`}
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>{linkedAnswer}</ReactMarkdown>
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
  const [activeTab, setActiveTab] = useState<'search' | 'graphrag'>('search')
  const [showDetails, setShowDetails] = useState(false)

  const tabs = [
    { id: 'search' as const, label: `AI Search (${combinedResults.search_strategy})`, icon: <Search className="h-4 w-4" />, color: 'text-blue-500' },
    { id: 'graphrag' as const, label: `GraphRAG (${combinedResults.graphrag_mode})`, icon: <Network className="h-4 w-4" />, color: 'text-purple-500' },
  ]

  const getDetailAnswer = () => {
    switch (activeTab) {
      case 'search': return combinedResults.search_answer
      case 'graphrag': return combinedResults.graphrag_answer
    }
  }

  const getDetailSources = () => {
    switch (activeTab) {
      case 'search': return combinedResults.search_sources
      case 'graphrag': return combinedResults.graphrag_sources
    }
  }

  // Main merged answer
  const mergedAnswer = response.answer
  const isRTL = /[\u0590-\u05FF\u0600-\u06FF]/.test(mergedAnswer)
  const linkedMerged = linkCitations(mergedAnswer)

  // Figures from all sources
  const allFigures = response.sources.filter((s) => s.content_type === 'figure')

  // Detail tab answer
  const detailAnswer = getDetailAnswer()
  const detailRTL = /[\u0590-\u05FF\u0600-\u06FF]/.test(detailAnswer)
  const linkedDetail = linkCitations(detailAnswer, 'detail-')

  return (
    <div className="space-y-4">
      {/* ═══════════════════════════════════════════════════ */}
      {/* SECTION 1: FINAL ANSWER + FIGURES                  */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="rounded-lg border bg-card p-6">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="h-5 w-5 text-amber-500" />
          <h2 className="text-lg font-semibold">Answer</h2>
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

        {/* Merged Answer Text */}
        <div
          className={`prose prose-sm max-w-none ${isRTL ? 'text-right' : 'text-left'}`}
          dir={isRTL ? 'rtl' : 'ltr'}
        >
          <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>{linkedMerged}</ReactMarkdown>
        </div>

        {/* Figures — directly below the answer */}
        {allFigures.length > 0 && (
          <div className="mt-6">
            {allFigures.map((source) => (
              <FigureDisplay key={source.id} source={source} />
            ))}
          </div>
        )}

        {/* Sources summary */}
        <SourcesList sources={response.sources} />
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* SECTION 2: HOW THIS ANSWER WAS GENERATED           */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="rounded-lg border bg-card overflow-hidden">
        {/* Collapsible header */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full flex items-center gap-2 p-4 hover:bg-muted/50 transition-colors text-left"
        >
          {showDetails
            ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
            : <ChevronRight className="h-4 w-4 text-muted-foreground" />
          }
          <Combine className="h-4 w-4 text-amber-500" />
          <span className="text-sm font-semibold">How this answer was generated</span>
          <span className="text-xs text-muted-foreground ml-2">
            — merged from AI Search ({combinedResults.search_strategy}) + GraphRAG ({combinedResults.graphrag_mode})
          </span>
        </button>

        {showDetails && (
          <div className="px-4 pb-4 border-t">
            {/* Tab Navigation */}
            <div className="flex gap-1 my-4 bg-muted/50 rounded-lg p-1">
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

            {/* Detail Answer */}
            <div
              className={`prose prose-sm max-w-none ${detailRTL ? 'text-right' : 'text-left'}`}
              dir={detailRTL ? 'rtl' : 'ltr'}
            >
              <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>{linkedDetail}</ReactMarkdown>
            </div>

            {/* Detail Sources */}
            <SourcesList sources={getDetailSources()} idPrefix="detail-" />
          </div>
        )}
      </div>
    </div>
  )
}

function SourcesList({ sources, idPrefix = '' }: { sources: SourceChunk[]; idPrefix?: string }) {
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
            id={`${idPrefix}source-${idx + 1}`}
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

/**
 * Extract a clean caption from figure chunk content.
 *
 * The indexed content for figures looks like:
 *   Document: 1706.03762v7.pdf\nSection: 3.2\nPage: 4\n\nSurrounding Context:\n...\n\nFigure Description:\n...
 *
 * We want to show only the Figure Description, or the Surrounding Context
 * as a fallback, instead of the raw metadata block.
 */
function extractFigureCaption(content: string): string {
  // Try to find "Figure Description:" and use everything after it
  const descIdx = content.indexOf('Figure Description:')
  if (descIdx !== -1) {
    let desc = content.slice(descIdx + 'Figure Description:'.length).trim()
    // Strip leading markdown bold markers from CU output like "**Type of image:**"
    desc = desc.replace(/^\*\*[^*]+\*\*\s*/g, '').trim()
    if (desc.length > 0) return desc.length > 300 ? desc.slice(0, 300) + '…' : desc
  }
  // Fallback: try "Surrounding Context:"
  const ctxIdx = content.indexOf('Surrounding Context:')
  if (ctxIdx !== -1) {
    const afterCtx = content.slice(ctxIdx + 'Surrounding Context:'.length).trim()
    const endIdx = afterCtx.indexOf('Figure Description:')
    const ctx = endIdx !== -1 ? afterCtx.slice(0, endIdx).trim() : afterCtx
    if (ctx.length > 0) return ctx.length > 200 ? ctx.slice(0, 200) + '…' : ctx
  }
  // Last resort: first 200 chars, skipping the "Document: / Section: / Page:" header
  const lines = content.split('\n').filter(l =>
    !/^(Document:|Section:|Page:)\s/.test(l.trim()) && l.trim().length > 0
  )
  const fallback = lines.join(' ').trim()
  return fallback.length > 200 ? fallback.slice(0, 200) + '…' : fallback
}

function FigureDisplay({ source }: { source: SourceChunk }) {
  const [imageStatus, setImageStatus] = React.useState<'loading' | 'loaded' | 'error'>('loading')
  const [isExpanded, setIsExpanded] = React.useState(false)
  const caption = React.useMemo(() => extractFigureCaption(source.content || ''), [source.content])

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
            alt={caption || 'Figure'}
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
      
      {caption && (
        <p className="text-xs text-muted-foreground mt-2 italic">
          {caption}
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
