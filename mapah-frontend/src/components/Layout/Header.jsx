import Disclaimer from './Disclaimer';
import Navbar from './Navbar';
import './Header.css';

export default function Header({ onOpenAuth, onOpenSubmit }) {
  return (
    <div className="header-container">
      <Disclaimer />
      <Navbar onOpenAuth={onOpenAuth} onOpenSubmit={onOpenSubmit} />
    </div>
  );
}


