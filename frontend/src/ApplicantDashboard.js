import React, { useState, useEffect, useRef } from 'react';
import { fetchApplicant } from './api/apiClient';
import ScoreBreakdownRadar from './ScoreBreakdownRadar';
import './index.css';

const ApplicantDashboard = ({ applicantId, token }) => {
  const [applicant, setApplicant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(5);
  const [doneMessage, setDoneMessage] = useState('');
  const [analysisReady, setAnalysisReady] = useState(false);
  const pollTimer = useRef(null);
  const progressTimer = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const loadApplicant = async () => {
      if (!applicant) setLoading(true);
      // Ensure progress bar is visible immediately
      setProgress((p) => (p <= 0 ? 5 : p));
      // Start simulated progress early so users see motion right away
      if (!progressTimer.current) {
        progressTimer.current = setInterval(() => {
          setProgress((p) => {
            if (p < 90) {
              const increment = Math.max(1, Math.round((90 - p) * 0.1));
              return Math.min(90, p + increment);
            }
            return p;
          });
        }, 800);
      }
      setError('');
      try {
        const res = await fetchApplicant(applicantId, token);
        if (cancelled) return;
        setApplicant(res.data);
        // If still processing, poll again in 3s
        const status = (res.data?.status || '').toString();
        if (status === 'submitted' || status === 'processing') {
          pollTimer.current = setTimeout(loadApplicant, 3000);
          // progress timer already started above
        } else if (status === 'processed') {
          // Completed: fill progress to 100 and show analysis
          setProgress(100);
          setDoneMessage('Your analysis is ready.');
          setAnalysisReady(true);
          if (progressTimer.current) {
            clearInterval(progressTimer.current);
            progressTimer.current = null;
          }
        }
      } catch (err) {
        if (!cancelled) setError('Failed to load applicant data.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadApplicant();
    return () => {
      cancelled = true;
      if (pollTimer.current) clearTimeout(pollTimer.current);
      if (progressTimer.current) clearInterval(progressTimer.current);
    };
  }, [applicantId, token]);

  // Show progress UI while loading, processing, or during the short post-completion window
  const status = (applicant?.status || '').toString();
  const showProgress = loading || status === 'submitted' || status === 'processing';
  if (showProgress) {
    return (
      <div>
        <div className="hero">
          <div>
            <div className="chip">Applicant</div>
            <div className="hero-title">Processing your application</div>
            <div className="hero-copy">We’re analyzing your resume and profile. This usually takes a moment.</div>
          </div>
        </div>
        <div className="card">
          <div className="progress" style={{ marginTop: 6 }}>
            <div className={`bar${progress >= 100 ? ' complete' : ''}`} style={{ width: `${progress}%` }} />
          </div>
          <p className="muted" style={{ marginTop: 8 }}>{progress}%</p>
        </div>
      </div>
    );
  }
  if (error) return <div style={{ color: 'red' }}>{error}</div>;
  if (!applicant) return <div>No applicant data found.</div>;

  // When loaded and not processing, show the heptagram (radar) analysis
  // Parse additional resume-quality signals from the summary string
  const summaryText = (applicant?.insights?.summary || '');
  let projectQuality = null;
  let confidenceTone = null;
  try {
    const pqMatch = summaryText.match(/Project quality \(resume\):\s*([0-9.]+)/i);
    if (pqMatch) projectQuality = parseFloat(pqMatch[1]);
  } catch {}
  try {
    const toneMatch = summaryText.match(/Confidence tone:\s*([0-9.]+)/i);
    if (toneMatch) confidenceTone = parseFloat(toneMatch[1]);
  } catch {}

  return (
    <div>
      <div className="hero">
        <div>
          <div className="chip">Applicant</div>
          <div className="hero-title">Your analysis</div>
          <div className="hero-copy">Here’s a breakdown of how your profile is evaluated across key dimensions.</div>
        </div>
      </div>
      {doneMessage && (
        <div className="card">
          <p className="success" style={{ marginTop: 4 }}>{doneMessage}</p>
        </div>
      )}
      <ScoreBreakdownRadar applicantId={applicantId} token={token} />
      {(projectQuality !== null || confidenceTone !== null) && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="muted" style={{ marginBottom: 6 }}>Resume-derived signals</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {projectQuality !== null && (
              <span className="chip" title="Heptagram Endorsements/Projects axis (resume-based)">
                Project quality: {projectQuality.toFixed(2)}
              </span>
            )}
            {confidenceTone !== null && (
              <span className="chip" title="Ownership/confidence tone from resume text">
                Confidence tone: {confidenceTone.toFixed(2)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicantDashboard;
