import { useState, useEffect, useRef } from 'react';
import {
  Cpu,
  Play,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
  Zap,
  Square,
  Trash2,
} from 'lucide-react';
import {
  getHardwareInfo,
  startFineTune,
  listFineTuneJobs,
  stopFineTuneJob,
  deleteFineTuneJob,
} from '../api/client';

// ─── helpers ──────────────────────────────────────────────────────────────────

function formatETA(seconds) {
  if (!seconds) return 'calculating...';
  if (seconds < 60) return `~${seconds}s remaining`;
  return `~${Math.ceil(seconds / 60)} min remaining`;
}

function formatDuration(seconds) {
  if (!seconds) return '';
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function isJobStale(job) {
  // Job is stale if status is 'stale' or if generating_data is older than 10 minutes
  if (job.status === 'stale') return true;
  if (job.status === 'generating_data' || job.status === 'training') {
    const jobTime = new Date(job.created_at).getTime();
    const now = Date.now();
    const tenMinutes = 10 * 60 * 1000;
    return (now - jobTime) > tenMinutes;
  }
  return false;
}

function ProgressBar({ value, total, color = 'blue' }) {
  const pct = total > 0 ? Math.min(100, (value / total) * 100) : 0;
  const colorMap = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
  };
  return (
    <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
      <div
        className={`${colorMap[color] || colorMap.blue} h-2.5 rounded-full transition-all duration-300`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function DeviceBadge({ device, backend }) {
  if (!device && !backend) return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs text-gray-600 font-mono">
      <Zap className="w-3 h-3" />
      {[device?.toUpperCase(), backend].filter(Boolean).join(' · ')}
    </span>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

function FineTunePanel({ documents, backendStatus }) {
  const [hardware, setHardware] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [jobName, setJobName] = useState('');
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const esRef = useRef(null);
  const isRunningRef = useRef(false);

  useEffect(() => {
    loadData();
    return () => esRef.current?.close();
  }, []);

  async function loadData() {
    try {
      const [hw, jobList] = await Promise.all([
        getHardwareInfo(),
        listFineTuneJobs(),
      ]);
      setHardware(hw);
      setJobs(jobList);
    } catch (error) {
      console.error('Failed to load fine-tune data:', error);
    }
  }

  function connectSSE() {
    if (esRef.current) {
      esRef.current.close();
    }

    const es = new EventSource('/api/finetune/status');
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.ping) return;
        setProgress(data);
        if (data.stage === 'done' || data.stage === 'error') {
          setIsRunning(false);
          isRunningRef.current = false;
          es.close();
          esRef.current = null;
          loadData();
        }
      } catch (_) {}
    };

    es.onerror = () => {
      // Retry after 2 s if still running
      es.close();
      esRef.current = null;
      setTimeout(() => {
        if (isRunningRef.current) connectSSE();
      }, 2000);
    };
  }

  async function handleStartFineTune() {
    if (!jobName.trim()) {
      alert('Please enter a job name');
      return;
    }

    setIsRunning(true);
    isRunningRef.current = true;
    setProgress(null);
    setStartTime(Date.now());

    try {
      await startFineTune(jobName, selectedDocs.length > 0 ? selectedDocs : null);
      setJobName('');
      setSelectedDocs([]);
      connectSSE();
    } catch (error) {
      alert(`Failed to start: ${error.message}`);
      setIsRunning(false);
    }
  }

  function toggleDocSelection(docId) {
    setSelectedDocs((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  }

  // ── stop/delete job handlers ───────────────────────────────────────────────────

  const refreshJobs = async () => {
    try {
      const jobList = await listFineTuneJobs();
      setJobs(jobList);
    } catch (error) {
      console.error('Failed to refresh jobs:', error);
    }
  };

  const stopJob = async (jobId) => {
    if (!confirm('Stop this fine-tuning job?')) return;
    try {
      await stopFineTuneJob(jobId);
      refreshJobs();
    } catch (error) {
      alert(`Failed to stop job: ${error.message}`);
    }
  };

  const deleteJob = async (jobId) => {
    if (!confirm('Delete this job and all its files?')) return;
    try {
      await deleteFineTuneJob(jobId);
      refreshJobs();
    } catch (error) {
      alert(`Failed to delete job: ${error.message}`);
    }
  };

  // ── progress section renderer ────────────────────────────────────────────────

  function renderProgress() {
    if (!progress || (!isRunning && !['done', 'error'].includes(progress?.stage))) return null;

    const { stage } = progress;

    if (stage === 'filtering') {
      return (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
          <span className="text-sm text-gray-600">Filtering chunks...</span>
        </div>
      );
    }

    if (stage === 'generating') {
      const { processed_chunks, total_chunks, cached_chunks, generated_chunks, eta_seconds, device, backend } = progress;
      return (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-blue-800">Generating Q&A Pairs</span>
            <DeviceBadge device={device} backend={backend} />
          </div>
          <ProgressBar value={processed_chunks} total={total_chunks} color="blue" />
          <div className="flex items-center justify-between text-xs text-blue-700">
            <span>{(processed_chunks || 0).toLocaleString()} / {(total_chunks || 0).toLocaleString()} chunks</span>
            <span>{formatETA(eta_seconds)}</span>
          </div>
          <div className="flex gap-4 text-xs">
            <span className="text-green-700 font-medium">✓ {(cached_chunks || 0).toLocaleString()} cached</span>
            <span className="text-blue-700 font-medium">{(generated_chunks || 0).toLocaleString()} generated</span>
          </div>
        </div>
      );
    }

    if (stage === 'training') {
      const { train_step, train_total_steps, train_loss, device, backend } = progress;
      return (
        <div className="mt-4 p-4 bg-purple-50 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-purple-800">Training Model</span>
            <DeviceBadge device={device} backend={backend} />
          </div>
          <ProgressBar value={train_step} total={train_total_steps} color="purple" />
          <div className="flex items-center justify-between text-xs text-purple-700">
            <span>Step {train_step || 0} / {train_total_steps || '?'}</span>
            {train_loss > 0 && <span>Loss: {(train_loss || 0).toFixed(4)}</span>}
          </div>
        </div>
      );
    }

    if (stage === 'done') {
      const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : null;
      return (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-green-800">Fine-tuning complete! Model ready.</p>
            {elapsed && <p className="text-xs text-green-600 mt-0.5">Total time: {formatDuration(elapsed)}</p>}
          </div>
        </div>
      );
    }

    if (stage === 'error') {
      return (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">Fine-tuning failed</p>
            {progress.error && <p className="text-xs text-red-600 mt-1 font-mono">{progress.error}</p>}
          </div>
        </div>
      );
    }

    return null;
  }

  // ── render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Hardware Info */}
      {hardware && (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5" />
            Hardware Status
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">CUDA Available</p>
              <p className="text-lg font-medium">
                {hardware.cuda_available ? 'Yes' : 'No'}
              </p>
            </div>
            {hardware.cuda_devices?.length > 0 && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">GPU</p>
                <p className="text-lg font-medium">
                  {hardware.cuda_devices[0].name}
                </p>
                <p className="text-sm text-gray-500">
                  {hardware.total_vram_gb} GB VRAM
                </p>
              </div>
            )}
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-600">Recommended Backend</p>
              <p className="text-lg font-medium text-blue-700">
                {hardware.recommendation}
              </p>
              <p className="text-xs text-blue-600 mt-1">
                {hardware.recommendation_reason}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Start Fine-tuning */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold mb-4">Start Fine-tuning</h2>

        {documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Upload documents first to enable fine-tuning</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Job Name
              </label>
              <input
                type="text"
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
                placeholder="my-finetuned-model"
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isRunning}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Documents (optional - uses all if none selected)
              </label>
              <div className="border rounded-lg max-h-40 overflow-y-auto">
                {documents.map((doc) => (
                  <label
                    key={doc.id}
                    className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocs.includes(doc.id)}
                      onChange={() => toggleDocSelection(doc.id)}
                      disabled={isRunning}
                      className="rounded"
                    />
                    <span className="text-sm">{doc.original_filename}</span>
                    <span className="text-xs text-gray-500">
                      ({doc.chunk_count} chunks)
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <button
              onClick={handleStartFineTune}
              disabled={isRunning || !jobName.trim()}
              className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Start Fine-tuning
                </>
              )}
            </button>

            {renderProgress()}
          </div>
        )}
      </div>

      {/* Job History */}
      {jobs.length > 0 && (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-semibold mb-4">Fine-tuning History</h2>
          <div className="space-y-3">
            {jobs.map((job) => {
              const stale = isJobStale(job);
              const canStop = (job.status === 'generating_data' || job.status === 'training') && !stale;
              
              return (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="font-medium">{job.name}</p>
                    <p className="text-sm text-gray-500">{job.base_model}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {job.status === 'completed' ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : job.status === 'error' ? (
                      <AlertCircle className="w-5 h-5 text-red-500" />
                    ) : job.status === 'stopped' ? (
                      <Square className="w-5 h-5 text-yellow-500" />
                    ) : (
                      <Loader2 className={`w-5 h-5 ${stale ? 'text-orange-500' : 'text-blue-500 animate-spin'}`} />
                    )}
                    <span
                      className={`text-sm ${
                        job.status === 'completed'
                          ? 'text-green-600'
                          : job.status === 'error'
                          ? 'text-red-600'
                          : job.status === 'stopped'
                          ? 'text-yellow-600'
                          : stale
                          ? 'text-orange-600'
                          : 'text-blue-600'
                      }`}
                    >
                      {stale ? 'stale' : job.status}
                    </span>
                    {/* Action buttons */}
                    {canStop && (
                      <button
                        onClick={() => stopJob(job.id)}
                        className="ml-2 px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-100 hover:bg-yellow-200 rounded"
                        title="Stop this job"
                      >
                        Stop
                      </button>
                    )}
                    <button
                      onClick={() => deleteJob(job.id)}
                      className="ml-2 px-2 py-1 text-xs font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded"
                      title="Delete this job and all its files"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default FineTunePanel;
