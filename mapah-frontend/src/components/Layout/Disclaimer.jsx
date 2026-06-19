import { useState } from 'react';
import './Disclaimer.css';

export default function Disclaimer() {
  const [dismissed, setDismissed] = useState(false);

  const handleDismiss = () => {
    setDismissed(true);
    window.dispatchEvent(new Event('resize'));
  };

  if (dismissed) return null;

  return (
    <div className="disclaimer-snackbar">
      <span className="disclaimer-text">
        ⚠️ Mapah takes no responsibility for the accuracy of this information. Always double check.
      </span>
      <button className="disclaimer-close" onClick={handleDismiss} aria-label="Dismiss disclaimer">
        ✕
      </button>
    </div>
  );
}


