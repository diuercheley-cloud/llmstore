import React, { useState, useCallback } from 'react'
import { Upload, Package, FileText, X } from 'lucide-react'
import { PageHeader } from '../../components/layout/PageHeader'

interface BundleUploadProps {
  onBundleLoaded?: (manifest: Record<string, unknown>) => void
}

export const BundleUpload: React.FC<BundleUploadProps> = ({ onBundleLoaded }) => {
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFile = useCallback(async (f: File) => {
    setError(null)
    setFile(f)

    if (f.name.endsWith('.json')) {
      try {
        const text = await f.text()
        const data = JSON.parse(text)
        setManifest(data)
        onBundleLoaded?.(data)
      } catch {
        setError('Invalid JSON file')
        setManifest(null)
      }
    } else if (f.name.endsWith('.zip')) {
      // Would parse zip in production
      setManifest({ name: f.name, version: 'unknown', _zip: true })
      onBundleLoaded?.({ name: f.name, version: 'unknown', _zip: true })
    } else {
      setError('Unsupported file type. Use .json (manifest) or .zip (bundle archive)')
      setManifest(null)
    }
  }, [onBundleLoaded])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) handleFile(f)
  }, [handleFile])

  const clearFile = () => {
    setFile(null)
    setManifest(null)
    setError(null)
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
        <Upload className="w-5 h-5" />
        Upload Bundle
      </h3>

      {!file ? (
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer
            ${dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30'}
          `}
          onClick={() => document.getElementById('bundle-upload-input')?.click()}
        >
          <Package className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="font-medium text-foreground mb-1">Drop manifest.json or bundle.zip here</p>
          <p className="text-sm text-muted-foreground">or click to browse</p>
          <input
            id="bundle-upload-input"
            type="file"
            accept=".json,.zip"
            className="hidden"
            onChange={handleInputChange}
          />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-primary" />
              <div>
                <p className="font-medium text-sm">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
            <button onClick={clearFile} className="p-1 hover:bg-background rounded-lg">
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {manifest && !error && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              Manifest loaded: {String(manifest.name || 'unnamed')} v{String(manifest.version || '?')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default BundleUpload
