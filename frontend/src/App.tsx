import React from 'react';
import ConvertForm from './components/ConvertForm';

const appStyles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#f3f2f1',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '40px 16px 60px',
    fontFamily:
      "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif",
  },
  header: {
    textAlign: 'center',
    marginBottom: '32px',
  },
  logo: {
    fontSize: '32px',
    marginBottom: '8px',
  },
  title: {
    fontSize: '26px',
    fontWeight: 700,
    color: '#201f1e',
    margin: '0 0 6px',
  },
  subtitle: {
    fontSize: '14px',
    color: '#605e5c',
    margin: 0,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '10px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.10)',
    padding: '32px 36px',
    width: '100%',
    maxWidth: '580px',
  },
  footer: {
    marginTop: '24px',
    fontSize: '12px',
    color: '#a19f9d',
    textAlign: 'center',
  },
};

const App: React.FC = () => {
  return (
    <div style={appStyles.page}>
      <header style={appStyles.header}>
        <div style={appStyles.logo}>📄</div>
        <h1 style={appStyles.title}>Repo-convert</h1>
        <p style={appStyles.subtitle}>
          Convert repository Markdown files to plain text for Microsoft 365 Chat agents
        </p>
      </header>

      <main style={appStyles.card}>
        <ConvertForm />
      </main>

      <footer style={appStyles.footer}>
        Repo-convert &mdash; converts .md files to M365-compatible plain text
      </footer>
    </div>
  );
};

export default App;
