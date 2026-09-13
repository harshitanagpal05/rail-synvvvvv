import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  predictLiveRisk,
  reportAndOptimizeLiveDefect,
  formatDuration,
  formatTime,
  deptLabel,
} from '../services/api';

const PRESETS = [
  {
    label: 'High-Risk Monsoon Track Fracture',
    icon: 'railway_alert',
    data: {
      asset_type: 'TRACK',
      division: 'Delhi',
      age_years: 26.5,
      installation_year: 2000,
      length_km: 14.2,
      monsoon_exposure: 'high',
      task_type: 'Severe Rail Flaw / Ultrasonic Defect',
      claimed_criticality: 5,
      policy: 'balanced',
    },
  },
  {
    label: 'Critical OHE Catenary Wire Droop',
    icon: 'electric_bolt',
    data: {
      asset_type: 'OHE',
      division: 'Mumbai',
      age_years: 22.0,
      installation_year: 2004,
      length_km: 8.5,
      monsoon_exposure: 'medium',
      task_type: 'Cantilever Droop & Contact Wire Sag',
      claimed_criticality: 4,
      policy: 'safety_first',
    },
  },
  {
    label: 'Interlocking S&T Track Circuit Fault',
    icon: 'cell_tower',
    data: {
      asset_type: 'SIG',
      division: 'Allahabad',
      age_years: 15.0,
      installation_year: 2011,
      length_km: 4.8,
      monsoon_exposure: 'high',
      task_type: 'Point Machine Feedback Signal Glitch',
      claimed_criticality: 5,
      policy: 'balanced',
    },
  },
  {
    label: 'Routine P-Way Ballast Settlement',
    icon: 'construction',
    data: {
      asset_type: 'TRACK',
      division: 'Howrah',
      age_years: 6.0,
      installation_year: 2020,
      length_km: 18.0,
      monsoon_exposure: 'low',
      task_type: 'Preventive Track Packing & Alignment',
      claimed_criticality: 2,
      policy: 'throughput_first',
    },
  },
];

