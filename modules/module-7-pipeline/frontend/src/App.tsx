import { useState } from 'react'
import { DocumentUpload } from './components/DocumentUpload'
import { QueryInput } from './components/QueryInput'
import { RetrievalConfig } from './components/RetrievalConfig'
import { AnswerDisplay } from './components/AnswerDisplay'
import { RetrievalDetails } from './components/RetrievalDetails'
import { ValidationReportPanel } from './components/ValidationReport'
import { IndexSchemaViewer } from './components/IndexSchemaViewer'
import { SystemControls } from './components/SystemControls'
import { useQuery } from './hooks/useQuery'
import { useConfig } from './hooks/useConfig'
import type { QueryResponse, QueryConfig } from './types'

function App() {
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [_currentQuestion, setCurrentQuestion] = useState('')
  
  const { config, updateConfig } = useConfig()
  const { executeQuery } = useQuery()

  const handleQuery = async (question: string) => {
    setCurrentQuestion(question)
    setIsLoading(true)
    try {
      const response = await executeQuery(question, config)
      setQueryResponse(response)
    } catch (error) {
      console.error('Query failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetryQuery = async (retryQuery: string) => {
    await handleQuery(retryQuery)
  }

  const handleConfigChange = (newConfig: Partial<QueryConfig>) => {
    updateConfig({ ...config, ...newConfig })
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="max-w-[1800px] mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-4xl">📚</span>
              <div>
                <h1 className="text-2xl font-bold">RAG Workshop</h1>
                <p className="text-base text-muted-foreground">Educational Pipeline Explorer</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">Module 7 - Capstone</span>
              <SystemControls />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1800px] mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Upload & Query */}
          <div className="lg:col-span-2 space-y-6">
            {/* Document Upload */}
            <DocumentUpload />

            {/* Query Input */}
            <QueryInput onSubmit={handleQuery} isLoading={isLoading} />

            {/* Answer Display */}
            {queryResponse && (
              <AnswerDisplay response={queryResponse} isLoading={isLoading} />
            )}

            {/* Validation Report (NEW!) */}
            {queryResponse?.validation_report && (
              <ValidationReportPanel 
                report={queryResponse.validation_report} 
                onRetry={handleRetryQuery}
              />
            )}

            {/* Retrieval Details (Observability) */}
            {queryResponse && (
              <RetrievalDetails metadata={queryResponse.retrieval_metadata} response={queryResponse} />
            )}
          </div>

          {/* Right Column - Config & Schema */}
          <div className="space-y-6">
            {/* Retrieval Configuration */}
            <RetrievalConfig config={config} onChange={handleConfigChange} />

            {/* Index Schema Viewer */}
            <IndexSchemaViewer />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-card mt-auto">
        <div className="container mx-auto px-4 py-4">
          <p className="text-center text-sm text-muted-foreground">
            RAG & Multimodal Knowledge Workshop - Microsoft AI Technologies
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
