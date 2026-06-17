import { useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import Navbar from './components/Layout/Navbar';
import AuthModal from './components/Auth/AuthModal';
import SubmissionModal from './components/Submission/SubmissionModal';
import HomePage from './pages/HomePage';
import AdminPage from './pages/AdminPage';
import MySubmissionsPage from './pages/MySubmissionsPage';
import { useAuth } from './contexts/AuthContext';
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

  const openSubmission = (mode = 'new_place', place = null) => {
    setSubmissionMode(mode);
    setSubmissionPlace(place);
  };
  const closeSubmission = () => {
    setSubmissionMode(null);
    setSubmissionPlace(null);
  };

  return (
    <>
      <Navbar
        onOpenAuth={() => setAuthOpen(true)}
        onOpenSubmit={() => openSubmission('new_place', null)}
      />

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
          path="/admin"
          element={
            <AdminRoute>
              <AdminPage />
            </AdminRoute>
          }
        />
      </Routes>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
      <SubmissionModal
        open={submissionMode !== null}
        mode={submissionMode || 'new_place'}
        place={submissionPlace}
        onClose={closeSubmission}
        onSubmitted={() => {}}
      />
    </>
  );
}

export default App;
