import React from 'react';

export default function Home({ onGetStarted }) {
  return (
    <div>
      <div className="hero">
        <div>
          <div className="chip">For Recruiters</div>
          <div className="hero-title">Hire smarter with QualifyAI</div>
          <div className="hero-copy">
            Turn resume piles into signal. QualifyAI extracts skills and experience with robust NLP, then scores candidates with an explainable, role-aware engine. See strengths at a glance and drill into the details when it matters.
          </div>
          <div style={{ marginTop: 14, display:'flex', gap:10, flexWrap:'wrap' }}>
            <button className="btn" onClick={onGetStarted}>Get started</button>
            <a className="btn btn-secondary" href="#benefits">Explore benefits</a>
          </div>
        </div>
        <div className="card" style={{ minWidth:280, maxWidth:400 }}>
          <h2>Why teams choose us</h2>
          <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--muted)' }}>
            <li>Explainable candidate scores (0–100) with transparent subscores</li>
            <li>Accurate entity extraction (skills, titles, education, experience)</li>
            <li>Role-aware weighting to match your hiring priorities</li>
            <li>Instant visual dashboards for quick shortlisting</li>
          </ul>
        </div>
      </div>

      <div id="benefits" className="grid grid-2">
        <div className="app-container">
          <h2>Surface the right talent faster</h2>
          <p className="muted">Our NLP pinpoints what matters—skills, seniority, education, and tenure—so you spend less time sifting and more time interviewing the right people.</p>
          <div className="divider" />
          <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--muted)' }}>
            <li>Automated insights summarizing key strengths</li>
            <li>LinkedIn activity and sentiment signals where available</li>
            <li>Consistency checks across resume and profile</li>
          </ul>
        </div>
        <div className="app-container">
          <h2>Make confident, explainable decisions</h2>
          <p className="muted">Every score is backed by a clear breakdown—experience, skills breadth/depth, seniority, education, endorsements, and more.</p>
          <div className="divider" />
          <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--muted)' }}>
            <li>Adjustable weight profiles by role or team</li>
            <li>Visual subscores via radar charts for quick comparison</li>
            <li>Exportable insights for hiring committees</li>
          </ul>
        </div>
      </div>

      <div className="app-container">
        <h2>How it works</h2>
        <ol style={{ margin: 0, paddingLeft: 18, color: 'var(--muted)' }}>
          <li>Upload resumes or sync from your corpus</li>
          <li>Our pipeline parses, extracts, and scores candidates</li>
          <li>Review candidates on the Recruiter dashboard and expand for details</li>
          <li>Share insights, shortlist top matches, and move faster</li>
        </ol>
      </div>
    </div>
  );
}
