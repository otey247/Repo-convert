import React, { useState, useEffect, useCallback } from 'react';
import { ConversionSummary as ConversionSummaryType, FilePreview as FilePreviewType } from '../types';
import { downloadZip, getFilePreview } from '../services/api';
import FilePreview from './FilePreview';
import PublishDialog from './PublishDialog';

interface Props {
  jobId: string;
  summary: ConversionSummaryType;
  onReset: () => void;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '8px',
  },
  successBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    backgroundColor: '#dff6dd',
    border: '1px solid #107c10',
    borderRadius: '6px',
    padding: '12px 16px',
    marginBottom: '20px',
  },
  checkIcon: {
    fontSize: '20px',
    color: '#107c10',
    flexShrink: 0,
  },
  successText: {
    fontSize: '14px',
    color: '#107c10',
    fontWeight: 600,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '20px',
  },
  statCard: {
    backgroundColor: '#f3f2f1',
    borderRadius: '6px',
    padding: '12px 16px',
  },
  statValue: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#0078D4',
    lineHeight: 1.1,
  },
  statLabel: {
    fontSize: '12px',
    color: '#605e5c',
    marginTop: '4px',
  },
  outputRepo: {
    fontSize: '14px',
    color: '#323130',
    marginBottom: '16px',
    padding: '10px 14px',
    backgroundColor: '#f3f2f1',
    borderRadius: '6px',
  },
  outputRepoLabel: {
    fontWeight: 600,
    color: '#605e5c',
    fontSize: '12px',
    display: 'block',
    marginBottom: '2px',
  },
  outputRepoName: {
    fontFamily: 'monospace',
    fontSize: '15px',
    color: '#201f1e',
  },
  section: {
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#323130',
    marginBottom: '6px',
  },
  listContainer: {
    backgroundColor: '#f3f2f1',
    borderRadius: '4px',
    padding: '8px 12px',
    maxHeight: '120px',
    overflowY: 'auto' as const,
  },
  listItem: {
    fontSize: '12px',
    fontFamily: 'monospace',
    color: '#605e5c',
    padding: '2px 0',
  },
  errorItem: {
    fontSize: '12px',
    fontFamily: 'monospace',
    color: '#a4262c',
    padding: '2px 0',
  },
  divider: {
    border: 'none',
    borderTop: '1px solid #edebe9',
    margin: '20px 0',
  },
  buttonRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    marginTop: '20px',
  },
  primaryBtn: {
    backgroundColor: '#0078D4',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '9px 18px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  secondaryBtn: {
    backgroundColor: '#fff',
    color: '#323130',
    border: '1px solid #8a8886',
    borderRadius: '4px',
    padding: '9px 18px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  ghostBtn: {
    backgroundColor: 'transparent',
    color: '#0078D4',
    border: '1px solid #0078D4',
    borderRadius: '4px',
    padding: '9px 18px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  copyFeedback: {
    fontSize: '12px',
    color: '#107c10',
    alignSelf: 'center',
  },
};

const ConversionSummary: React.FC<Props> = ({ jobId, summary, onReset }) => {
  const [previews, setPreviews] = useState<FilePreviewType[]>([]);
  const [showPublish, setShowPublish] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState('');

  useEffect(() => {
    getFilePreview(jobId)
      .then(setPreviews)
      .catch(() => {
        // Preview is optional, silently ignore errors
      });
  }, [jobId]);

  const handleDownload = useCallback(() => {
    downloadZip(jobId);
  }, [jobId]);

  const handleCopySummary = useCallback(() => {
    const lines = [
      `Repo-convert Summary`,
      `====================`,
      `Output Repo: ${summary.output_repo_name}`,
      `Total Files Scanned: ${summary.total_files}`,
      `Markdown Files Converted: ${summary.md_files_converted}`,
    ];

    if (summary.skipped_files.length > 0) {
      lines.push('', `Skipped Files (${summary.skipped_files.length}):`);
      summary.skipped_files.forEach((f) => lines.push(`  - ${f}`));
    }

    if (summary.errors.length > 0) {
      lines.push('', `Errors (${summary.errors.length}):`);
      summary.errors.forEach((e) => lines.push(`  - ${e}`));
    }

    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      setCopyFeedback('Copied!');
      setTimeout(() => setCopyFeedback(''), 2500);
    });
  }, [summary]);

  return (
    <div style={styles.container}>
      <div style={styles.successBanner}>
        <span style={styles.checkIcon}>✓</span>
        <span style={styles.successText}>Conversion completed successfully!</span>
      </div>

      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{summary.total_files}</div>
          <div style={styles.statLabel}>Files scanned</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{summary.md_files_converted}</div>
          <div style={styles.statLabel}>Markdown files converted</div>
        </div>
      </div>

      <div style={styles.outputRepo}>
        <span style={styles.outputRepoLabel}>OUTPUT REPOSITORY</span>
        <span style={styles.outputRepoName}>{summary.output_repo_name}</span>
      </div>

      {summary.skipped_files.length > 0 && (
        <div style={styles.section}>
          <p style={styles.sectionTitle}>
            Skipped Files ({summary.skipped_files.length})
          </p>
          <div style={styles.listContainer}>
            {summary.skipped_files.map((f, i) => (
              <div key={i} style={styles.listItem}>{f}</div>
            ))}
          </div>
        </div>
      )}

      {summary.errors.length > 0 && (
        <div style={styles.section}>
          <p style={styles.sectionTitle}>
            Errors ({summary.errors.length})
          </p>
          <div style={styles.listContainer}>
            {summary.errors.map((e, i) => (
              <div key={i} style={styles.errorItem}>{e}</div>
            ))}
          </div>
        </div>
      )}

      {previews.length > 0 && (
        <>
          <hr style={styles.divider} />
          <FilePreview files={previews} />
        </>
      )}

      <hr style={styles.divider} />

      <div style={styles.buttonRow}>
        <button style={styles.primaryBtn} onClick={handleDownload}>
          ↓ Download ZIP
        </button>
        <button style={styles.secondaryBtn} onClick={handleCopySummary}>
          Copy Summary
        </button>
        <button style={styles.ghostBtn} onClick={() => setShowPublish(true)}>
          Publish to GitHub
        </button>
        <button style={styles.secondaryBtn} onClick={onReset}>
          Convert Another
        </button>
        {copyFeedback && <span style={styles.copyFeedback}>{copyFeedback}</span>}
      </div>

      {showPublish && (
        <PublishDialog jobId={jobId} onClose={() => setShowPublish(false)} />
      )}
    </div>
  );
};

export default ConversionSummary;
