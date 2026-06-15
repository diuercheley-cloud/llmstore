import { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Trash2, Eye, Database, Loader2 } from 'lucide-react';
import { Progress } from './ui-feedback';
import { toast } from 'sonner';
import { api } from '../lib/api';

export const RagDocs = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.listRagDocuments();
      setDocs(response.data);
    } catch (err) {
      console.error('Failed to load RAG docs', err);
      // Fallback or explicit unavailable state
      toast.error("Serviço de RAG indisponível ou erro na conexão.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => loadDocs());
  }, [loadDocs]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(10);
    
    try {
      await api.uploadRagDocument(file);
      setUploadProgress(100);
      toast.success("Upload concluído!", {
        description: "O documento está sendo processado para indexação RAG."
      });
      loadDocs();
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Upload failed';
      toast.error(errMsg);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteRagDocument(id);
      toast.success("Documento removido.");
      loadDocs();
    } catch (err) {
      toast.error("Falha ao remover documento.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">RAG Documents</h1>
        <div className="relative">
          <input
            type="file"
            id="rag-upload"
            className="hidden"
            onChange={handleFileUpload}
            disabled={isUploading}
          />
          <label 
            htmlFor="rag-upload"
            className={`btn btn-primary w-full sm:w-auto py-2.5 flex items-center justify-center gap-2 cursor-pointer ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload size={18} />}
            {isUploading ? 'Uploading...' : 'Upload New Document'}
          </label>
        </div>
      </div>

      {isUploading && (
        <div className="bg-white border border-border-base rounded-2xl p-6 shadow-sm animate-in fade-in slide-in-from-top-4">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <FileText className="text-primary w-5 h-5" />
              <span className="font-bold">Processando...</span>
            </div>
            <span className="text-sm font-mono font-bold text-primary">{uploadProgress}%</span>
          </div>
          <Progress value={uploadProgress} />
        </div>
      )}

      <div className="card !p-0 overflow-hidden">
        {loading && !docs.length ? (
          <div className="p-12 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-slate-500">Carregando documentos...</p>
          </div>
        ) : (
          <div className="resp-table-container">
            <table className="resp-table">
              <thead>
                <tr>
                  <th>DOCUMENT NAME</th>
                  <th>SIZE</th>
                  <th>CHUNKS</th>
                  <th>STATUS</th>
                  <th className="text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {docs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-12 text-slate-400 italic">
                      Nenhum documento encontrado. Faça upload para começar.
                    </td>
                  </tr>
                ) : docs.map(doc => (
                  <tr key={doc.id}>
                    <td data-label="DOCUMENT" className="font-medium text-slate-900">
                      <div className="flex items-center gap-3">
                        <div className="bg-slate-100 p-2 rounded-lg">
                          <FileText size={18} className="text-slate-500"/>
                        </div>
                        <span className="truncate max-w-[200px]">{doc.original_filename}</span>
                      </div>
                    </td>
                    <td data-label="SIZE" className="text-slate-500">{(doc.file_size_bytes / 1024).toFixed(1)} KB</td>
                    <td data-label="CHUNKS" className="text-slate-500 font-mono text-xs">{doc.chunks || 0}</td>
                    <td data-label="STATUS">
                      <span className={`badge ${doc.status === 'Processed' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                        {doc.status || 'Unknown'}
                      </span>
                    </td>
                    <td data-label="ACTIONS" className="md:text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button className="btn btn-outline !p-2" title="View Chunks"><Eye size={16} /></button>
                        <button 
                          onClick={() => handleDelete(doc.id)}
                          className="btn btn-danger !p-2" 
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-4">
        <div className="bg-blue-100 p-2 h-fit rounded-lg text-blue-600">
          <Database size={20} />
        </div>
        <div>
          <h4 className="font-bold text-blue-900">RAG Processing</h4>
          <p className="text-sm text-blue-700 mt-1 leading-relaxed">
            Your documents are automatically split into chunks and indexed for efficient retrieval during chat sessions. 
            Processing time depends on file size.
          </p>
        </div>
      </div>
    </div>
  );
};
