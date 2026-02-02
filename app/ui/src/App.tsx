import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import Files from "./pages/files/Files";
import Review from "./pages/review/Review";
import RulesPage from "./pages/rules/RulesPage";
import LandingPage from "./pages/landing/LandingPage";
import PrivacyPolicyPage from './pages/legal/PrivacyPolicyPage'
import TermsOfServicePage from './pages/legal/TermsOfServicePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/privacy" element={<PrivacyPolicyPage />} />
      <Route path="/terms" element={<TermsOfServicePage />} />
      <Route
        path="/*"
        element={
          <AppShell>
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
