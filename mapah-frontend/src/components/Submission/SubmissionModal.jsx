import { useRef, useState } from 'react';
import { createHechsher, searchHechshers } from '../../api/hechshers';
import { reverseGeocode, searchLocations } from '../../api/locations';
import { submitPlace, tagPlace } from '../../api/submissions';
import './SubmissionModal.css';

function splitCsv(value) {
  return value
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);
}

export default function SubmissionModal({ open, onClose, mode = 'new_place', place = null, onSubmitted }) {
  const [placeName, setPlaceName] = useState(place?.place_name ?? '');
  const [otherNames, setOtherNames] = useState((place?.aliases ?? []).join(', '));
  const [streetAddress, setStreetAddress] = useState(place?.street_address ?? '');
  const [latitude, setLatitude] = useState(place?.latitude != null ? String(place.latitude) : '');
  const [longitude, setLongitude] = useState(place?.longitude != null ? String(place.longitude) : '');
  const [selectedAddress, setSelectedAddress] = useState(null);
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  const [selectedHechshers, setSelectedHechshers] = useState(place?.hechshers ?? []);
  const [hechsherQuery, setHechsherQuery] = useState('');
  const [hechsherSuggestions, setHechsherSuggestions] = useState([]);
  const [tags, setTags] = useState((place?.tags ?? []).join(', ') || 'restaurant');
  const [reason, setReason] = useState('');
  const [showNewHechsher, setShowNewHechsher] = useState(false);
  const [newHechsherName, setNewHechsherName] = useState('');
  const [newHechsherAliases, setNewHechsherAliases] = useState('');
  const [newHechsherIcon, setNewHechsherIcon] = useState(null);
  const [error, setError] = useState('');
  const [newHechsherError, setNewHechsherError] = useState('');
  const [newHechsherNotice, setNewHechsherNotice] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [creatingHechsher, setCreatingHechsher] = useState(false);
  const addressDebounceRef = useRef(null);
  const hechsherDebounceRef = useRef(null);

  if (!open) return null;

  const handleAddressInput = (nextValue) => {
    setStreetAddress(nextValue);
    setSelectedAddress(null);
    clearTimeout(addressDebounceRef.current);

    if (!nextValue.trim()) {
      setAddressSuggestions([]);
      return;
    }

    addressDebounceRef.current = setTimeout(async () => {
      try {
        const { data } = await searchLocations({ q: nextValue, limit: 8 });
        setAddressSuggestions(data?.items ?? []);
      } catch {
        setAddressSuggestions([]);
      }
    }, 220);
  };

  const pickAddressSuggestion = (item) => {
    setSelectedAddress(item);
    setStreetAddress(item.place_name || '');
    setLatitude(Number.isFinite(item.lat) ? String(item.lat) : '');
    setLongitude(Number.isFinite(item.lng) ? String(item.lng) : '');
    setAddressSuggestions([]);
  };

  const handleUseLocation = () => {
    setError('');
    navigator.geolocation?.getCurrentPosition(
      async ({ coords }) => {
        const nextLat = Number(coords.latitude);
        const nextLng = Number(coords.longitude);
        setLatitude(String(nextLat));
        setLongitude(String(nextLng));
        setSelectedAddress({ place_name: streetAddress || 'Detected location', lat: nextLat, lng: nextLng });
        try {
          const placeName = await reverseGeocode(nextLat, nextLng);
          if (placeName) {
            setStreetAddress(placeName);
            setSelectedAddress({ place_name: placeName, lat: nextLat, lng: nextLng });
          }
        } catch {
          // Keep coordinates even if reverse geocoding fails.
        }
      },
      () => setError('Location unavailable. Please enter coordinates manually.'),
      { timeout: 5000 },
    );
  };

  const handleHechsherSearch = (nextQuery) => {
    setHechsherQuery(nextQuery);
    clearTimeout(hechsherDebounceRef.current);

    if (!nextQuery.trim()) {
      setHechsherSuggestions([]);
      return;
    }

    hechsherDebounceRef.current = setTimeout(async () => {
      try {
        const { data } = await searchHechshers(nextQuery);
        setHechsherSuggestions(data?.items ?? []);
      } catch {
        setHechsherSuggestions([]);
      }
    }, 220);
  };

  const selectHechsher = (hechsher) => {
    if (selectedHechshers.some((h) => h.hechsher_id === hechsher.hechsher_id)) {
      setHechsherQuery('');
      setHechsherSuggestions([]);
      return;
    }
    setSelectedHechshers((prev) => [...prev, hechsher]);
    setHechsherQuery('');
    setHechsherSuggestions([]);
  };

  const removeHechsher = (hechsherId) => {
    setSelectedHechshers((prev) => prev.filter((h) => h.hechsher_id !== hechsherId));
  };

  const submitNewHechsher = async () => {
    setNewHechsherError('');
    setNewHechsherNotice('');
    if (!newHechsherName.trim()) {
      setNewHechsherError('Hechsher name is required.');
      return;
    }

    setCreatingHechsher(true);
    try {
      const formData = new FormData();
      formData.append('name', newHechsherName.trim());
      splitCsv(newHechsherAliases).forEach((alias) => formData.append('aliases', alias));
      if (newHechsherIcon) formData.append('icon', newHechsherIcon);

      const { data } = await createHechsher(formData);
      if (data?.hechsher?.hechsher_id) {
        selectHechsher(data.hechsher);
        setNewHechsherNotice('Hechsher added.');
        setShowNewHechsher(false);
      } else if (data?.spam_filter_result === 'flagged') {
        const reason = data?.moderation?.reason || 'It was flagged by AI moderation and sent to admin review.';
        setNewHechsherNotice(`Hechsher submitted for review and not added yet: ${reason}`);
      } else {
        setNewHechsherNotice('Hechsher submitted for review.');
      }
      setNewHechsherName('');
      setNewHechsherAliases('');
      setNewHechsherIcon(null);
    } catch (err) {
      setNewHechsherError(err?.response?.data?.message || 'Could not create hechsher');
    } finally {
      setCreatingHechsher(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      if (mode === 'tag_update') {
        await tagPlace(place.place_id, {
          tags: splitCsv(tags),
          reason,
        });
      } else {
        const hechsherIds = selectedHechshers
          .map((h) => Number(h.hechsher_id))
          .filter((id) => Number.isFinite(id));
        const hasCoords = latitude.trim() !== '' && longitude.trim() !== '';
        const hasSelectedAddress = Boolean(selectedAddress);
        const tagList = splitCsv(tags);

        if (!placeName.trim()) {
          throw new Error('Place name is required.');
        }
        if (!hechsherIds.length) {
          throw new Error('Select at least one hechsher.');
        }
        if (!hasSelectedAddress && !hasCoords) {
          throw new Error('Provide either a selected address or coordinates.');
        }
        if (streetAddress.trim() && !hasSelectedAddress && !hasCoords) {
          throw new Error('Choose an address suggestion from the list.');
        }

        await submitPlace({
          submission_type: mode,
          place_id: mode === 'edit' ? place?.place_id : null,
          place_name: placeName.trim(),
          aliases: splitCsv(otherNames),
          street_address: streetAddress.trim() || null,
          latitude: latitude ? Number(latitude) : null,
          longitude: longitude ? Number(longitude) : null,
          hechsher_ids: hechsherIds,
          tags: tagList.length ? tagList : ['restaurant'],
          source: latitude && longitude ? 'location_detect' : 'manual',
        });
      }
      onSubmitted?.();
      onClose();
    } catch (err) {
      const msg = err?.message || err?.response?.data?.message || err?.response?.data?.error || 'Submission failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const title = mode === 'new_place' ? 'Add Place' : mode === 'edit' ? 'Edit Place' : 'Tag Place';

  return (
    <div className="modal-backdrop">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header-row">
          <h2>{title}</h2>
          <button type="button" className="modal-x-btn" onClick={onClose} aria-label="Close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {mode !== 'tag_update' && (
            <>
              <label className="field-label">Place name</label>
              <input className="input" value={placeName} onChange={(e) => setPlaceName(e.target.value)} required />

              <label className="field-label">Other names (comma-separated)</label>
              <input
                className="input"
                value={otherNames}
                onChange={(e) => setOtherNames(e.target.value)}
                placeholder="Alt Name 1, Alt Name 2"
              />

              <label className="field-label">Address</label>
              <input
                className="input"
                value={streetAddress}
                onChange={(e) => handleAddressInput(e.target.value)}
                placeholder="Start typing and select one suggestion"
              />
              {addressSuggestions.length > 0 && (
                <ul className="submission-suggestions">
                  {addressSuggestions.map((item, idx) => (
                    <li key={`${item.place_name}-${idx}`} onMouseDown={() => pickAddressSuggestion(item)}>
                      {item.place_name}
                    </li>
                  ))}
                </ul>
              )}
              <div className="field-hint">Use selected address or coordinates.</div>

              <div className="coord-row">
                <div>
                  <label className="field-label">Latitude</label>
                  <input className="input" value={latitude} onChange={(e) => setLatitude(e.target.value)} />
                </div>
                <div>
                  <label className="field-label">Longitude</label>
                  <input className="input" value={longitude} onChange={(e) => setLongitude(e.target.value)} />
                </div>
              </div>
              <button type="button" className="btn btn-ghost" onClick={handleUseLocation}>Use my location</button>

              <label className="field-label">Hechsher</label>
              {selectedHechshers.length > 0 && (
                <div className="selected-hechshers">
                  {selectedHechshers.map((h) => (
                    <button
                      type="button"
                      key={h.hechsher_id}
                      className="hechsher-chip"
                      onClick={() => removeHechsher(h.hechsher_id)}
                    >
                      {h.hechsher_display_name} ×
                    </button>
                  ))}
                </div>
              )}
              <input
                className="input"
                value={hechsherQuery}
                onChange={(e) => handleHechsherSearch(e.target.value)}
                placeholder="Search hechshers..."
              />
              {hechsherSuggestions.length > 0 && (
                <ul className="submission-suggestions">
                  {hechsherSuggestions.map((h) => (
                    <li key={h.hechsher_id} onMouseDown={() => selectHechsher(h)}>
                      {h.hechsher_display_name}
                      {h.matched_alias ? ` (${h.matched_alias})` : ''}
                    </li>
                  ))}
                </ul>
              )}
              <button type="button" className="btn btn-secondary" onClick={() => setShowNewHechsher(true)}>
                Add new hechsher
              </button>

              <label className="field-label">Tags (comma-separated)</label>
              <input className="input" value={tags} onChange={(e) => setTags(e.target.value)} />
            </>
          )}

          {mode === 'tag_update' && (
            <>
              <label className="field-label">Tags (comma-separated)</label>
              <input className="input" value={tags} onChange={(e) => setTags(e.target.value)} required />
              <label className="field-label">Reason</label>
              <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} />
            </>
          )}

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </form>

        {showNewHechsher && (
          <div className="inline-popup-backdrop" onClick={() => setShowNewHechsher(false)}>
            <div className="inline-popup-card" onClick={(e) => e.stopPropagation()}>
              <h3>Add New Hechsher</h3>
              <label className="field-label">Hechsher name</label>
              <input className="input" value={newHechsherName} onChange={(e) => setNewHechsherName(e.target.value)} />

              <label className="field-label">Aliases (comma-separated)</label>
              <input className="input" value={newHechsherAliases} onChange={(e) => setNewHechsherAliases(e.target.value)} />

              <label className="field-label">Icon</label>
              <input type="file" accept="image/*" onChange={(e) => setNewHechsherIcon(e.target.files?.[0] ?? null)} />

              {newHechsherError && <div className="form-error">{newHechsherError}</div>}
              {newHechsherNotice && <div className="field-hint">{newHechsherNotice}</div>}

              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowNewHechsher(false)}>Cancel</button>
                <button type="button" className="btn btn-primary" onClick={submitNewHechsher} disabled={creatingHechsher}>
                  {creatingHechsher ? 'Saving...' : 'Save hechsher'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

