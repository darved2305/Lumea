import { useState } from 'react'
import { Loader2, AlertCircle, FileText } from 'lucide-react'
import './PdfPreview.css'

interface PdfPreviewProps {
  fileUrl: string
  fileName?: string
  className?: string
}

function PdfPreview({ fileUrl, fileName, className = '' }: PdfPreviewProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const handleLoad = () => {
    setLoading(false)
    setError(false)
  }

  const handleError = () => {
    setLoading(false)
    setError(true)
  }

  if (!fileUrl) {
    return (
      <div className={`pdf-preview-empty ${className}`}>
        <FileText size={48} />
        <p>No file selected</p>
      </div>
    )
  }

  return (
    <div className={`pdf-preview-container ${className}`}>
      {loading && (
        <div className="pdf-preview-loading">
          <Loader2 size={32} className="spin" />
          <p>Loading PDF...</p>
        </div>
      )}
      
      {error && (
        <div className="pdf-preview-error">
          <AlertCircle size={48} />
          <p>Failed to load PDF</p>
          <p className="error-detail">{fileName || 'Unknown file'}</p>
        </div>
      )}
      
      {!error && (
        <iframe
          src={fileUrl}
          title={fileName || 'PDF Preview'}
          className="pdf-preview-iframe"
          onLoad={handleLoad}
          onError={handleError}
          style={{ display: loading ? 'none' : 'block' }}
        />
      )}
    </div>
  )
}

export default PdfPreview
