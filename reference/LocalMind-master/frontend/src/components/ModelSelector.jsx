import { useState, useEffect } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import { listModels } from '../api/client';

function ModelSelector({ selectedModel, onModelSelect }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    loadModels();
  }, []);

  async function loadModels() {
    try {
      const modelList = await listModels();
      setModels(modelList);
    } catch (error) {
      console.error('Failed to load models:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading models...</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Select Model
      </label>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2 border rounded-lg bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <span className="truncate">
          {selectedModel || 'Select a model'}
        </span>
        <ChevronDown
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {models.length === 0 ? (
            <div className="p-4 text-center text-gray-500 text-sm">
              No models available. Make sure your LLM backend is running.
            </div>
          ) : (
            models.map((model) => (
              <button
                key={model.id}
                onClick={() => {
                  onModelSelect(model.id);
                  setIsOpen(false);
                }}
                className={`w-full px-4 py-2 text-left hover:bg-gray-100 ${
                  selectedModel === model.id ? 'bg-blue-50 text-blue-700' : ''
                }`}
              >
                <span className="block font-medium">{model.name}</span>
                {model.size && (
                  <span className="text-xs text-gray-500">
                    {(model.size / (1024 * 1024 * 1024)).toFixed(1)} GB
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default ModelSelector;
