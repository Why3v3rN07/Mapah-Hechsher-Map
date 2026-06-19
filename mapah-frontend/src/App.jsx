import { useEffect, useRef, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import Navbar from './components/Layout/Navbar';
import Disclaimer from './components/Layout/Disclaimer';
import AuthModal from './components/Auth/AuthModal';
import SubmissionModal from './components/Submission/SubmissionModal';
import HomePage from './pages/HomePage';
import AdminPage from './pages/AdminPage';
import MySubmissionsPage from './pages/MySubmissionsPage';
import PreferencesPage from './pages/PreferencesPage';
import { useAuth } from './contexts/AuthContext';
import './components/Layout/Header.css';
import './App.css';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-wrap">Loading...</div>;
  if (!user) return <Navigate to="/" replace />;
  return children;
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-wrap">Loading...</div>;
  if (!user || user.user_status !== 'admin') return <Navigate to="/" replace />;
  return children;
}

function App() {
  const [authOpen, setAuthOpen] = useState(false);
  const [submissionMode, setSubmissionMode] = useState(null); // new_place | edit | tag_update
  const [submissionPlace, setSubmissionPlace] = useState(null);
  const headerRef = useRef(null);
  const [headerHeight, setHeaderHeight] = useState(64);

  const openSubmission = (mode = 'new_place', place = null) => {
    setSubmissionMode(mode);
    setSubmissionPlace(place);
  };
  const closeSubmission = () => {
    setSubmissionMode(null);
    setSubmissionPlace(null);
  };

  useEffect(() => {
    const headerEl = headerRef.current;
    if (!headerEl) return undefined;

    const updateHeight = () => {
      const next = Math.max(0, Math.round(headerEl.getBoundingClientRect().height));
      setHeaderHeight(next || 64);
    };

    updateHeight();

    let observer;
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(updateHeight);
      observer.observe(headerEl);
    } else {
      window.addEventListener('resize', updateHeight);
    }

    return () => {
      observer?.disconnect();
      window.removeEventListener('resize', updateHeight);
    };
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty('--app-header-height', `${headerHeight}px`);
  }, [headerHeight]);

  return (
    <>
      <div className="header-container" ref={headerRef}>
        <Disclaimer />
        <Navbar
          onOpenAuth={() => setAuthOpen(true)}
          onOpenSubmit={() => openSubmission('new_place', null)}
        />
      </div>
      <main className="app-main" style={{ marginTop: `${headerHeight}px` }}>
        <Routes>
          <Route
            path="/"
            element={
              <HomePage
                openGlobalSubmission={openSubmission}
              />
            }
          />

          <Route
            path="/my-submissions"
            element={
              <ProtectedRoute>
                <MySubmissionsPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/preferences"
            element={
              <ProtectedRoute>
                <PreferencesPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminPage />
              </AdminRoute>
            }
          />
        </Routes>
      </main>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
      {submissionMode !== null && (
        <SubmissionModal
          open
          mode={submissionMode || 'new_place'}
          place={submissionPlace}
          onClose={closeSubmission}
          onSubmitted={() => {}}
        />
      )}
    </>
  );
}

export default App;
