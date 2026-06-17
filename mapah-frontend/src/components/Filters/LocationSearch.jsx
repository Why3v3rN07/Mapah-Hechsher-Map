/**
 * Location typeahead: searches by address/city/neighborhood, shows location suggestions.
 */
import { useEffect, useRef, useState } from 'react';
import { searchLocations } from '../../api/locations';
import './LocationSearch.css';

export default function LocationSearch({ value, onChange }) {
  const [query, setQuery] = useState(value ?? '');
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const { data } = await searchLocations({ q: query });
        setSuggestions(data.items || []);
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

  const select = (location) => {
    setQuery(location.place_name);
    setOpen(false);
    onChange(location.place_name, location.lat, location.lng);
  };

  const clear = () => {
    setQuery('');
    setSuggestions([]);
    setOpen(false);
    onChange('');
  };

  return (
    <div className="location-search" ref={containerRef}>
      <div className="location-search-input-wrap">
        <input
          className="input"
          placeholder="City, address…"
          value={query}
          onChange={(e) => {
            const next = e.target.value;
            setQuery(next);
            if (!next) {
              setSuggestions([]);
              setOpen(false);
              onChange('');
            }
          }}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
        />
        {query && (
          <button className="location-clear-btn" onClick={clear} aria-label="Clear">×</button>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="location-suggestions">
          {suggestions.map((location, idx) => (
            <li key={idx} className="location-suggestion" onMouseDown={() => select(location)}>
              <span className="suggestion-name">{location.place_name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


