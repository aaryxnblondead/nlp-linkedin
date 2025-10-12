import React, { useState, useEffect, useMemo } from 'react';
import { fetchAllApplicants } from './api/apiClient';
import ScoreBreakdownRadar from './ScoreBreakdownRadar';
import './index.css';
import SummaryCell from './SummaryCell';

function RecruiterDashboard({ token }) {
  const [applicants, setApplicants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [experienceFilter, setExperienceFilter] = useState('');
  const [minRating, setMinRating] = useState('');
  const [skills, setSkills] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [sortBy, setSortBy] = useState('created');

  const loadApplicants = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {
        search: searchTerm,
        min_exp: experienceFilter || 0,
        min_rating: minRating !== '' ? Number(minRating) : undefined,
        skills: skills || undefined,
      };
      const res = await fetchAllApplicants(token, params);
      setApplicants(res.data);
    } catch (err) {
      setError('Failed to fetch applicants.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplicants();
  }, [token, searchTerm, experienceFilter, minRating, skills]);

  const filteredApplicants = useMemo(() => {
    const arr = [...applicants];
    switch (sortBy) {
      case 'rating-desc':
        return arr.sort((a,b) => (b.insights?.rating ?? -1) - (a.insights?.rating ?? -1));
      case 'experience-desc':
        return arr.sort((a,b) => (b.insights?.experience_years ?? -1) - (a.insights?.experience_years ?? -1));
      case 'name-asc':
        return arr.sort((a,b) => (a.name||'').localeCompare(b.name||''));
      default:
        return arr; // created order from API
    }
  }, [applicants, sortBy]);

  // removed Resync LinkedIn handler

  return (
    <div>
      <div className="hero">
        <div>
          <div className="chip">Recruiter</div>
          <div className="hero-title">Talent overview</div>
          <div className="hero-copy">Search, filter, and review candidates from your aggregated resume corpus.</div>
        </div>
        <select className="select" value={sortBy} onChange={(e)=>setSortBy(e.target.value)}>
          <option value="created">Sort: Created (default)</option>
          <option value="rating-desc">Sort: Rating (high→low)</option>
          <option value="experience-desc">Sort: Experience (high→low)</option>
          <option value="name-asc">Sort: Name (A→Z)</option>
        </select>
      </div>

      <div className="toolbar">
        <button className="btn btn-secondary" onClick={loadApplicants} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
        <input className="input" type="text" placeholder="Search by keyword…" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
        <input className="input" type="number" placeholder="Min Experience (years)" value={experienceFilter} onChange={(e) => setExperienceFilter(e.target.value)} />
        <input className="input" type="number" placeholder="Min Rating (-2 to 2)" value={minRating} min={-2} max={2} onChange={(e) => setMinRating(e.target.value)} />
        <input className="input" type="text" placeholder="Required skills (comma-separated)" value={skills} onChange={(e) => setSkills(e.target.value)} />
      </div>

      {error && <div style={{ color: 'var(--danger)' }}>{error}</div>}

      <div className="card">
        {filteredApplicants.length > 0 ? (
          <table>
            <colgroup>
              <col className="col-name" />
              <col className="col-email" />
              <col className="col-linkedin" />
              <col className="col-rating" />
              <col className="col-exp" />
              <col className="col-education" />
              <col className="col-summary" />
              <col className="col-actions" />
            </colgroup>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>LinkedIn</th>
                <th>Rating</th>
                <th>Experience (Yrs)</th>
                <th>Education</th>
                <th>Summary</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {filteredApplicants.map((applicant) => (
                <React.Fragment key={applicant.id}>
                  <tr>
                    <td>{applicant.name}</td>
                    <td>{applicant.email}</td>
                    <td>
                      <a href={applicant.linkedin_url} target="_blank" rel="noopener noreferrer">
                        Profile
                      </a>
                    </td>
                    <td>{applicant.insights?.rating || 'N/A'}</td>
                    <td>{applicant.insights?.experience_years || 'N/A'}</td>
                    <td>{applicant.insights?.education_score || 'N/A'}</td>
                    <td>
                      {(() => {
                        const r = applicant?.insights?.rating;
                        const y = applicant?.insights?.experience_years;
                        const rTxt = (typeof r === 'number') ? r : 'N/A';
                        const yTxt = (typeof y === 'number') ? y : 'N/A';
                        return (
                          <span className="summary-badge" title="Rating and years of experience">
                            Rating {rTxt} | {yTxt} yrs
                          </span>
                        );
                      })()}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={() => setExpandedId(expandedId === applicant.id ? null : applicant.id)}
                      >
                        {expandedId === applicant.id ? 'Hide' : 'Show'}
                      </button>
                      {/* Resync LinkedIn button removed per request */}
                    </td>
                  </tr>
                  {expandedId === applicant.id && (
                    <tr>
                      <td colSpan={8}>
                        <div className="grid grid-2" style={{ padding: 12 }}>
                          <div className="card">
                            <ScoreBreakdownRadar applicantId={applicant.id} token={token} />
                          </div>
                          <div className="card details-card">
                            <h3 className="details-heading">Candidate details</h3>
                            <SummaryCell insights={applicant.insights} />
                            {Array.isArray(applicant.insights?.projects) && applicant.insights.projects.length > 0 && (
                              <div style={{ marginBottom: 8 }}>
                                <div className="muted" style={{ marginBottom: 6 }}>LinkedIn Projects</div>
                                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                  {applicant.insights.projects.slice(0, 6).map((p, idx) => {
                                    const name = typeof p === 'string' ? p : (p?.name || 'Project');
                                    const url = typeof p === 'object' ? (p?.url || '') : '';
                                    return url ? (
                                      <a key={idx} href={url} target="_blank" rel="noopener noreferrer" className="chip" title={name}>
                                        {name}
                                      </a>
                                    ) : (
                                      <span key={idx} className="chip" title={name}>{name}</span>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No applicants match your criteria.</p>
        )}
      </div>
    </div>
  );
}

export default RecruiterDashboard;
