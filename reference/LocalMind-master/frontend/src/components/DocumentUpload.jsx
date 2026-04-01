import { useState, useCallback } from 'react';
import { Upload, FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadDocument } from '../api/client';

function DocumentUpload({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e) => {
      e.preventDefault();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        await handleUpload(files[0]);
      }
    },
    [onUploadComplete]
  );

  const handleFileSelect = useCallback(
    async (e) => {
      const file = e.target.files?.[0];
      if (file) {
        await handleUpload(file);
      }
      e.target.value = '';
    },
    [onUploadComplete]
  );

  async function handleUpload(file) {
    setUploading(true);
    setUploadStatus(null);

    try {
      const result = await uploadDocument(file);
      setUploadStatus({
        type: 'success',
        message: `Uploaded ${file.name} (${result.chunk_count} chunks)`,
        warning: result.warning,
      });
      onUploadComplete?.();
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: error.message,
      });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="font-medium text-gray-900 mb-3">Upload Document</h3>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        {uploading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            <p className="mt-2 text-sm text-gray-600">Processing...</p>
          </div>
        ) : (
          <>
            <Upload className="w-8 h-8 text-gray-400 mx-auto" />
            <p className="mt-2 text-sm text-gray-600">
              Drag & drop or{' '}
              <label className="text-blue-600 hover:underline cursor-pointer">
                browse
                <input
                  type="file"
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.pptx,.txt,.md,.json,.xml,.yaml,.yml,.jpg,.jpeg,.png,.webp,.bmp,.tiff"
                />
              </label>
            </p>
            <p className="text-xs text-gray-500 mt-1">
              PDF, Word, Excel, Images, PowerPoint, Text
            </p>
          </>
        )}
      </div>

      {uploadStatus && (
        <div
          className={`mt-3 p-3 rounded-lg flex items-start gap-2 ${
            uploadStatus.type === 'success'
              ? 'bg-green-50 text-green-700'
              : 'bg-red-50 text-red-700'
          }`}
        >
          {uploadStatus.type === 'success' ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <div className="text-sm">
            <p>{uploadStatus.message}</p>
            {uploadStatus.warning && (
              <p className="text-yellow-700 mt-1">{uploadStatus.warning}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default DocumentUpload;
