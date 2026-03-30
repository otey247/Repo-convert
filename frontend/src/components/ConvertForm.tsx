import React, { useState, useCallback } from 'react';
import { JobStatus } from '../types';
import { submitGithubJob, submitZipJob, pollJobStatus } from '../services/api';
import ConversionSummary from './ConversionSummary';

type InputType = 'github-public' | 'github-private' | 'zip';

const styles: Record<string, React.CSSProperties> = {
  form: {
    width: '100%',
  },
  tabRow: {
    display: 'flex',
    borderBottom: '2px solid #edebe9',
    marginBottom: '24px',
  },
  tab: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: 'none',
    color: '#605e5c',
    borderBottom: '2px solid transparent',
    marginBottom: '-2px',
    transition: 'color 0.15s',
  },
  activeTab: {
    color: '#0078D4',
    borderBottom: '2px solid #0078D4',
    fontWeight: 600,
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: '#323130',
    marginBottom: '5px',
  },
  input: {
    width: '100%',
    padding: '9px 12px',
    fontSize: '14px',
    border: '1px solid #8a8886',
    borderRadius: '4px',
    marginBottom: '16px',
    boxSizing: 'border-box' as const,
    outline: 'none',
    color: '#201f1e',
    backgroundColor: '#fff',
  },
  inputError: {
    borderColor: '#a4262c',
  },
  fieldError: {
    fontSize: '12px',
    color: '#a4262c',
    marginTop: '-12px',
    marginBottom: '12px',
    display: 'block',
  },
  hint: {
    fontSize: '12px',
    color: '#605e5c',
    marginTop: '-12px',
    marginBottom: '14px',
  },
  fileInputWrapper: {
    position: 'relative' as const,
    marginBottom: '16px',
  },
  fileInputLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    border: '2px dashed #8a8886',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#605e5c',
    backgroundColor: '#faf9f8',
    transition: 'border-color 0.15s',
  },
  fileInputLabelActive: {
    borderColor: '#0078D4',
    backgroundColor: '#f0f6ff',
  },
  fileInput: {
    position: 'absolute' as const,
    opacity: 0,
    width: 0,
    height: 0,
  },
  fileSelected: {
    fontSize: '13px',
    color: '#107c10',
    fontWeight: 500,
  },
  submitBtn: {
    width: '100%',
    padding: '11px',
    fontSize: '15px',
    fontWeight: 600,
    backgroundColor: '#0078D4',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginTop: '4px',
    transition: 'background-color 0.15s',
  },
  disabledBtn: {
    opacity: 0.65,
    cursor: 'not-allowed',
  },
  progressSection: {
    marginTop: '20px',
  },
  progressLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '13px',
    color: '#605e5c',
    marginBottom: '6px',
  },
  progressBarTrack: {
    width: '100%',
    height: '8px',
    backgroundColor: '#edebe9',
    borderRadius: '4px',
    overflow: 'hidden' as const,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#0078D4',
    borderRadius: '4px',
    transition: 'width 0.4s ease',
  },
  statusMessage: {
    fontSize: '13px',
    color: '#605e5c',
    marginTop: '8px',
    textAlign: 'center' as const,
  },
  errorBox: {
    marginTop: '16px',
    padding: '12px 14px',
    backgroundColor: '#fde7e9',
    border: '1px solid #a4262c',
    borderRadius: '4px',
    color: '#a4262c',
    fontSize: '13px',
    borderLeft: '4px solid #a4262c',
  },
};

const statusLabels: Record<string, string> = {
  pending: 'Queued…',
  processing: 'Converting files…',
  completed: 'Done!',
  failed: 'Failed',
};

