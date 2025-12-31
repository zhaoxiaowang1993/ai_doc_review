import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import Files from "./pages/files/Files";
import Review from "./pages/review/Review";
import type { ThemeMode } from './theme'

type AppProps = {
  mode: ThemeMode
  onToggleMode: () => void
}

function App({ mode, onToggleMode }: AppProps) {
  return (
    <AppShell mode={mode} onToggleMode={onToggleMode}>
      <Pages />
    </AppShell>
  );
}

function Pages() {
  return (
      <Routes>
          <Route path="/" element={<Files />} />
          <Route path="/review" element={<Review />} />
      </Routes>
  );
}

export default App;
