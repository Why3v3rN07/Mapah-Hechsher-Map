import { useEffect, useState } from 'react';
import { getMySubmissions } from '../../api/me';

function summaryText(summary = {}) {
  const parts = [];
  if (summary.place_name) parts.push(`place: ${summary.place_name}`);
  if (summary.street_address) parts.push(`address: ${summary.street_address}`);
  if (Array.isArray(summary.tags) && summary.tags.length) parts.push(`tags: ${summary.tags.join(', ')}`);
  if (Array.isArray(summary.aliases) && summary.aliases.length) parts.push(`aliases: ${summary.aliases.join(', ')}`);
  return parts.join(' | ') || 'No summary available';
}

function moderationText(submission = {}) {
  const moderation = submission?.payload_json?.moderation || {};
  const reason = moderation.reason || '';
  const source = moderation.source || 'unknown';
  const version = moderation.moderation_version || 'n/a';
  if (!reason) return `moderation: ${source} (${version})`;
  return `moderation: ${source} (${version}) - ${reason}`;
}

export default function MySubmissionsList() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getMySubmissions({ page: 1, page_size: 50 })
      .then(({ data }) => setItems(data.items))
      .catch((err) => setError(err?.response?.data?.message || 'Failed to load submissions'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-card">Loading submissions...</div>;
  if (error) return <div className="page-card form-error">{error}</div>;

  return (
    <section className="page-card">
      <h2>My submissions</h2>
      {items.length === 0 && <p>No submissions yet.</p>}
      {items.map((s) => (
        <article key={s.submission_id} className="queue-item">
          <div>
            <strong>#{s.submission_id}</strong> {s.submission_type}
            <div className="muted">
              spam: {s.spam_filter_result} · admin: {s.admin_review_status}
            </div>
            <div className="muted">{moderationText(s)}</div>
          </div>
          <p className="muted">{summaryText(s.summary)}</p>
        </article>
      ))}
    </section>
  );
}

