import { useState } from 'react';
import './Disclaimer.css';

export default function Disclaimer() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="disclaimer-snackbar">
      <span className="disclaimer-text">
        ⚠️ Mapah takes no responsibility for the accuracy of this information. Always double check.
      </span>
      <button className="disclaimer-close" onClick={() => setDismissed(true)} aria-label="Dismiss disclaimer">
        ✕
      </button>
    </div>
  );
}


