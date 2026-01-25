import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import Files from "./pages/files/Files";
import Review from "./pages/review/Review";
import RulesPage from "./pages/rules/RulesPage";
import LandingPage from "./pages/landing/LandingPage";
import type { ThemeMode } from './theme'

type AppProps = {
  mode: ThemeMode
  onToggleMode: () => void
}

function App({ mode, onToggleMode }: AppProps) {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/*"
        element={
          <AppShell mode={mode} onToggleMode={onToggleMode}>
            <AuthorizedPages />
          </AppShell>
        }
      />
    </Routes>
  );
}

function AuthorizedPages() {
  return (
    <Routes>
      <Route path="/files" element={<Files />} />
      <Route path="/review" element={<Review />} />
      <Route path="/rules" element={<RulesPage />} />
    </Routes>
  );
}

export default App;
