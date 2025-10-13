// API Client for QualifyAI
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const fetchAllApplicants = async (token, params) => {
  return axios.get(`${API_BASE}/applicants/`, {
    headers: { Authorization: `Bearer ${token}` },
    params,
  });
};

export const submitApplicant = async (formData, token) => {
  return axios.post(`${API_BASE}/applicants/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${token}` },
  });
};

export const fetchApplicant = async (id, token) => {
  return axios.get(`${API_BASE}/applicants/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export const fetchMyApplicant = async (token) => {
  return axios.get(`${API_BASE}/me/applicant`, {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export const fetchScoringBreakdown = async (id, token) => {
  return axios.get(`${API_BASE}/applicants/${id}/scoring_breakdown`, {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export const reprocessApplicant = async (id, token) => {
  return axios.post(`${API_BASE}/applicants/${id}/reprocess`, {}, {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export const registerUser = async (username, password, role) => {
  return axios.post(`${API_BASE}/register/`, { username, password, role });
};

export const loginUser = async (username, password) => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  return axios.post(`${API_BASE}/login/`, params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

// Chat: grounded Q&A over an applicant's KB
export const chatApplicant = async (applicantId, messages, token, opts = {}) => {
  const body = {
    messages,
    top_k: typeof opts.top_k === 'number' ? opts.top_k : 6,
    max_new_tokens: typeof opts.max_new_tokens === 'number' ? opts.max_new_tokens : 256,
  };
  const base = API_BASE;
  const url = applicantId ? `${base}/chat/${applicantId}` : `${base}/chat`;
  return axios.post(url, body, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  });
};