const ConvertForm: React.FC = () => {
  const [inputType, setInputType] = useState<InputType>('github-public');
  const [githubUrl, setGithubUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [globalError, setGlobalError] = useState('');

  const validate = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (inputType === 'github-public' || inputType === 'github-private') {
      if (!githubUrl.trim()) {
        errors.githubUrl = 'GitHub URL is required.';
      } else if (!githubUrl.trim().startsWith('https://github.com/')) {
        errors.githubUrl = 'URL must start with https://github.com/';
      }
      if (inputType === 'github-private' && !githubToken.trim()) {
        errors.githubToken = 'Personal Access Token is required for private repositories.';
      }
    }

    if (inputType === 'zip') {
      if (!zipFile) {
        errors.zipFile = 'Please select a .zip file.';
      } else if (!zipFile.name.toLowerCase().endsWith('.zip')) {
        errors.zipFile = 'File must be a .zip archive.';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [inputType, githubUrl, githubToken, zipFile]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGlobalError('');
    setJobStatus(null);

    if (!validate()) return;

    setSubmitting(true);

    try {
      let jobResponse;

      if (inputType === 'github-public') {
        jobResponse = await submitGithubJob(githubUrl.trim());
      } else if (inputType === 'github-private') {
        jobResponse = await submitGithubJob(githubUrl.trim(), githubToken.trim());
      } else {
        jobResponse = await submitZipJob(zipFile!);
      }

      // Start polling
      await pollJobStatus(jobResponse.job_id, (status) => {
        setJobStatus(status);
      });
    } catch (err: any) {
      setGlobalError(err.message || 'An unexpected error occurred. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setGithubUrl('');
    setGithubToken('');
    setZipFile(null);
    setJobStatus(null);
    setGlobalError('');
    setFieldErrors({});
    setSubmitting(false);
    setInputType('github-public');
  };

  const handleFileChange = (file: File | null) => {
    setZipFile(file);
    if (file) {
      setFieldErrors((prev) => ({ ...prev, zipFile: '' }));
    }
  };

  const isProcessing = submitting || (jobStatus?.status === 'pending' || jobStatus?.status === 'processing');
  const isCompleted = jobStatus?.status === 'completed' && jobStatus?.summary;

  if (isCompleted) {
    return (
      <ConversionSummary
        jobId={jobStatus!.job_id}
        summary={jobStatus!.summary!}
        onReset={handleReset}
      />
    );
  }

  return (
    <form style={styles.form} onSubmit={handleSubmit} noValidate>
      {/* Tab selector */}
      <div style={styles.tabRow} role="tablist">
        {(['github-public', 'github-private', 'zip'] as InputType[]).map((type) => {
          const labels: Record<InputType, string> = {
            'github-public': 'GitHub Public',
            'github-private': 'GitHub Private',
            'zip': 'ZIP Upload',
          };
          return (
            <button
              key={type}
              type="button"
              role="tab"
              aria-selected={inputType === type}
              style={{
                ...styles.tab,
                ...(inputType === type ? styles.activeTab : {}),
              }}
              onClick={() => {
                setInputType(type);
                setFieldErrors({});
                setGlobalError('');
              }}
              disabled={isProcessing}
            >
              {labels[type]}
            </button>
          );
        })}
      </div>

      {/* GitHub URL input (public & private) */}
      {(inputType === 'github-public' || inputType === 'github-private') && (
        <>
          <label style={styles.label} htmlFor="github-url">
            GitHub Repository URL
          </label>
          <input
            id="github-url"
            style={{
              ...styles.input,
              ...(fieldErrors.githubUrl ? styles.inputError : {}),
            }}
            type="url"
            value={githubUrl}
            onChange={(e) => {
              setGithubUrl(e.target.value);
              setFieldErrors((p) => ({ ...p, githubUrl: '' }));
            }}
            placeholder="https://github.com/owner/repository"
            disabled={isProcessing}
            autoComplete="off"
          />
          {fieldErrors.githubUrl && (
            <span style={styles.fieldError}>{fieldErrors.githubUrl}</span>
          )}
        </>
      )}

      {/* PAT input (private only) */}
      {inputType === 'github-private' && (
        <>
          <label style={styles.label} htmlFor="pat">
            Personal Access Token
          </label>
          <input
            id="pat"
            style={{
              ...styles.input,
              ...(fieldErrors.githubToken ? styles.inputError : {}),
            }}
            type="password"
            value={githubToken}
            onChange={(e) => {
              setGithubToken(e.target.value);
              setFieldErrors((p) => ({ ...p, githubToken: '' }));
            }}
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            disabled={isProcessing}
            autoComplete="new-password"
          />
          {fieldErrors.githubToken && (
            <span style={styles.fieldError}>{fieldErrors.githubToken}</span>
          )}
          <p style={styles.hint}>
            Requires <code>repo</code> read scope. Token is sent only to your backend and never stored.
          </p>
        </>
      )}

      {/* ZIP upload */}
      {inputType === 'zip' && (
        <div style={styles.fileInputWrapper}>
          <label
            htmlFor="zip-file"
            style={{
              ...styles.fileInputLabel,
              ...(isDragOver ? styles.fileInputLabelActive : {}),
              ...(fieldErrors.zipFile ? { borderColor: '#a4262c' } : {}),
            }}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              const file = e.dataTransfer.files[0] || null;
              handleFileChange(file);
            }}
          >
            <span style={{ fontSize: '20px' }}>📁</span>
            {zipFile ? (
              <span style={styles.fileSelected}>✓ {zipFile.name}</span>
            ) : (
              <span>Click to select or drag & drop a <strong>.zip</strong> file</span>
            )}
          </label>
          <input
            id="zip-file"
            style={styles.fileInput}
            type="file"
            accept=".zip"
            onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
            disabled={isProcessing}
          />
          {fieldErrors.zipFile && (
            <span style={{ ...styles.fieldError, marginTop: '4px', display: 'block' }}>
              {fieldErrors.zipFile}
            </span>
          )}
        </div>
      )}

      {/* Submit button */}
      <button
        type="submit"
        style={{
          ...styles.submitBtn,
          ...(isProcessing ? styles.disabledBtn : {}),
        }}
        disabled={isProcessing}
      >
        {isProcessing ? 'Processing…' : 'Convert Repository'}
      </button>

      {/* Progress section */}
      {isProcessing && jobStatus && (
        <div style={styles.progressSection}>
          <div style={styles.progressLabel}>
            <span>{statusLabels[jobStatus.status] || 'Processing…'}</span>
            <span>{jobStatus.progress}%</span>
          </div>
          <div style={styles.progressBarTrack}>
            <div
              style={{
                ...styles.progressBarFill,
                width: `${jobStatus.progress}%`,
              }}
            />
          </div>
          <p style={styles.statusMessage}>
            This may take a moment depending on the repository size.
          </p>
        </div>
      )}

      {/* Initial pending state (before first status update) */}
      {isProcessing && !jobStatus && (
        <div style={styles.progressSection}>
          <div style={styles.progressLabel}>
            <span>Submitting job…</span>
            <span>0%</span>
          </div>
          <div style={styles.progressBarTrack}>
            <div style={{ ...styles.progressBarFill, width: '5%' }} />
          </div>
        </div>
      )}

      {/* Error */}
      {globalError && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {globalError}
        </div>
      )}

      {/* Failed job error */}
      {jobStatus?.status === 'failed' && (
        <div style={styles.errorBox}>
          <strong>Conversion failed:</strong>{' '}
          {jobStatus.error || 'An unknown error occurred during processing.'}
        </div>
      )}
    </form>
  );
};

export default ConvertForm;
