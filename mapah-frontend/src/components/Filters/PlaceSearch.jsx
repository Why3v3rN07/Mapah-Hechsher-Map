/**
 * Place typeahead: searches by name, shows matching places in a dropdown.
 */
import { useEffect, useRef, useState } from 'react';
import { getPlaces } from '../../api/places';
import './PlaceSearch.css';

export default function PlaceSearch({ value, onChange }) {
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
        const { data } = await getPlaces({ q: query });
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

  const select = (place) => {
    setQuery(place.place_name);
    setOpen(false);
    onChange(place.place_name);
  };

  const clear = () => {
    setQuery('');
    setSuggestions([]);
    setOpen(false);
    onChange('');
  };

  return (
    <div className="place-search" ref={containerRef}>
      <div className="place-search-input-wrap">
        <input
          className="input"
          placeholder="Name…"
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
          <button className="place-clear-btn" onClick={clear} aria-label="Clear">×</button>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="place-suggestions">
          {suggestions.map((place) => (
            <li key={place.place_id} className="place-suggestion" onMouseDown={() => select(place)}>
              <div className="suggestion-info">
                <span className="suggestion-name">{place.place_name}</span>
                {place.street_address && (
                  <span className="suggestion-address">{place.street_address}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

