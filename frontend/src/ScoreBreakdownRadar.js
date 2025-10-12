import React, { useEffect, useState } from 'react';
import { Radar } from 'react-chartjs-2';
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, Title } from 'chart.js';
import { fetchScoringBreakdown } from './api/apiClient';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, Title);

export default function ScoreBreakdownRadar({ applicantId, token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      if (!applicantId) return;
      setLoading(true);
      setError('');
      try {
        const res = await fetchScoringBreakdown(applicantId, token);
        setData(res.data);
      } catch (e) {
        setError('Failed to load breakdown');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [applicantId, token]);

  // Pull CSS variables for colors/fonts
  let textColor = '#e5e7eb';
  let mutedColor = '#9aa3b2';
  let fontFamily = 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif';
  if (typeof window !== 'undefined') {
    const css = getComputedStyle(document.documentElement);
    textColor = (css.getPropertyValue('--text') || textColor).trim() || textColor;
    mutedColor = (css.getPropertyValue('--muted') || mutedColor).trim() || mutedColor;
  }
  // Set Chart.js global defaults (idempotent per mount)
  ChartJS.defaults.color = textColor;
  ChartJS.defaults.font = ChartJS.defaults.font || {};
  ChartJS.defaults.font.family = fontFamily;
  ChartJS.defaults.font.size = 12;

  if (loading) return <div className="muted">Loading chart…</div>;
  if (error) return <div style={{ color: 'var(--danger)' }}>{error}</div>;
  if (!data || !data.breakdown || !data.breakdown.subscores) return <div className="muted">No breakdown available.</div>;

  const subs = data.breakdown.subscores;
  const labels = [
    'Experience',
    'Seniority',
    'Skills',
    'Education',
    'Activity',
    'Sentiment',
    'Endorsements/Projects',
  ];
  const values = [
    subs.experience_score ?? 0,
    subs.seniority_score ?? 0,
    subs.skills_score ?? 0,
    subs.education_score ?? 0,
    subs.activity_score ?? 0,
    subs.sentiment_score_norm ?? 0,
    subs.endorsements_projects_score ?? 0,
  ];

  const chartData = {
    labels,
    datasets: [
      {
        label: `Subscores (0-1)` ,
        data: values,
        backgroundColor: 'rgba(54, 162, 235, 0.16)',
        borderColor: 'rgba(54, 162, 235, 0.9)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(54, 162, 235, 1)',
        pointRadius: 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: mutedColor, boxWidth: 14, boxHeight: 2, usePointStyle: false, padding: 8, font: { weight: 600 } }
      },
      title: {
        display: true,
        text: `Rating ${data.rating} (${data.rating_label || ''})`,
        color: textColor,
        font: { family: fontFamily, weight: 600, size: 13 }
      },
      tooltip: { enabled: true },
    },
    scales: {
      r: {
        min: 0,
        max: 1,
        ticks: {
          stepSize: 0.2,
          showLabelBackdrop: false,
          color: mutedColor,
          backdropColor: 'transparent',
          font: { family: fontFamily, size: 10, weight: 500 }
        },
        grid: { color: 'rgba(255,255,255,0.06)' },
        angleLines: { color: 'rgba(255,255,255,0.04)' },
        pointLabels: {
          color: mutedColor,
          font: { family: fontFamily, size: 12, weight: 600 },
          backdropColor: 'transparent'
        },
      },
    },
  };

  return (
    <div className="card radar-wrapper" style={{ padding: 16, minHeight: 420 }}>
      <div style={{ position: 'relative', height: 360 }}>
        <Radar data={chartData} options={options} />
      </div>
      <div className="muted" style={{ marginTop: 8 }}>Experience years: {data.experience_years ?? 'N/A'}</div>
    </div>
  );
}
