import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react'
import { documentsApi } from '../services/api'
import type { DocumentStatus } from '../types'

export function DocumentUpload() {
  const [documents, setDocuments] = useState<DocumentStatus[]>([])
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true)

    for (const file of acceptedFiles) {
      try {
        const status = await documentsApi.upload(file)
        setDocuments((prev) => [...prev, status])

        // Poll for status updates
        pollStatus(status.id)
      } catch (error) {
        console.error('Upload failed:', error)
      }
    }

    setUploading(false)
  }, [])

  const pollStatus = async (docId: string) => {
    const checkStatus = async () => {
      try {
        const status = await documentsApi.getStatus(docId)
        setDocuments((prev) =>
          prev.map((d) => (d.id === docId ? status : d))
        )

        if (status.status === 'pending' || status.status === 'processing') {
          setTimeout(checkStatus, 2000) // Poll every 2 seconds
        }
      } catch (error) {
        console.error('Status check failed:', error)
      }
    }
    checkStatus()
  }

  const handleReindex = async (docId: string) => {
    try {
      const updated = await documentsApi.reindex(docId)
      setDocuments((prev) => prev.map((d) => (d.id === docId ? updated : d)))
      pollStatus(docId)
    } catch (error) {
      console.error('Reindex failed:', error)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    },
    multiple: true,
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Loader2 className="h-4 w-4 text-gray-400" />
    }
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Upload className="h-5 w-5" />
        Document Upload
      </h2>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
          ${uploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />
        <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
        {isDragActive ? (
          <p className="text-primary">Drop files here...</p>
        ) : (
          <>
            <p className="text-muted-foreground">
              Drag & drop files here, or click to browse
            </p>
            <p className="text-sm text-muted-foreground/75 mt-1">
              Supports PDF, DOCX, XLSX, PPTX
            </p>
          </>
        )}
      </div>

      {/* Uploaded Documents */}
      {documents.length > 0 && (
        <div className="mt-4 space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <File className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{doc.filename}</p>
                  {doc.status === 'completed' && (
                    <p className="text-xs text-muted-foreground">
                      {doc.chunks_created} chunks, {doc.figures_extracted} figures
                    </p>
                  )}
                  {doc.status === 'failed' && (
                    <p className="text-xs text-red-500">{doc.error_message}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {doc.status === 'completed' && (
                  <button
                    onClick={() => handleReindex(doc.id)}
                    className="p-1 rounded hover:bg-muted"
                    title="Reindex document"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                )}
                {getStatusIcon(doc.status)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
