/**
 * Unified search: searches both places and locations, shows results in one dropdown.
 * Markers only update when user selects from dropdown or presses Enter.
 */
import { useEffect, useRef, useState } from 'react';
import { searchLocations } from '../../api/locations';
import { getPlaces } from '../../api/places';
import './UnifiedSearch.css';

const DEBOUNCE_MS = 120;
const CACHE_LIMIT = 25;

function normalizeQuery(value) {
  return String(value ?? '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function mergeUnique(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = item.type === 'location'
      ? `location:${item.place_name}:${item.lat}:${item.lng}`
      : `place:${item.place_id ?? item.place_name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export default function UnifiedSearch({ valuePlaceName, valueLocationName, onSelectPlace, onSelectLocation, onClear }) {
  // Use location name if set, otherwise place name
  const currentValue = valueLocationName || valuePlaceName;
  const [query, setQuery] = useState(currentValue ?? '');
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);
  const containerRef = useRef(null);
  const cacheRef = useRef(new Map());
  const requestSeqRef = useRef(0);

  useEffect(() => {
    setQuery(currentValue ?? '');
  }, [currentValue]);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    const normalized = normalizeQuery(query);

    if (!normalized) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    const cached = cacheRef.current.get(normalized);
    if (cached) {
      setSuggestions(cached);
      setOpen(true);
      return;
    }

    setSuggestions([]);
    setOpen(false);

    debounceRef.current = setTimeout(async () => {
      const requestSeq = ++requestSeqRef.current;
      let placeItems = [];
      let locationItems = [];

      const applyResults = () => {
        if (requestSeq !== requestSeqRef.current) return;
        const merged = mergeUnique([...placeItems, ...locationItems]);
        cacheRef.current.set(normalized, merged);
        if (cacheRef.current.size > CACHE_LIMIT) {
          const oldestKey = cacheRef.current.keys().next().value;
          cacheRef.current.delete(oldestKey);
        }
        setSuggestions(merged);
        setOpen(merged.length > 0);
      };

      getPlaces({ q: query })
        .then(({ data }) => {
          placeItems = (data?.items || []).map((item) => ({ type: 'place', ...item }));
          applyResults();
        })
        .catch(() => {
          placeItems = [];
          applyResults();
        });

      searchLocations({ q: query, limit: 8 })
        .then(({ data }) => {
          locationItems = (data?.items || []).map((item) => ({ type: 'location', ...item }));
          applyResults();
        })
        .catch(() => {
          locationItems = [];
          applyResults();
        });
    }, DEBOUNCE_MS);

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

  const select = (item) => {
    const normalized = normalizeQuery(item.place_name);
    if (normalized) {
      cacheRef.current.set(normalized, [item]);
    }
    if (item.type === 'place') {
      setQuery(item.place_name);
      onSelectPlace?.(item.place_name, item.lat, item.lng);
    } else if (item.type === 'location') {
      setQuery(item.place_name);
      onSelectLocation?.(item.place_name, item.lat, item.lng);
    }
    setSuggestions([]);
    setOpen(false);
  };

  const resolveTypedLocation = async () => {
    const typed = query.trim();
    if (!typed) return;

    const normalized = normalizeQuery(typed);
    const cached = cacheRef.current.get(normalized);
    const cachedLocation = cached?.find((item) => item.type === 'location' && Number.isFinite(item.lat) && Number.isFinite(item.lng));
    if (cachedLocation) {
      const resolvedName = cachedLocation.place_name || typed;
      setQuery(resolvedName);
      onSelectLocation?.(resolvedName, cachedLocation.lat, cachedLocation.lng);
      setSuggestions([]);
      setOpen(false);
      return;
    }

    try {
      const { data } = await searchLocations({ q: typed, limit: 1 });
      const first = data?.items?.[0];
      if (first && Number.isFinite(first.lat) && Number.isFinite(first.lng)) {
        const resolvedName = first.place_name || typed;
        setQuery(resolvedName);
        onSelectLocation?.(resolvedName, first.lat, first.lng);
        setSuggestions([]);
        setOpen(false);
        return;
      }
    } catch {
      // Fall back to backend free-text location_query behavior.
    }

    onSelectLocation?.(typed, null, null);
    setOpen(false);
  };

  const handleKeyDown = async (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      // If there's a selected suggestion, use it; otherwise attempt to search as-is
      if (suggestions.length > 0) {
        // Select the first suggestion on Enter
        select(suggestions[0]);
      } else if (query.trim()) {
        await resolveTypedLocation();
      }
    }
  };

  const clear = () => {
    setQuery('');
    setSuggestions([]);
    setOpen(false);
    onClear?.();
  };

  return (
    <div className="unified-search" ref={containerRef}>
      <div className="unified-search-input-wrap">
        <input
          className="input"
          placeholder="Search places or locations…"
          value={query}
          onChange={(e) => {
            const next = e.target.value;
            setQuery(next);
            if (!next) {
              // User cleared the input - only close dropdown, don't clear filters
              // filters will only change on explicit selection or clear button click
              setSuggestions([]);
              setOpen(false);
            }
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
        />
        {query && (
          <button className="unified-clear-btn" onClick={clear} aria-label="Clear">×</button>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="unified-suggestions">
          {suggestions.map((item, idx) => {
            const key = `${item.type}-${item.place_id || idx}`;
            return (
              <li
                key={key}
                className={`unified-suggestion unified-suggestion--${item.type}`}
                onMouseDown={() => select(item)}
              >
                <span className="suggestion-type">{item.type === 'place' ? '📍' : '🗺️'}</span>
                <div className="suggestion-info">
                  <span className="suggestion-name">{item.place_name}</span>
                  {item.street_address && (
                    <span className="suggestion-address">{item.street_address}</span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}



