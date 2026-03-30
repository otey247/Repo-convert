import { JobResponse, JobStatus, FilePreview, PublishResult } from '../types';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export async function submitGithubJob(url: string, token?: string): Promise<JobResponse> {
  const formData = new FormData();
  formData.append('source_type', token ? 'github_private' : 'github_public');
  formData.append('github_url', url);
  if (token) formData.append('github_token', token);

  const response = await fetch(`${BASE_URL}/api/jobs`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

export async function submitZipJob(file: File): Promise<JobResponse> {
  const formData = new FormData();
  formData.append('source_type', 'zip_upload');
  formData.append('file', file);

  const response = await fetch(`${BASE_URL}/api/jobs`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${BASE_URL}/api/jobs/${jobId}`);

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

export function pollJobStatus(
  jobId: string,
  onUpdate: (status: JobStatus) => void
): Promise<JobStatus> {
  return new Promise((resolve, reject) => {
    let intervalId: ReturnType<typeof setInterval>;

    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        onUpdate(status);

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(intervalId);
          resolve(status);
        }
      } catch (err) {
        clearInterval(intervalId);
        reject(err);
      }
    };

    intervalId = setInterval(poll, 2000);
    // Start immediately
    poll();
  });
}

export function downloadZip(jobId: string): void {
  const url = `${BASE_URL}/api/jobs/${jobId}/download`;
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = '';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

export async function publishToGithub(
  jobId: string,
  repoName: string,
  token: string,
  description: string
): Promise<PublishResult> {
  const response = await fetch(`${BASE_URL}/api/jobs/${jobId}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_name: repoName, github_token: token, description }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  const data = await response.json();
  return { repo_url: data.repo_url };
}

export async function getFilePreview(jobId: string): Promise<FilePreview[]> {
  const response = await fetch(`${BASE_URL}/api/jobs/${jobId}/preview`);

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  const data = await response.json();
  // Backend returns PreviewResponse { job_id, mappings: [{source_path, output_path, action}] }
  // Map to the frontend FilePreview type
  return (data.mappings || []).map((m: { source_path: string; output_path: string; action: string }) => ({
    original: m.source_path,
    converted: m.output_path || '',
    action: m.action,
  }));
}
