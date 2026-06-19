import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Navbar.css';

export default function Navbar({ onOpenAuth, onOpenSubmit }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">🗺️ Mapah</Link>

      <div className="navbar-actions">
        <button className="btn btn-ghost" onClick={onOpenSubmit}>
          + Add Place
        </button>

        {user ? (
          <>
            {user.user_status === 'admin' && (
              <Link to="/admin" className="btn btn-ghost">Admin</Link>
            )}
            <Link to="/preferences" className="btn btn-ghost">Preferences</Link>
            <Link to="/my-submissions" className="btn btn-ghost">My Submissions</Link>
            <span className="navbar-username">{user.user_name}</span>
            <button className="btn btn-secondary" onClick={handleLogout}>Log out</button>
          </>
        ) : (
          <button className="btn btn-primary" onClick={onOpenAuth}>Sign in</button>
        )}
      </div>
    </nav>
  );
}

