import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

function BackendStatus({ status }) {
  if (!status) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Checking...</span>
      </div>
    );
  }

  const isHealthy = status.llm_status === 'healthy';

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        {isHealthy ? (
          <CheckCircle className="w-4 h-4 text-green-500" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
        <span className="text-sm text-gray-600">
          {status.llm_backend}
        </span>
      </div>
      <div className="text-sm text-gray-500">
        {status.default_model}
      </div>
      {status.hardware?.cuda_available && (
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
          GPU
        </span>
      )}
    </div>
  );
}

export default BackendStatus;
