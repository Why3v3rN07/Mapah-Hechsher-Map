/**
 * Hechsher typeahead: searches by name + alias, shows icon + display name.
 */
import { useEffect, useRef, useState } from 'react';
import { searchHechshers } from '../../api/hechshers';
import './HechsherSearch.css';

export default function HechsherSearch({ value, onChange }) {
  const [query, setQuery] = useState(value?.hechsher_display_name ?? '');
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
    setQuery(h.hechsher_display_name);
    setOpen(false);
    onChange(h);
  };

  const clear = () => {
    setQuery('');
    setOpen(false);
    onChange(null);
  };

  return (
    <div className="hechsher-search" ref={containerRef}>
      <div className="hechsher-search-input-wrap">
        <input
          className="input"
          placeholder="Search hechsher…"
          value={query}
          onChange={(e) => {
            const next = e.target.value;
            setQuery(next);
            if (!next) {
              setSuggestions([]);
              clear();
            }
          }}
          onFocus={() => suggestions.length && setOpen(true)}
        />
        {query && (
          <button className="hechsher-clear-btn" onClick={clear} aria-label="Clear">×</button>
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



