import { useState } from 'react';
import { Upload, FileText, Trash2, Eye, Database, Loader2 } from 'lucide-react';
import { Progress } from './ui-feedback';
import { toast } from 'sonner';

export const RagDocs = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [docs, setDocs] = useState([
    { id: '1', name: 'company_policy.pdf', size: '2.4 MB', chunks: 15, status: 'Processed' },
    { id: '2', name: 'api_docs.md', size: '45 KB', chunks: 3, status: 'Processed' }
  ]);

  const handleUpload = () => {
    setIsUploading(true);
    setUploadProgress(0);
    
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          setDocs(prevDocs => [
            { id: Date.now().toString(), name: 'new_document.pdf', size: '1.2 MB', chunks: 0, status: 'Processing' },
            ...prevDocs
          ]);
          toast.success("Upload concluído!", {
            description: "O documento está sendo processado para indexação RAG."
          });
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">RAG Documents</h1>
        <button 
          onClick={handleUpload}
          disabled={isUploading}
          className="btn btn-primary w-full sm:w-auto py-2.5 flex items-center justify-center gap-2"
        >
          {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload size={18} />}
          {isUploading ? 'Uploading...' : 'Upload New Document'}
        </button>
      </div>

      {isUploading && (
        <div className="bg-white border border-border-base rounded-2xl p-6 shadow-sm animate-in fade-in slide-in-from-top-4">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <FileText className="text-primary w-5 h-5" />
              <span className="font-bold">new_document.pdf</span>
            </div>
            <span className="text-sm font-mono font-bold text-primary">{uploadProgress}%</span>
          </div>
          <Progress value={uploadProgress} />
        </div>
      )}

      <div className="card !p-0 overflow-hidden">
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
              {docs.map(doc => (
                <tr key={doc.id}>
                  <td data-label="DOCUMENT" className="font-medium text-slate-900">
                    <div className="flex items-center gap-3">
                      <div className="bg-slate-100 p-2 rounded-lg">
                        <FileText size={18} className="text-slate-500"/>
                      </div>
                      <span className="truncate max-w-[200px]">{doc.name}</span>
                    </div>
                  </td>
                  <td data-label="SIZE" className="text-slate-500">{doc.size}</td>
                  <td data-label="CHUNKS" className="text-slate-500 font-mono text-xs">{doc.chunks}</td>
                  <td data-label="STATUS">
                    <span className="badge bg-emerald-100 text-emerald-700">{doc.status}</span>
                  </td>
                  <td data-label="ACTIONS" className="md:text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="btn btn-outline !p-2" title="View Chunks"><Eye size={16} /></button>
                      <button className="btn btn-danger !p-2" title="Delete"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