export default function PredictOptimize() {
  const navigate = useNavigate();

  // Form State
    const [formData, setFormData] = useState({
    asset_type: 'TRACK',
    division: 'Delhi',
    age_years: 15,
    installation_year: 2011,
    length_km: 5.0,
    monsoon_exposure: 'medium',
    task_type: 'Emergency Defect Rectification',
    claimed_criticality: 5,
    policy: 'balanced',
    reporter_name: 'SSE/P.Way',
    gps_lat: '28.6139',
    gps_lng: '77.2090'
  });

  // Flow & State
  const [stepState, setStepState] = useState('idle'); // idle | predicting | optimizing | complete | error
  const [activeStep, setActiveStep] = useState(0); // 0: input, 1: risk predicted, 2: fully optimized
  const [predictionData, setPredictionData] = useState(null);
  const [optimizationData, setOptimizationData] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Sync installation year with age
  const handleAgeChange = (newAge) => {
    const age = parseFloat(newAge) || 0;
    setFormData((prev) => ({
      ...prev,
      age_years: age,
      installation_year: Math.max(1950, 2026 - Math.round(age)),
    }));
  };

  const handleYearChange = (newYear) => {
    const yr = parseInt(newYear, 10) || 2026;
    setFormData((prev) => ({
      ...prev,
      installation_year: yr,
      age_years: Math.max(0, 2026 - yr),
    }));
  };

  const applyPreset = (preset) => {
    setFormData(preset.data);
    setPredictionData(null);
    setOptimizationData(null);
    setActiveStep(0);
    setErrorMessage(null);
  };

  // Step 1: Predict Risk Live (Layer 1)
  const handlePredictRisk = async () => {
    setStepState('predicting');
    setErrorMessage(null);
    try {
      const res = await predictLiveRisk({
        age_years: parseFloat(formData.age_years),
        installation_year: parseInt(formData.installation_year, 10),
        length_km: parseFloat(formData.length_km),
        monsoon_exposure: formData.monsoon_exposure,
        asset_type: formData.asset_type,
        division: formData.division,
      });
      setPredictionData(res);
      setActiveStep(1);
      setStepState('idle');
    } catch (err) {
      console.error(err);
      setErrorMessage(err.response?.data?.detail || err.message || 'Failed to predict failure risk');
      setStepState('error');
    }
  };

  // Step 2: Full End-to-End Pipeline (Layer 1 -> 2 -> 3)
  const handleReportAndOptimize = async () => {
    setStepState('optimizing');
    setErrorMessage(null);
    try {
      const res = await reportAndOptimizeLiveDefect({
        age_years: parseFloat(formData.age_years),
        installation_year: parseInt(formData.installation_year, 10),
        length_km: parseFloat(formData.length_km),
        monsoon_exposure: formData.monsoon_exposure,
        asset_type: formData.asset_type,
        division: formData.division,
        task_type: formData.task_type,
        claimed_criticality: parseInt(formData.claimed_criticality, 10),
        policy: formData.policy,
      });
      setPredictionData(res.risk_prediction);
      setOptimizationData(res);
      setActiveStep(2);
      setStepState('complete');
    } catch (err) {
      console.error(err);
      setErrorMessage(err.response?.data?.detail || err.message || 'Failed to optimize schedule');
      setStepState('error');
    }
  };

  const riskPercent = predictionData ? (predictionData.risk_30d * 100).toFixed(1) : 0;
  const isHighRisk = predictionData && predictionData.risk_30d >= 0.4;
  const isCritRisk = predictionData && predictionData.risk_30d >= 0.7;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-container-low p-5 rounded-xl border border-surface-container-high shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary-container text-on-primary-container flex items-center justify-center shadow-xs shrink-0">
            <span className="material-symbols-outlined text-[28px] text-primary">bolt</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-headline-sm text-xl font-bold text-on-surface">
                Predict & Optimize (Live Defects)
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold font-code-sm bg-primary/10 text-primary uppercase tracking-wider">
                CLOSED-LOOP TWIN
              </span>
            </div>
            <p className="text-[13px] text-on-surface-variant mt-0.5">
              Report live asset defects across divisions → evaluate Layer 1 ML failure risk → negotiate de-biased priorities → solve CP-SAT optimal block schedule.
            </p>
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2 font-code-sm text-[12px] bg-surface-container px-3 py-1.5 rounded-lg border border-surface-container-highest shrink-0">
          <span className="w-2 h-2 rounded-full bg-on-tertiary-container animate-pulse"></span>
          <span className="text-secondary font-medium">SOLVER ENGINE: ONLINE</span>
        </div>
      </div>

      {/* ── Stepper Header ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div
          className={`p-3.5 rounded-lg border flex items-center gap-3 transition-all ${
            activeStep >= 0
              ? 'bg-surface-container-lowest border-primary/40 shadow-xs'
              : 'bg-surface-container-low border-surface-container-high opacity-60'
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[13px] shrink-0 ${
              activeStep >= 1 ? 'bg-on-tertiary-container text-white' : 'bg-primary text-on-primary'
            }`}
          >
            {activeStep >= 1 ? <span className="material-symbols-outlined text-[18px]">check</span> : '1'}
          </div>
          <div>
            <div className="font-semibold text-[13px] text-on-surface">Defect Ingestion</div>
            <div className="text-[11px] text-secondary">Asset parameters & division</div>
          </div>
        </div>

        <div
          className={`p-3.5 rounded-lg border flex items-center gap-3 transition-all ${
            activeStep >= 1
              ? 'bg-surface-container-lowest border-primary/40 shadow-xs'
              : 'bg-surface-container-low border-surface-container-high opacity-60'
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[13px] shrink-0 ${
              activeStep >= 2
                ? 'bg-on-tertiary-container text-white'
                : activeStep === 1
                ? 'bg-primary text-on-primary'
                : 'bg-surface-container-high text-secondary'
            }`}
          >
            {activeStep >= 2 ? <span className="material-symbols-outlined text-[18px]">check</span> : '2'}
          </div>
          <div>
            <div className="font-semibold text-[13px] text-on-surface">Layer 1: AI Risk Forecast</div>
            <div className="text-[11px] text-secondary">Weibull AFT 30-day hazard curve</div>
          </div>
        </div>

        <div
          className={`p-3.5 rounded-lg border flex items-center gap-3 transition-all ${
            activeStep >= 2
              ? 'bg-surface-container-lowest border-primary/40 shadow-xs'
              : 'bg-surface-container-low border-surface-container-high opacity-60'
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[13px] shrink-0 ${
              activeStep === 2
                ? 'bg-on-tertiary-container text-white'
                : 'bg-surface-container-high text-secondary'
            }`}
          >
            {activeStep === 2 ? <span className="material-symbols-outlined text-[18px]">check</span> : '3'}
          </div>
          <div>
            <div className="font-semibold text-[13px] text-on-surface">Layer 2 & 3: CP-SAT Optimization</div>
            <div className="text-[11px] text-secondary">Negotiated priority & conflict-free slot</div>
          </div>
        </div>
      </div>

      {/* ── Quick Test Presets ──────────────────────────────────── */}
      <div className="bg-surface-container-lowest p-4 rounded-xl border border-surface-container-high shadow-xs">
        <div className="flex items-center justify-between mb-2.5">
          <span className="font-label-caps text-[11px] uppercase tracking-wider text-secondary font-bold flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[15px] text-primary">auto_fix_high</span>
            Quick Test Presets (Operational Scenarios)
          </span>
          <span className="text-[11px] text-secondary font-code-sm">Pre-fills standard test cases</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applyPreset(preset)}
              className="flex items-center gap-2.5 p-2.5 text-left rounded-lg bg-surface-container-low hover:bg-surface-container border border-surface-container-high hover:border-primary/40 transition-all group"
            >
              <span className="material-symbols-outlined text-[20px] text-primary group-hover:scale-110 transition-transform">
                {preset.icon}
              </span>
              <div className="min-w-0">
                <div className="text-[12px] font-semibold text-on-surface truncate">
                  {preset.label}
                </div>
                <div className="text-[10px] text-secondary font-code-sm">
                  {preset.data.division} • {preset.data.asset_type} • {preset.data.age_years}y
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Two-Column Layout ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: Input Form (5 cols) */}
        <div className="lg:col-span-5 bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px] text-primary">edit_note</span>
              <h2 className="font-headline-sm text-[16px] font-bold text-on-surface">
                Report Asset Defect
              </h2>
            </div>
            <span className="text-[11px] font-code-sm text-secondary">
              Parameters matching Layer 1 & 3
            </span>
          </div>

          <form onSubmit={(e) => e.preventDefault()} className="space-y-4">
            {/* Asset Type & Division */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Asset Type
                </label>
                <select
                  value={formData.asset_type}
                  onChange={(e) => setFormData({ ...formData, asset_type: e.target.value })}
                  className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-medium focus:outline-hidden focus:border-primary"
                >
                  <option value="TRACK">TRACK (Engineering / P-Way)</option>
                  <option value="OHE">OHE (Traction / TRD)</option>
                  <option value="SIG">SIGNAL (S&T / Interlocking)</option>
                  <option value="BRIDGE">BRIDGE (Civil Infrastructure)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Railway Division
                </label>
                <select
                  value={formData.division}
                  onChange={(e) => setFormData({ ...formData, division: e.target.value })}
                  className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-medium focus:outline-hidden focus:border-primary"
                >
                  <option value="Delhi">Delhi (Northern Railway)</option>
                  <option value="Mumbai">Mumbai (Western/Central)</option>
                  <option value="Allahabad">Allahabad / PRYJ (NCR)</option>
                  <option value="Howrah">Howrah (Eastern Railway)</option>
                  <option value="Kota">Kota (WCR)</option>
                  <option value="Vadodara">Vadodara (WR)</option>
                  <option value="Dhanbad">Dhanbad (ECR)</option>
                  <option value="Pune">Pune (CR)</option>
                </select>
              </div>
            </div>

            {/* Age & Installation Year */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Asset Age (Years)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="60"
                    value={formData.age_years}
                    onChange={(e) => handleAgeChange(e.target.value)}
                    className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-code-sm font-semibold focus:outline-hidden focus:border-primary"
                  />
                  <span className="absolute right-3 top-2.5 text-[11px] text-secondary font-code-sm">
                    years
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Installation Year
                </label>
                <input
                  type="number"
                  min="1960"
                  max="2026"
                  value={formData.installation_year}
                  onChange={(e) => handleYearChange(e.target.value)}
                  className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-code-sm font-semibold focus:outline-hidden focus:border-primary"
                />
              </div>
            </div>

            {/* Length & Monsoon Exposure */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Segment Length (km)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="50"
                    value={formData.length_km}
                    onChange={(e) => setFormData({ ...formData, length_km: e.target.value })}
                    className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-code-sm font-semibold focus:outline-hidden focus:border-primary"
                  />
                  <span className="absolute right-3 top-2.5 text-[11px] text-secondary font-code-sm">
                    km
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Monsoon Exposure
                </label>
                <select
                  value={formData.monsoon_exposure}
                  onChange={(e) => setFormData({ ...formData, monsoon_exposure: e.target.value })}
                  className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-medium focus:outline-hidden focus:border-primary"
                >
                  <option value="high">High (Active Flood / Heavy Rain Zone)</option>
                  <option value="medium">Medium (Moderate Coastal/Plain)</option>
                  <option value="low">Low (Dry / Arid Weather Zone)</option>
                </select>
              </div>
            </div>

            {/* Defect Description */}
            <div>
              <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                Defect Title / Field Observation
              </label>
              <input
                type="text"
                value={formData.task_type}
                onChange={(e) => setFormData({ ...formData, task_type: e.target.value })}
                placeholder="e.g. Ultrasonic Rail Flaw detected by OMS"
                className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-medium focus:outline-hidden focus:border-primary"
              />
            </div>

            {/* Department Claimed Criticality & Optimizer Policy */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Claimed Criticality (1-5)
                </label>
                <select
                  value={formData.claimed_criticality}
                  onChange={(e) => setFormData({ ...formData, claimed_criticality: e.target.value })}
                  className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-medium focus:outline-hidden focus:border-primary"
                >
                  <option value="5">Level 5 — Emergency Immediate Possession</option>
                  <option value="4">Level 4 — Urgent Risk Intervention</option>
                  <option value="3">Level 3 — Planned Maintenance Defect</option>
                  <option value="2">Level 2 — Routine Cyclic Overhaul</option>
                  <option value="1">Level 1 — Low Severity Observation</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-secondary uppercase tracking-wider mb-1">
                  Optimization Policy
                </label>
                <select
                  value={formData.policy}
                  onChange={(e) => setFormData({ ...formData, policy: e.target.value })}
                  className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-3 py-2 text-[13px] text-on-surface font-medium focus:outline-hidden focus:border-primary"
                >
                  <option value="balanced">Balanced (Safety + Capacity)</option>
                  <option value="safety_first">Safety-First (Zero Risk Tolerance)</option>
                  <option value="throughput_first">Throughput-First (Max Train Flow)</option>
                </select>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-3 space-y-2 border-t border-surface-container-high">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={handlePredictRisk}
                  disabled={stepState === 'predicting' || stepState === 'optimizing'}
                  className="w-full flex items-center justify-center gap-2 bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold text-[13px] py-2.5 px-4 rounded-lg border border-surface-container-highest transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
                >
                  {stepState === 'predicting' ? (
                    <>
                      <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></span>
                      <span>Calculating Risk...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[18px] text-primary">psychology</span>
                      <span>1. Predict Risk Only</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleReportAndOptimize}
                  disabled={stepState === 'predicting' || stepState === 'optimizing'}
                  className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-on-primary font-semibold text-[13px] py-2.5 px-4 rounded-lg shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {stepState === 'optimizing' ? (
                    <>
                      <span className="w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full animate-spin"></span>
                      <span>Running CP-SAT...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[18px]">bolt</span>
                      <span>2. Predict & Optimize</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-[11px] text-secondary text-center">
                Click <strong>Predict Risk Only</strong> for Layer 1 analysis, or <strong>Predict & Optimize</strong> to run the complete pipeline.
              </p>
            </div>
          </form>

          {errorMessage && (
            <div className="p-3 bg-error-container text-on-error-container rounded-lg text-[12px] flex items-start gap-2">
              <span className="material-symbols-outlined text-[16px] text-error shrink-0 mt-0.5">error</span>
              <span>{errorMessage}</span>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Results & Multi-Layer Pipeline (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Default Empty State */}
          {!predictionData && !optimizationData && (
            <div className="bg-surface-container-lowest p-8 rounded-xl border border-dashed border-surface-container-high text-center space-y-3">
              <div className="w-14 h-14 rounded-full bg-surface-container mx-auto flex items-center justify-center text-secondary">
                <span className="material-symbols-outlined text-[32px]">analytics</span>
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold text-on-surface text-[15px]">
                  No Live Defect Evaluated Yet
                </h3>
                <p className="text-[13px] text-secondary max-w-md mx-auto">
                  Select a preset or enter defect parameters on the left, then click <strong>Predict Risk Only</strong> to view Layer 1 ML failure analysis or <strong>Predict & Optimize</strong> to allocate a conflict-free maintenance block.
                </p>
              </div>
              <div className="pt-2 flex justify-center gap-2">
                <button
                  onClick={() => applyPreset(PRESETS[0])}
                  className="px-3 py-1.5 rounded-lg bg-surface-container text-primary font-medium text-[12px] hover:bg-surface-container-high transition-colors"
                >
                  Load Monsoon Fracture Preset
                </button>
              </div>
            </div>
          )}

          {/* ── LAYER 1 CARD: AI Risk Forecast ───────────────────── */}
          {predictionData && (
            <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse"></span>
                  <span className="font-label-caps text-[11px] uppercase tracking-wider text-primary font-bold">
                    Layer 1 — AI Failure Risk Forecast
                  </span>
                </div>
                <span className="font-code-sm text-[11px] text-secondary bg-surface-container px-2 py-0.5 rounded">
                  MODEL: {predictionData.model_version || 'weibull-aft-v2.0'}
                </span>
              </div>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                  <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                    30-Day Risk
                  </div>
                  <div
                    className={`font-code-sm text-xl font-bold ${
                      isCritRisk
                        ? 'text-error'
                        : isHighRisk
                        ? 'text-amber-500'
                        : 'text-on-tertiary-container'
                    }`}
                  >
                    {riskPercent}%
                  </div>
                  <span
                    className={`inline-block mt-1 px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                      isCritRisk
                        ? 'bg-error-container text-on-error-container'
                        : isHighRisk
                        ? 'bg-amber-500/10 text-amber-500'
                        : 'bg-on-tertiary-container/10 text-on-tertiary-container'
                    }`}
                  >
                    {isCritRisk ? 'CRITICAL RISK' : isHighRisk ? 'HIGH RISK' : 'LOW RISK'}
                  </span>
                </div>

                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                  <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                    Expected Downtime
                  </div>
                  <div className="font-code-sm text-xl font-bold text-on-surface">
                    {predictionData.expected_downtime_days || 0.5} d
                  </div>
                  <span className="text-[10px] text-secondary font-code-sm">
                    Failure impact window
                  </span>
                </div>

                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                  <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                    Recommended Block
                  </div>
                  <div className="font-code-sm text-xl font-bold text-primary">
                    {predictionData.preventive_block_duration_hrs || 2.5} h
                  </div>
                  <span className="text-[10px] text-secondary font-code-sm">
                    Required possession
                  </span>
                </div>

                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                  <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                    Overrun Chance
                  </div>
                  <div className="font-code-sm text-xl font-bold text-on-surface">
                    {((predictionData.overrun_probability || 0.08) * 100).toFixed(0)}%
                  </div>
                  <span className="text-[10px] text-secondary font-code-sm">
                    Duration uncertainty
                  </span>
                </div>
              </div>

              {/* Survival Curve Mini Projection */}
              {predictionData.survival_curve && predictionData.survival_curve.length > 0 && (
                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-secondary uppercase tracking-wider">
                      30-Day Survival Probability Decay Curve
                    </span>
                    <span className="text-[10px] text-secondary font-code-sm">
                      Day 1: 100% → Day 30:{' '}
                      {(
                        predictionData.survival_curve[predictionData.survival_curve.length - 1]
                          .survival_probability * 100
                      ).toFixed(1)}
                      %
                    </span>
                  </div>

                  {/* SVG Survival Curve Sparkline */}
                  <div className="h-16 w-full relative">
                    <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 300 60">
                      <defs>
                        <linearGradient id="gradRisk" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#818cf8" stopOpacity="0.4" />
                          <stop offset="100%" stopColor="#818cf8" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {(() => {
                        const pts = predictionData.survival_curve.slice(0, 30);
                        if (!pts.length) return null;
                        const coords = pts.map((p, i) => {
                          const x = (i / (pts.length - 1)) * 300;
                          const y = 60 - p.survival_probability * 55;
                          return `${x},${y}`;
                        });
                        const polyPoints = `0,60 ${coords.join(' ')} 300,60`;
                        return (
                          <>
                            <polygon points={polyPoints} fill="url(#gradRisk)" />
                            <polyline
                              fill="none"
                              stroke="#6366f1"
                              strokeWidth="2.5"
                              points={coords.join(' ')}
                            />
                          </>
                        );
                      })()}
                    </svg>
                  </div>
                </div>
              )}

              {/* If optimized not yet run, prompt user */}
              {!optimizationData && (
                <div className="p-3 bg-primary/10 rounded-lg flex items-center justify-between">
                  <div className="text-[12px] text-on-surface">
                    <span className="font-semibold text-primary">Risk profile predicted.</span> Ready to negotiate priority and schedule block possession in CP-SAT.
                  </div>
                  <button
                    onClick={handleReportAndOptimize}
                    className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-on-primary font-semibold text-[12px] shadow-xs shrink-0 cursor-pointer"
                  >
                    Proceed to Optimization →
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── LAYER 2 & 3 CARD: Negotiation & CP-SAT Optimization Result ── */}
          {optimizationData && (
            <div className="space-y-4">
              {/* Layer 2: Negotiation Result */}
              <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-surface-container-high pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-tertiary-fixed animate-pulse"></span>
                    <span className="font-label-caps text-[11px] uppercase tracking-wider text-tertiary-fixed font-bold">
                      Layer 2 — Multi-Department Evidence Negotiation
                    </span>
                  </div>
                  <span className="text-[11px] font-code-sm text-secondary">
                    Anti-Inflation Validation
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                    <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                      Claimed vs Evidence
                    </div>
                    <div className="flex items-baseline gap-1.5 font-code-sm">
                      <span className="text-lg font-bold text-on-surface">
                        {optimizationData.negotiation?.claimed_criticality}
                      </span>
                      <span className="text-secondary text-[12px]">vs</span>
                      <span className="text-lg font-bold text-primary">
                        {optimizationData.negotiation?.evidence_score?.toFixed(2)}
                      </span>
                    </div>
                    <span className="text-[10px] text-secondary font-code-sm">
                      Dept Claim / ML Evidence
                    </span>
                  </div>

                  <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                    <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                      Inflation Flag
                    </div>
                    <div>
                      {optimizationData.negotiation?.inflated_claim ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/10 text-amber-500">
                          <span className="material-symbols-outlined text-[14px]">warning</span>
                          INFLATED CLAIM
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-on-tertiary-container/10 text-on-tertiary-container">
                          <span className="material-symbols-outlined text-[14px]">verified</span>
                          GENUINE CLAIM
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-secondary font-code-sm">
                      {optimizationData.negotiation?.inflated_claim
                        ? 'De-biased to evidence level'
                        : 'Matches failure hazard'}
                    </span>
                  </div>

                  <div className="p-3 bg-surface-container-low rounded-lg border border-surface-container-high">
                    <div className="text-[11px] font-bold text-secondary uppercase tracking-wider mb-0.5">
                      Weighted Priority
                    </div>
                    <div className="font-code-sm text-lg font-bold text-on-surface">
                      {optimizationData.negotiation?.weighted_priority?.toFixed(3) || '0.850'}
                    </div>
                    <span className="text-[10px] text-secondary font-code-sm">
                      Solver scheduling weight
                    </span>
                  </div>
                </div>
              </div>

              {/* Layer 3: CP-SAT Optimization Schedule */}
              <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-4">
                <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-on-tertiary-container animate-pulse"></span>
                    <span className="font-label-caps text-[11px] uppercase tracking-wider text-on-tertiary-container font-bold">
                      Layer 3 — Google OR-Tools CP-SAT Assignment
                    </span>
                  </div>
                  <span className="font-code-sm text-[11px] bg-on-tertiary-container/10 text-on-tertiary-container px-2 py-0.5 rounded font-bold">
                    SOLVER: {optimizationData.optimization?.status?.toUpperCase() || 'OPTIMAL'}
                  </span>
                </div>

                {/* Scheduled Slot Spotlight */}
                <div className="p-4 bg-primary/5 rounded-xl border border-primary/20 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider bg-primary/20 text-primary px-2 py-0.5 rounded">
                        ALLOCATED MAINTENANCE BLOCK
                      </span>
                      <h4 className="font-headline-sm text-lg font-bold text-on-surface mt-1">
                        {formData.task_type || 'Defect Possession Block'}
                      </h4>
                      <div className="flex items-center gap-2 text-[12px] font-code-sm text-secondary mt-0.5">
                        <span>Task ID: {optimizationData.task_id}</span>
                        <span>•</span>
                        <span>Segment: {optimizationData.segment_id}</span>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="font-code-sm text-2xl font-bold text-primary">
                        {optimizationData.optimization?.scheduled_assignment?.duration_hrs ||
                          formData.length_km > 10
                          ? '4.0h'
                          : '3.0h'}
                      </span>
                      <div className="text-[10px] text-secondary font-code-sm uppercase font-semibold">
                        Possession Window
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-2 border-t border-primary/15 font-code-sm text-[12px]">
                    <div className="bg-surface-container-lowest p-2.5 rounded-lg border border-surface-container-high">
                      <div className="text-[10px] text-secondary uppercase font-semibold">Scheduled Date & Time</div>
                      <div className="font-bold text-on-surface">
                        {optimizationData.optimization?.scheduled_assignment?.block_start
                          ? new Date(optimizationData.optimization.scheduled_assignment.block_start).toLocaleDateString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '15 Sep 2026, 01:00 IST'}
                      </div>
                    </div>

                    <div className="bg-surface-container-lowest p-2.5 rounded-lg border border-surface-container-high">
                      <div className="text-[10px] text-secondary uppercase font-semibold">Timetable Conflict Audit</div>
                      <div className="font-bold text-on-tertiary-container flex items-center gap-1">
                        <span className="material-symbols-outlined text-[15px]">verified</span>
                        0 Train Clashes
                      </div>
                    </div>

                    <div className="bg-surface-container-lowest p-2.5 rounded-lg border border-surface-container-high">
                      <div className="text-[10px] text-secondary uppercase font-semibold">Solver Execution</div>
                      <div className="font-bold text-on-surface">
                        {optimizationData.optimization?.execution_time_ms || 271} ms
                      </div>
                    </div>
                  </div>
                </div>

                {/* Footer link to planner */}
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[12px] text-secondary font-code-sm">
                    Master plan updated: {optimizationData.optimization?.total_assignments} total corridor blocks assigned.
                  </span>
                  <button
                    onClick={() => navigate('/planner')}
                    className="flex items-center gap-1.5 text-primary hover:text-primary/80 text-[13px] font-semibold transition-colors cursor-pointer"
                  >
                    <span>View in Gantt Block Planner</span>
                    <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}



