import { useEffect, useState } from 'react';
import { approveSubmission, listAdminSubmissions, rejectSubmission } from '../../api/admin';

export default function AdminQueue() {
  const [flagged, setFlagged] = useState([]);
  const [approved, setApproved] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [flaggedRes, approvedRes] = await Promise.all([
        listAdminSubmissions({ spam_filter_result: 'flagged' }),
        listAdminSubmissions({ spam_filter_result: 'approved' }),
      ]);
      setFlagged(flaggedRes.data.items);
      setApproved(approvedRes.data.items);
    } catch (e) {
      setError(e?.response?.data?.message || 'Failed to load admin queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const onApprove = async (id) => {
    await approveSubmission(id);
    await load();
  };

  const onReject = async (id) => {
    const reason = window.prompt('Reason for rejection (optional)') ?? '';
    await rejectSubmission(id, reason);
    await load();
  };

  if (loading) return <div className="page-card">Loading admin queue...</div>;
  if (error) return <div className="page-card form-error">{error}</div>;

  return (
    <div className="admin-grid">
      <section className="page-card">
        <h3>Flagged</h3>
        {flagged.length === 0 && <p>No flagged submissions.</p>}
        {flagged.map((s) => (
          <article key={s.submission_id} className="queue-item">
            <div>
              <strong>#{s.submission_id}</strong> {s.submission_type}
              <div className="muted">status: {s.admin_review_status}</div>
            </div>
            <div className="row-actions">
              <button className="btn btn-primary" onClick={() => onApprove(s.submission_id)}>Approve</button>
              <button className="btn btn-secondary" onClick={() => onReject(s.submission_id)}>Reject</button>
            </div>
            <pre>{JSON.stringify(s.payload_json, null, 2)}</pre>
          </article>
        ))}
      </section>

      <section className="page-card">
        <h3>Non-flagged</h3>
        {approved.length === 0 && <p>No non-flagged submissions.</p>}
        {approved.map((s) => (
          <article key={s.submission_id} className="queue-item">
            <div>
              <strong>#{s.submission_id}</strong> {s.submission_type}
              <div className="muted">status: {s.admin_review_status}</div>
            </div>
            <div className="row-actions">
              {s.admin_review_status === 'pending_review' && (
                <>
                  <button className="btn btn-primary" onClick={() => onApprove(s.submission_id)}>Approve</button>
                  <button className="btn btn-secondary" onClick={() => onReject(s.submission_id)}>Reject</button>
                </>
              )}
            </div>
            <pre>{JSON.stringify(s.payload_json, null, 2)}</pre>
          </article>
        ))}
      </section>
    </div>
  );
}

