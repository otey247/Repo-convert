import React, { useState } from 'react';
import { publishToGithub } from '../services/api';

interface Props {
  jobId: string;
  onClose: () => void;
}

const overlay: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0,0,0,0.45)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const modal: React.CSSProperties = {
  backgroundColor: '#fff',
  borderRadius: '8px',
  padding: '28px 32px',
  width: '460px',
  maxWidth: '95vw',
  boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
};

const styles: Record<string, React.CSSProperties> = {
  title: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#201f1e',
    marginBottom: '4px',
  },
  subtitle: {
    fontSize: '13px',
    color: '#605e5c',
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: '#323130',
    marginBottom: '4px',
  },
  input: {
    width: '100%',
    padding: '8px 10px',
    fontSize: '14px',
    border: '1px solid #8a8886',
    borderRadius: '4px',
    marginBottom: '14px',
    boxSizing: 'border-box' as const,
    outline: 'none',
  },
  inputFocus: {
    border: '1px solid #0078D4',
  },
  buttonRow: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'flex-end',
    marginTop: '8px',
  },
  primaryBtn: {
    backgroundColor: '#0078D4',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '9px 20px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryBtn: {
    backgroundColor: '#fff',
    color: '#323130',
    border: '1px solid #8a8886',
    borderRadius: '4px',
    padding: '9px 20px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  disabledBtn: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  error: {
    color: '#a4262c',
    fontSize: '13px',
    marginBottom: '10px',
    padding: '8px 10px',
    backgroundColor: '#fde7e9',
    borderRadius: '4px',
    borderLeft: '3px solid #a4262c',
  },
  success: {
    color: '#107c10',
    fontSize: '13px',
    marginBottom: '10px',
    padding: '10px 12px',
    backgroundColor: '#dff6dd',
    borderRadius: '4px',
    borderLeft: '3px solid #107c10',
  },
  link: {
    color: '#0078D4',
    textDecoration: 'underline',
    wordBreak: 'break-all' as const,
  },
  requiredStar: {
    color: '#a4262c',
    marginLeft: '2px',
  },
  hint: {
    fontSize: '11px',
    color: '#605e5c',
    marginTop: '-10px',
    marginBottom: '12px',
  },
};

const PublishDialog: React.FC<Props> = ({ jobId, onClose }) => {
  const [repoName, setRepoName] = useState('');
  const [token, setToken] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [repoUrl, setRepoUrl] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!repoName.trim()) {
      setError('Repository name is required.');
      return;
    }
    if (!token.trim()) {
      setError('GitHub token is required.');
      return;
    }

    setLoading(true);
    try {
      const result = await publishToGithub(jobId, repoName.trim(), token.trim(), description.trim());
      if (result.repo_url) {
        setRepoUrl(result.repo_url);
      } else {
        setError('Publish failed. Please try again.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to publish to GitHub.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={modal} role="dialog" aria-modal="true" aria-labelledby="publish-dialog-title">
        <h2 style={styles.title} id="publish-dialog-title">Publish to GitHub</h2>
        <p style={styles.subtitle}>Create a new repository with the converted files.</p>

        {repoUrl ? (
          <div>
            <div style={styles.success}>
              <strong>Published successfully!</strong><br />
              Repository created:{' '}
              <a href={repoUrl} target="_blank" rel="noopener noreferrer" style={styles.link}>
                {repoUrl}
              </a>
            </div>
            <div style={styles.buttonRow}>
              <button style={styles.primaryBtn} onClick={onClose}>Close</button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && <div style={styles.error}>{error}</div>}

            <label style={styles.label} htmlFor="repo-name">
              Repository Name<span style={styles.requiredStar}>*</span>
            </label>
            <input
              id="repo-name"
              style={styles.input}
              type="text"
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              placeholder="my-converted-docs"
              disabled={loading}
              autoComplete="off"
              autoFocus
            />

            <label style={styles.label} htmlFor="github-token">
              GitHub Personal Access Token<span style={styles.requiredStar}>*</span>
            </label>
            <input
              id="github-token"
              style={styles.input}
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              disabled={loading}
              autoComplete="new-password"
            />
            <p style={styles.hint}>Requires <code>repo</code> scope. Token is never stored.</p>

            <label style={styles.label} htmlFor="description">
              Description <span style={{ fontWeight: 400, color: '#605e5c' }}>(optional)</span>
            </label>
            <input
              id="description"
              style={styles.input}
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Converted docs for Microsoft 365 Chat"
              disabled={loading}
            />

            <div style={styles.buttonRow}>
              <button
                type="button"
                style={styles.secondaryBtn}
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{ ...styles.primaryBtn, ...(loading ? styles.disabledBtn : {}) }}
                disabled={loading}
              >
                {loading ? 'Publishing…' : 'Publish'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default PublishDialog;
