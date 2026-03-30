import React, { useState } from 'react';
import { FilePreview as FilePreviewType } from '../types';

interface Props {
  files: FilePreviewType[];
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '16px',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#323130',
    marginBottom: '8px',
  },
  toggleButton: {
    background: 'none',
    border: 'none',
    color: '#0078D4',
    cursor: 'pointer',
    fontSize: '13px',
    padding: '0',
    textDecoration: 'underline',
    marginBottom: '8px',
    display: 'block',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '12px',
  },
  th: {
    textAlign: 'left',
    padding: '6px 10px',
    backgroundColor: '#f3f2f1',
    borderBottom: '2px solid #edebe9',
    color: '#605e5c',
    fontWeight: 600,
  },
  td: {
    padding: '6px 10px',
    borderBottom: '1px solid #edebe9',
    color: '#323130',
    wordBreak: 'break-all' as const,
  },
  originalFile: {
    color: '#a4262c',
    fontFamily: 'monospace',
  },
  convertedFile: {
    color: '#107c10',
    fontFamily: 'monospace',
  },
  arrow: {
    color: '#605e5c',
    textAlign: 'center' as const,
  },
  empty: {
    color: '#605e5c',
    fontStyle: 'italic',
    fontSize: '13px',
    padding: '8px 0',
  },
};

const FilePreview: React.FC<Props> = ({ files }) => {
  const [expanded, setExpanded] = useState(false);

  if (!files || files.length === 0) {
    return (
      <div style={styles.container}>
        <p style={styles.empty}>No file preview available.</p>
      </div>
    );
  }

  const displayFiles = expanded ? files : files.slice(0, 5);

  return (
    <div style={styles.container}>
      <p style={styles.title}>File Conversion Preview ({files.length} files)</p>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Original File</th>
            <th style={{ ...styles.th, width: '30px', textAlign: 'center' }}>→</th>
            <th style={styles.th}>Converted File</th>
          </tr>
        </thead>
        <tbody>
          {displayFiles.map((file, index) => (
            <tr key={index}>
              <td style={{ ...styles.td, ...styles.originalFile }}>{file.original}</td>
              <td style={{ ...styles.td, ...styles.arrow }}>→</td>
              <td style={{ ...styles.td, ...styles.convertedFile }}>{file.converted}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {files.length > 5 && (
        <button style={styles.toggleButton} onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show less' : `Show all ${files.length} files`}
        </button>
      )}
    </div>
  );
};

export default FilePreview;
