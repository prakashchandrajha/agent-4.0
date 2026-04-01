import { useState, useEffect } from 'react';
import { Brain, FileText, Settings, Cpu } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import DocumentUpload from './components/DocumentUpload';
import DocumentList from './components/DocumentList';
import ModelSelector from './components/ModelSelector';
import BackendStatus from './components/BackendStatus';
import HardwareBanner from './components/HardwareBanner';
import FineTunePanel from './components/FineTunePanel';
import { listDocuments, getBackendStatus } from './api/client';

function App() {
  const [documents, setDocuments] = useState([]);
  const [backendStatus, setBackendStatus] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    try {
      const [docs, status] = await Promise.all([
        listDocuments(),
        getBackendStatus(),
      ]);
      setDocuments(docs);
      setBackendStatus(status);
      setSelectedModel(status.default_model);
    } catch (error) {
      console.error('Failed to load initial data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function refreshDocuments() {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to refresh documents:', error);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Brain className="w-12 h-12 text-blue-600 mx-auto animate-pulse" />
          <p className="mt-4 text-gray-600">Loading LocalMind...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-8 h-8 text-blue-600" />
            <h1 className="text-xl font-bold text-gray-900">LocalMind</h1>
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              100% Offline
            </span>
          </div>
          <BackendStatus status={backendStatus} />
        </div>
      </header>

      {/* Hardware Performance Banner */}
      <div className="max-w-7xl mx-auto w-full px-4 mt-2">
        <HardwareBanner />
      </div>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'chat'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Brain className="w-4 h-4 inline mr-2" />
              Chat
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'documents'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" />
              Documents ({documents.length})
            </button>
            <button
              onClick={() => setActiveTab('finetune')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'finetune'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Cpu className="w-4 h-4 inline mr-2" />
              Fine-tune
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'settings'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Settings className="w-4 h-4 inline mr-2" />
              Settings
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4">
        {activeTab === 'chat' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100vh-180px)]">
            <div className="lg:col-span-3">
              <ChatInterface
                selectedModel={selectedModel}
                documents={documents}
              />
            </div>
            <div className="space-y-4">
              <DocumentUpload onUploadComplete={refreshDocuments} />
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-medium text-gray-900 mb-2">Quick Stats</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>Documents: {documents.length}</p>
                  <p>
                    Total chunks:{' '}
                    {documents.reduce((sum, d) => sum + d.chunk_count, 0)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="space-y-4">
            <DocumentUpload onUploadComplete={refreshDocuments} />
            <DocumentList
              documents={documents}
              onDocumentDeleted={refreshDocuments}
            />
          </div>
        )}

        {activeTab === 'finetune' && (
          <FineTunePanel
            documents={documents}
            backendStatus={backendStatus}
          />
        )}

        {activeTab === 'settings' && (
          <div className="bg-white rounded-lg border p-6">
            <h2 className="text-lg font-semibold mb-4">Model Settings</h2>
            <ModelSelector
              selectedModel={selectedModel}
              onModelSelect={setSelectedModel}
            />
            {backendStatus && (
              <div className="mt-6 pt-6 border-t">
                <h3 className="font-medium mb-2">Backend Configuration</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>LLM Backend: {backendStatus.llm_backend}</p>
                  <p>LLM URL: {backendStatus.llm_url}</p>
                  <p>Embedding Backend: {backendStatus.embedding_backend}</p>
                  <p>Embedding Model: {backendStatus.embedding_model}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
