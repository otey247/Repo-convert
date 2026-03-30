import { JobResponse, JobStatus, FilePreview, PublishResult } from '../types';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export async function submitGithubJob(url: string, token?: string): Promise<JobResponse> {
  const body: Record<string, string> = { url };
  if (token) body.token = token;

  const response = await fetch(`${BASE_URL}/api/jobs/github`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

export async function submitZipJob(file: File): Promise<JobResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${BASE_URL}/api/jobs/zip`, {
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
    body: JSON.stringify({ repo_name: repoName, token, description }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

export async function getFilePreview(jobId: string): Promise<FilePreview[]> {
  const response = await fetch(`${BASE_URL}/api/jobs/${jobId}/preview`);

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}
