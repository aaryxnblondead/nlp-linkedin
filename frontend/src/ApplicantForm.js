import React, { useState } from 'react';
import { submitApplicant } from './api/apiClient';

const ApplicantForm = ({ onSubmitted, token }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [linkedin, setLinkedin] = useState('');
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);
    formData.append('linkedin_url', linkedin);
    formData.append('resume', resume);
    try {
      const res = await submitApplicant(formData, token);
      onSubmitted(res.data.applicant_id);
    } catch (err) {
      setError('Submission failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="stack">
        <div>
          <h2>Submit your application</h2>
          <p className="muted">Provide your details and resume</p>
        </div>
        <input className="input" type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} required />
        <input className="input" type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
        <input className="input" type="url" placeholder="LinkedIn URL" value={linkedin} onChange={e => setLinkedin(e.target.value)} required />
        <input className="input" type="file" accept=".pdf,.doc,.docx" onChange={e => setResume(e.target.files[0])} required />
        <div>
          <button className="btn" type="submit" disabled={loading}>{loading ? 'Submitting…' : 'Submit'}</button>
        </div>
        {error && <div style={{color:'var(--danger)'}}>{error}</div>}
      </div>
    </form>
  );
};

export default ApplicantForm;
