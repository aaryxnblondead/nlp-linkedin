import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerUser, loginUser } from './api/apiClient';

export function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await loginUser(username, password);
      const { access_token, role } = res.data;
      onLogin(access_token, role);
      
      // Navigate based on role
      if (role === 'recruiter') {
        navigate('/recruiter');
      } else {
        navigate('/applicant');
      }
    } catch (err) {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="stack">
      <div>
        <h2>Welcome back</h2>
        <p className="muted">Sign in to continue</p>
      </div>
      <div className="divider" />
      <input className="input" type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required />
      <input className="input" type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
      <button className="btn" type="submit" disabled={loading}>{loading ? 'Logging in...' : 'Login'}</button>
      {error && <div className="hint" style={{color:'var(--danger)'}}>{error}</div>}
    </form>
  );
}

export function Register({ onRegister }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('applicant');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await registerUser(username, password, role);
      onRegister();
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="stack">
      <div>
        <h2>Create account</h2>
        <p className="muted">Choose your role to begin</p>
      </div>
      <div className="divider" />
      <input className="input" type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required />
      <input className="input" type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
      <select className="select" value={role} onChange={e => setRole(e.target.value)}>
        <option value="applicant">Applicant</option>
        <option value="recruiter">Recruiter</option>
      </select>
      <button className="btn" type="submit" disabled={loading}>{loading ? 'Registering...' : 'Register'}</button>
      {error && <div className="hint" style={{color:'var(--danger)'}}>{error}</div>}
    </form>
  );
}
