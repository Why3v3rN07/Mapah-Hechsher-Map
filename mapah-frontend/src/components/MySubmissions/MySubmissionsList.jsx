import { useEffect, useState } from 'react';
import { getMySubmissions } from '../../api/me';

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
          </div>
          <pre>{JSON.stringify(s.payload_json, null, 2)}</pre>
        </article>
      ))}
    </section>
  );
}

