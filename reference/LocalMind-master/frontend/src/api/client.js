/**
 * LocalMind API Client
 */

const API_BASE = '/api';

/**
 * Upload a document
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

/**
 * List all documents
 */
export async function listDocuments() {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
}

/**
 * Delete a document
 */
export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete document');
  }
  return response.json();
}

/**
 * Chat with documents (streaming)
 */
export async function* streamChat(query, options = {}) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      stream: true,
      ...options,
    }),
  });

  if (!response.ok) {
    throw new Error('Chat request failed');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }
}

/**
 * List available models
 */
export async function listModels() {
  const response = await fetch(`${API_BASE}/models`);
  if (!response.ok) {
    throw new Error('Failed to fetch models');
  }
  return response.json();
}

/**
 * Get backend status
 */
export async function getBackendStatus() {
  const response = await fetch(`${API_BASE}/backends/status`);
  if (!response.ok) {
    throw new Error('Failed to fetch backend status');
  }
  return response.json();
}

/**
 * Get hardware info (fine-tuning specific)
 */
export async function getHardwareInfo() {
  const response = await fetch(`${API_BASE}/finetune/hardware`);
  if (!response.ok) {
    throw new Error('Failed to fetch hardware info');
  }
  return response.json();
}

/**
 * Get comprehensive hardware status (CPU, GPU, memory, accelerators)
 */
export async function getHardwareStatus() {
  const response = await fetch(`${API_BASE}/hardware-status`);
  if (!response.ok) {
    throw new Error('Failed to fetch hardware status');
  }
  return response.json();
}

/**
 * Start fine-tuning job
 */
export async function startFineTune(name, documentIds = null, pairsPerChunk = 5) {
  const response = await fetch(`${API_BASE}/finetune/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name,
      document_ids: documentIds,
      pairs_per_chunk: pairsPerChunk,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to start fine-tuning');
  }

  return response.json();
}

/**
 * Stream fine-tune status
 */
export async function* streamFineTuneStatus(jobId) {
  const response = await fetch(`${API_BASE}/finetune/status/${jobId}`);

  if (!response.ok) {
    throw new Error('Failed to get fine-tune status');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }
}

/**
 * List fine-tune jobs
 */
export async function listFineTuneJobs() {
  const response = await fetch(`${API_BASE}/finetune/jobs`);
  if (!response.ok) {
    throw new Error('Failed to fetch fine-tune jobs');
  }
  return response.json();
}

/**
 * Stop a fine-tune job
 */
export async function stopFineTuneJob(jobId) {
  const response = await fetch(`${API_BASE}/finetune/jobs/${jobId}/stop`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to stop fine-tune job');
  }
  return response.json();
}

/**
 * Delete a fine-tune job
 */
export async function deleteFineTuneJob(jobId) {
  const response = await fetch(`${API_BASE}/finetune/jobs/${jobId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete fine-tune job');
  }
  return response.json();
}

/**
 * Health check
 */
export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }
  return response.json();
}
