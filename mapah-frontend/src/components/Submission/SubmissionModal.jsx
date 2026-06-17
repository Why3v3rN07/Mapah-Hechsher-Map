import { useEffect, useState } from 'react';
import { submitPlace, tagPlace } from '../../api/submissions';
import './SubmissionModal.css';

function splitCsv(value) {
  return value
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);
}

function splitCsvNums(value) {
  return splitCsv(value).map((v) => Number(v)).filter((n) => !Number.isNaN(n));
}

export default function SubmissionModal({ open, onClose, mode = 'new_place', place = null, onSubmitted }) {
  const [placeName, setPlaceName] = useState('');
  const [streetAddress, setStreetAddress] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [hechsherIds, setHechsherIds] = useState('');
  const [tags, setTags] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (!place) {
      setPlaceName('');
      setStreetAddress('');
      setLatitude('');
      setLongitude('');
      setHechsherIds('');
      setTags('');
      setReason('');
      return;
    }

    setPlaceName(place.place_name ?? '');
    setStreetAddress(place.street_address ?? '');
    setLatitude(place.latitude ?? '');
    setLongitude(place.longitude ?? '');
    setHechsherIds((place.hechshers ?? []).map((h) => h.hechsher_id).join(','));
    setTags((place.tags ?? []).join(','));
  }, [open, place]);

  if (!open) return null;

  const handleUseLocation = () => {
    navigator.geolocation?.getCurrentPosition(
      ({ coords }) => {
        setLatitude(String(coords.latitude));
        setLongitude(String(coords.longitude));
      },
      () => setError('Location unavailable. Please enter coordinates manually.'),
      { timeout: 5000 },
    );
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
        await submitPlace({
          submission_type: mode,
          place_id: mode === 'edit' ? place?.place_id : null,
          place_name: placeName,
          street_address: streetAddress,
          latitude: latitude ? Number(latitude) : null,
          longitude: longitude ? Number(longitude) : null,
          hechsher_ids: splitCsvNums(hechsherIds),
          tags: splitCsv(tags),
          source: latitude && longitude ? 'location_detect' : 'manual',
        });
      }
      onSubmitted?.();
      onClose();
    } catch (err) {
      const msg = err?.response?.data?.message || err?.response?.data?.error || 'Submission failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const title = mode === 'new_place' ? 'Add Place' : mode === 'edit' ? 'Edit Place' : 'Tag Place';

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>

        <form onSubmit={handleSubmit} className="modal-form">
          {mode !== 'tag_update' && (
            <>
              <label className="field-label">Place name</label>
              <input className="input" value={placeName} onChange={(e) => setPlaceName(e.target.value)} required />

              <label className="field-label">Address</label>
              <input className="input" value={streetAddress} onChange={(e) => setStreetAddress(e.target.value)} required />

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

              <label className="field-label">Hechsher IDs (comma-separated)</label>
              <input className="input" value={hechsherIds} onChange={(e) => setHechsherIds(e.target.value)} required />
            </>
          )}

          <label className="field-label">Tags (comma-separated)</label>
          <input className="input" value={tags} onChange={(e) => setTags(e.target.value)} required />

          {mode === 'tag_update' && (
            <>
              <label className="field-label">Reason</label>
              <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} />
            </>
          )}

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

