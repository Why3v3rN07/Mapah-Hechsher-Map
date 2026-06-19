import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getHechshers } from '../api/hechshers';
import { getPreferences } from '../api/me';
import { useAuth } from '../contexts/AuthContext';

const SAVE_DEBOUNCE_MS = 800;

export default function PreferencesPage() {
  const { updatePreferences } = useAuth();
  const [allHechshers, setAllHechshers] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'error'
  const debounceRef = useRef(null);
  // Keep a ref to latest selectedIds so the debounced save always uses fresh value
  const selectedIdsRef = useRef(selectedIds);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        setLoading(true);
        const [{ data: hechshersData }, { data: prefsData }] = await Promise.all([
          getHechshers(),
          getPreferences(),
        ]);
        if (!active) return;
        setAllHechshers(Array.isArray(hechshersData?.items) ? hechshersData.items : []);
        const ids = Array.isArray(prefsData?.hechsher_ids) ? prefsData.hechsher_ids : [];
        setSelectedIds(ids);
        selectedIdsRef.current = ids;
      } catch {
        // silently fall through — user will see empty list
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, []);

  const save = useCallback(async (ids) => {
    try {
      setSaveStatus('saving');
      await updatePreferences(ids);
      setSaveStatus('saved');
    } catch {
      setSaveStatus('error');
    }
  }, [updatePreferences]);

  const toggle = (id) => {
    // Compute next state synchronously, outside the updater
    setSelectedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      selectedIdsRef.current = next;
      return next;
    });
    // Side-effects live outside the updater so they run exactly once
    clearTimeout(debounceRef.current);
    setSaveStatus('idle');
    debounceRef.current = setTimeout(() => save(selectedIdsRef.current), SAVE_DEBOUNCE_MS);
  };

  // Clean up on unmount
  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return allHechshers;
    return allHechshers.filter((h) => {
      if (h.hechsher_display_name.toLowerCase().includes(q)) return true;
      return Array.isArray(h.aliases) && h.aliases.some((a) => a.toLowerCase().includes(q));
    });
  }, [allHechshers, search]);

  const statusLabel =
    saveStatus === 'saving' ? '💾 Saving…' :
    saveStatus === 'saved'  ? '✓ Saved'   :
    saveStatus === 'error'  ? '⚠ Save failed' :
    '';

  return (
    <main className="page-wrap">
      <h1>Hechsher Preferences</h1>
      <p className="muted">Choose the hechshers you follow. The map will default to these when you are logged in.</p>

      <section className="page-card prefs-card">
        <div className="prefs-header">
          <input
            className="input prefs-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or alias…"
            aria-label="Search hechshers"
          />
          {statusLabel && (
            <span className={`prefs-save-status prefs-save-status--${saveStatus}`}>
              {statusLabel}
            </span>
          )}
        </div>

        {loading ? (
          <p>Loading…</p>
        ) : (
          <div className="prefs-list" role="group" aria-label="Hechsher preferences list">
            {filtered.map((h) => (
              <label key={h.hechsher_id} className="prefs-row">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(h.hechsher_id)}
                  onChange={() => toggle(h.hechsher_id)}
                />
                {h.hechsher_symbol && <img src={h.hechsher_symbol} alt="" className="prefs-icon" />}
                <div className="prefs-label">
                  <span className="prefs-name">{h.hechsher_display_name}</span>
                  {Array.isArray(h.aliases) && h.aliases.length > 0 && (
                    <span className="prefs-aliases">{h.aliases.join(' · ')}</span>
                  )}
                </div>
              </label>
            ))}
            {!filtered.length && <p className="muted" style={{padding:'0.75rem'}}>No hechshers match your search.</p>}
          </div>
        )}
      </section>
    </main>
  );
}

