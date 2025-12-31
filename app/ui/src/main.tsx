import { FluentProvider } from '@fluentui/react-components';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router } from 'react-router-dom';
import App from "./App";
import './index.css';
import { getAppTheme, ThemeMode } from './theme';
import { useEffect, useState } from 'react';

const root = ReactDOM.createRoot(
    document.getElementById("root") as HTMLElement
);

function Root() {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('themeMode') as ThemeMode | null
    return saved === 'light' || saved === 'dark' ? saved : 'dark'
  })

  useEffect(() => {
    localStorage.setItem('themeMode', mode)
    document.body.dataset.theme = mode
  }, [mode])

  return (
    <Router>
      <FluentProvider theme={getAppTheme(mode)}>
        <App mode={mode} onToggleMode={() => setMode((m) => (m === 'dark' ? 'light' : 'dark'))} />
      </FluentProvider>
    </Router>
  )
}

root.render(<Root />);
