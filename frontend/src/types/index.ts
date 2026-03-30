export interface JobResponse {
  job_id: string;
  status: string;
}

export interface ConversionSummary {
  total_files: number;
  md_files_converted: number;
  output_repo_name: string;
  skipped_files: string[];
  errors: string[];
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  summary?: ConversionSummary;
  error?: string;
}

export interface FilePreview {
  original: string;
  converted: string;
}

export interface PublishResult {
  success: boolean;
  repo_url?: string;
  error?: string;
}
