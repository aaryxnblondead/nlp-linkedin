import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ApplicantForm from './ApplicantForm';
import ApplicantDashboard from './ApplicantDashboard';
import RecruiterDashboard from './RecruiterDashboard';
import { Login, Register } from './AuthForms';
import Home from './Home';
import { fetchMyApplicant } from './api/apiClient';

function PrivateRoute({ children, token, role, allowedRoles }) {
  if (!token) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/" />;
  return children;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [role, setRole] = useState(localStorage.getItem('role'));
  const [applicantId, setApplicantId] = useState(null);
  const [myApplicant, setMyApplicant] = useState(null);
  const [showRegister, setShowRegister] = useState(false);

  const handleLogin = (jwt, userRole) => {
    setToken(jwt);
    setRole(userRole);
    localStorage.setItem('token', jwt);
    localStorage.setItem('role', userRole);
  };

  const handleLogout = () => {
    setToken(null);
    setRole(null);
    setApplicantId(null);
    localStorage.removeItem('token');
    localStorage.removeItem('role');
  };

  return (
    <Router>
      <div className="shell">
        <div className="nav">
          <div className="brand">
            <div className="brand-badge" />
            <div className="brand-name">QualifyAI</div>
          </div>
          {token && <button className="btn btn-secondary" onClick={handleLogout}>Logout</button>}
        </div>
        <Routes>
          <Route path="/login" element={
            showRegister ? (
              <>
                <div className="app-container">
                  <Register onRegister={() => setShowRegister(false)} />
                </div>
                <button className="btn btn-secondary" onClick={() => setShowRegister(false)} style={{ marginTop: 8 }}>
                  Back to Login
                </button>
              </>
            ) : (
              <>
                <div className="app-container">
                  <Login onLogin={handleLogin} />
                </div>
                <button className="btn btn-secondary" onClick={() => setShowRegister(true)} style={{ marginTop: 8 }}>
                  Register
                </button>
              </>
            )
          } />
          <Route path="/recruiter" element={
            <PrivateRoute token={token} role={role} allowedRoles={['recruiter']}>
              <div className="app-container" style={{ minHeight: 'calc(100vh - 140px)' }}>
                <RecruiterDashboard token={token} />
              </div>
            </PrivateRoute>
          } />
          <Route path="/applicant" element={
            <PrivateRoute token={token} role={role} allowedRoles={['applicant']}>
              <ApplicantGate token={token} />
            </PrivateRoute>
          } />
          <Route path="/" element={
            token ? (
              role === 'recruiter' ? <Navigate to="/recruiter" /> : <Navigate to="/applicant" />
            ) : (
              <div className="app-container">
                <Home onGetStarted={() => window.location.assign('/login')} />
              </div>
            )
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

function ApplicantGate({ token }){
  const [state, setState] = React.useState({ loading: true, exists: false, applicantId: null, insights: null, percentile: null, improvements: [] });
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try{
        const res = await fetchMyApplicant(token);
        if(cancelled) return;
        if(res.data.exists){
          setState({
            loading:false,
            exists:true,
            applicantId: res.data.applicant?.id || null,
            insights: res.data.insights || null,
            percentile: res.data.percentile ?? null,
            improvements: res.data.improvements || [],
          });
        } else {
          setState(s=>({...s, loading:false, exists:false}));
        }
      }catch{
        setState(s=>({...s, loading:false, exists:false}));
      }
    })();
    return ()=>{ cancelled = true };
  }, [token]);

  if(state.loading){
    return <div className="app-container"><p className="muted">Loading…</p></div>;
  }
  if(!state.exists){
    return (
      <div className="app-container">
        <ApplicantForm onSubmitted={()=>window.location.reload()} token={token} />
      </div>
    );
  }
  return (
    <div className="grid grid-2">
      <div className="app-container">
        <ApplicantDashboard applicantId={state.applicantId} token={token} />
      </div>
      <div className="app-container">
        <ApplicantSummaryPanel insights={state.insights} percentile={state.percentile} improvements={state.improvements} />
      </div>
    </div>
  );
}

function ApplicantSummaryPanel({ insights, percentile, improvements }){
  if(!insights){
    return <div><h3>Analysis</h3><p className="muted">Insights will appear once processing completes.</p></div>;
  }
  const rating = insights?.rating ?? 'N/A';
  const yrs = insights?.experience_years ?? 'N/A';
  const educationScore = insights?.education_score ?? 'N/A';
  // Derive a simple rating label (mirrors backend fallback)
  const ratingLabel = typeof rating === 'number'
    ? (rating >= 90 ? 'Outstanding' : rating >= 75 ? 'Strong' : rating >= 60 ? 'Good' : rating >= 40 ? 'Fair' : 'Needs improvement')
    : '—';

  return (
    <div>
      <h3>Your analysis</h3>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-card-label">Rating</div>
          <div className="kpi-card-value">{rating}</div>
          <div className="kpi-card-sub">{ratingLabel}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card-label">Experience</div>
          <div className="kpi-card-value">{yrs}<span className="kpi-card-unit"> yrs</span></div>
          <div className="kpi-card-sub">Total industry</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card-label">Education</div>
          <div className="kpi-card-value">{educationScore}</div>
          <div className="kpi-card-sub">Education score</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card-label">Percentile</div>
          <div className="kpi-card-value">{percentile != null ? percentile : '—'}<span className="kpi-card-unit">th</span></div>
          <div className="kpi-card-sub">Relative to cohort</div>
        </div>
      </div>
      <div className="divider" />
      <h3>Improvement ideas</h3>
      {improvements && improvements.length > 0 ? (
        <ul>
          {improvements.map((t,i)=>(<li key={i} className="muted" style={{marginBottom:6}}>{t}</li>))}
        </ul>
      ) : (
        <p className="muted">We’ll suggest improvements as soon as we finish analyzing your resume and profile.</p>
      )}
    </div>
  );
}
