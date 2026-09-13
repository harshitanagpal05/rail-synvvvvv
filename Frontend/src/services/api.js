/**
 * RailSync 2.0 — Central API Service
 * Connects Frontend to Backend (FastAPI Layer 4)
 * Real data flows: L0 (Timetable) → L1 (Risk ML) → L2 (Negotiation) → L3 (CP-SAT Optimization) → L4 (API)
 */

import axios from 'axios';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Health ─────────────────────────────────────────
export const getHealth = () => API.get('/health').then(r => r.data);

// ─── Tasks (Layer 0 seed data) ──────────────────────
export const getTasks = () => API.get('/tasks').then(r => r.data);
export const ingestTask = (data) => API.post('/ingest/tasks', data).then(r => r.data);

// ─── Risk Predictions (Layer 1 — ML Model) ─────────
export const getRiskSegments = (params = {}) =>
  API.get('/risk/segments', { params }).then(r => r.data);

export const getSegmentRisk = (segmentId) =>
  API.get(`/risk/${segmentId}`).then(r => r.data);

// ─── Negotiation (Layer 2) ──────────────────────────
export const runNegotiation = () => API.post('/negotiate').then(r => r.data);

// ─── Optimization (Layer 3 — CP-SAT Solver) ────────
export const runOptimization = (policy = 'balanced', horizon = 'both', objectiveWeights = null) =>
  API.post('/optimize', {
    policy,
    horizon,
    objective_weights: objectiveWeights,
  }).then(r => r.data);

// ─── What-If Simulation (Layer 3) ───────────────────
export const runWhatIf = ({ type, segment_id, severity = 'moderate', time = null, description = null }) =>
  API.post('/optimize/whatif', {
    type,
    segment_id,
    severity,
    time,
    description,
  }).then(r => r.data);

// ─── Plans (Layer 4 — Persisted) ────────────────────
export const getCurrentPlan = () => API.get('/plan/current').then(r => r.data);
export const getPlanById = (planId) => API.get(`/plan/${planId}`).then(r => r.data);

// ─── Feedback (Layer 4 — Post-execution) ────────────
export const submitFeedback = (data) => API.post('/feedback/block', data).then(r => r.data);
export const getFeedbackMetrics = () => API.get('/feedback/metrics').then(r => r.data);

// ─── Live Defect & Real-Time Optimization (Layer 1 → 2 → 3) ────────
export const predictLiveRisk = (data) =>
  API.post('/live/predict', data).then(r => r.data);

export const reportAndOptimizeLiveDefect = (data) =>
  API.post('/live/report-and-optimize', data).then(r => r.data);

// ─── Real-Time Operations ───────────────────────────
export const getRealtimeStatus = () =>
  API.get('/realtime/status').then(r => r.data);

export const getRealtimeTrains = () =>
  API.get('/realtime/trains').then(r => r.data);

export const getWeatherContext = () =>
  API.get('/realtime/weather-context').then(r => r.data);

export const getNetworkMap = () =>
  API.get('/realtime/network-map').then(r => r.data);

// ─── Utility Helpers ────────────────────────────────
export const formatDuration = (hrs) => {
  if (!hrs) return '—';
  const h = Math.floor(hrs);
  const m = Math.round((hrs - h) * 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
};

export const formatDateTime = (isoStr) => {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
};

export const formatTime = (isoStr) => {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
};

export const riskLevel = (risk30d) => {
  if (risk30d >= 0.7) return { label: 'CRITICAL', color: 'error' };
  if (risk30d >= 0.4) return { label: 'HIGH', color: 'secondary' };
  if (risk30d >= 0.2) return { label: 'MODERATE', color: 'on-surface-variant' };
  return { label: 'LOW', color: 'on-tertiary-container' };
};

export const criticalityLabel = (lvl) => {
  const map = { 1: 'CRITICAL', 2: 'URGENT', 3: 'HIGH', 4: 'ROUTINE', 5: 'LOW' };
  return map[lvl] || `LVL ${lvl}`;
};

export const deptLabel = (dept) => {
  const map = {
    TRACK: 'Engineering (P-Way)',
    OHE: 'Traction (TRD/OHE)',
    SIG: 'Signalling (S&T)',
    TELE: 'Telecom',
    BRIDGE: 'Bridge (BR)',
  };
  return map[dept] || dept;
};

export default API;
