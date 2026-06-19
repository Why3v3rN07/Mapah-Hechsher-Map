/**
 * Hechsher typeahead with multi-select: searches by name + alias, shows icon + display name.
 * Allows selecting multiple hechshers; selected items appear as removable pills.
 */
import { useEffect, useRef, useState } from 'react';
import { searchHechshers } from '../../api/hechshers';
import './HechsherSearch.css';

export default function HechsherSearch({ value = [], onChange }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!query.trim()) {
      return undefined;
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const { data } = await searchHechshers(query);
        setSuggestions(data.items);
        setOpen(true);
      } catch {
        setSuggestions([]);
      }
    }, 200);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (!containerRef.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const select = (h) => {
    // Check if already selected
    const isSelected = value.some((sel) => sel.hechsher_id === h.hechsher_id);
    if (!isSelected) {
      onChange([...value, h]);
    }
    setQuery('');
    setOpen(false);
    setSuggestions([]);
  };

  const remove = (hechsherId) => {
    onChange(value.filter((h) => h.hechsher_id !== hechsherId));
  };

  const clear = () => {
    setQuery('');
    setOpen(false);
    onChange([]);
    setSuggestions([]);
  };
  return (
    <div className="hechsher-search" ref={containerRef}>
      <div className="hechsher-search-input-wrap">
        {/* Display selected hechshers as pills */}
        {value.length > 0 && (
          <div className="hechsher-pills">
            {value.map((h) => (
              <div key={h.hechsher_id} className="hechsher-pill">
                {h.hechsher_symbol && (
                  <img src={h.hechsher_symbol} alt="" className="pill-icon" />
                )}
                <span className="pill-name">{h.hechsher_display_name}</span>
                <button
                  className="pill-remove"
                  onClick={() => remove(h.hechsher_id)}
                  aria-label="Remove"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        <input
          className="input"
          placeholder="Search hechsher…"
          value={query}
          onChange={(e) => {
            const next = e.target.value;
            setQuery(next);
            if (!next) setSuggestions([]);
          }}
          onFocus={() => suggestions.length && setOpen(true)}
        />
        {value.length > 0 && (
          <button className="hechsher-clear-btn" onClick={clear} aria-label="Clear all">Clear all</button>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="hechsher-suggestions">
          {suggestions.map((h) => (
            <li key={h.hechsher_id} className="hechsher-suggestion" onMouseDown={() => select(h)}>
              {h.hechsher_symbol && (
                <img src={h.hechsher_symbol} alt="" className="suggestion-icon" />
              )}
              <div>
                <span className="suggestion-name">{h.hechsher_display_name}</span>
                {h.matched_alias && (
                  <span className="suggestion-alias"> ({h.matched_alias})</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}



