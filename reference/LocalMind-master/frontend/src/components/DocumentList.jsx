import { useState } from 'react';
import {
  FileText,
  Trash2,
  Loader2,
  FileSpreadsheet,
  Image,
  Presentation,
  File,
  Clock,
  Cpu,
} from 'lucide-react';
import { deleteDocument } from '../api/client';

const FILE_ICONS = {
  pdf: FileText,
  word: FileText,
  excel: FileSpreadsheet,
  csv: FileSpreadsheet,
  image: Image,
  pptx: Presentation,
  text: File,
};

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString();
}

function DocumentList({ documents, onDocumentDeleted }) {
  const [deletingId, setDeletingId] = useState(null);

  async function handleDelete(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    setDeletingId(documentId);
    try {
      await deleteDocument(documentId);
      onDocumentDeleted?.();
    } catch (error) {
      alert(`Failed to delete: ${error.message}`);
    } finally {
      setDeletingId(null);
    }
  }

  if (documents.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <FileText className="w-12 h-12 text-gray-300 mx-auto" />
        <p className="mt-4 text-gray-500">No documents uploaded yet</p>
        <p className="text-sm text-gray-400 mt-1">
          Upload documents to start chatting with them
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border">
      <div className="p-4 border-b">
        <h2 className="font-semibold text-gray-900">
          Documents ({documents.length})
        </h2>
      </div>
      <div className="divide-y">
        {documents.map((doc) => {
          const Icon = FILE_ICONS[doc.file_type] || File;
          const isDeleting = deletingId === doc.id;

          return (
            <div
              key={doc.id}
              className="p-4 flex items-center gap-4 hover:bg-gray-50"
            >
              <div className="p-2 bg-gray-100 rounded-lg">
                <Icon className="w-6 h-6 text-gray-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {doc.original_filename}
                </p>
                <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                  <span>{formatFileSize(doc.file_size)}</span>
                  <span>{doc.chunk_count} chunks</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      doc.status === 'ready'
                        ? 'bg-green-100 text-green-700'
                        : doc.status === 'error'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {doc.status}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {formatDate(doc.created_at)}
                </p>
                {doc.processing_time != null && (
                  <div className="flex items-center gap-2 text-xs text-indigo-600 mt-1">
                    <Clock className="w-3 h-3" />
                    <span>
                      {doc.processing_time}s
                      {doc.accelerator_used && (
                        <> via <Cpu className="w-3 h-3 inline mx-0.5" />{doc.accelerator_used}</>
                      )}
                    </span>
                  </div>
                )}
                {doc.error_message && (
                  <p className="text-xs text-red-600 mt-1">{doc.error_message}</p>
                )}
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                disabled={isDeleting}
                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              >
                {isDeleting ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Trash2 className="w-5 h-5" />
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DocumentList;
