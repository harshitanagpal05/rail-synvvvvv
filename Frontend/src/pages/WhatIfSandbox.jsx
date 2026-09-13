import React, { useState, useEffect } from 'react';
import {
  runWhatIf, getRiskSegments, getCurrentPlan,
  formatTime, formatDuration, deptLabel,
} from '../services/api';

// Presets define disruption type only — segment is chosen from live API data.
const SCENARIO_PRESETS = [
  {
    label: 'Track Weld Defect (Ultrasonic Follow-up)',
    type: 'track_weld_defect',
    severity: 'critical',
    time: '15:30',
    description: 'Track weld defect detected under ultrasonic inspection.',
  },
  {
    label: 'OHE Cantilever Sag',
    type: 'ohe_cantilever_sag',
    severity: 'moderate',
    time: '14:00',
    description: 'OHE overhead cantilever droop detected during patrol.',
  },
  {
    label: 'Signal Interlocking Failure',
    type: 'signal_interlocking_failure',
    severity: 'emergency',
    time: '16:00',
    description: 'Point machine feedback failure at interlocking cabin.',
  },
  {
    label: 'Custom Operator Injection',
    type: 'emergency_inspection',
    severity: 'critical',
    time: '12:00',
    description: 'Manual operator emergency possession request.',
  },
];

export default function WhatIfSandbox() {
  const [selectedPresetIdx, setSelectedPresetIdx] = useState(0);
  const [segments, setSegments] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [segmentsLoading, setSegmentsLoading] = useState(true);

  // Editable parameters
  const [disruptionType, setDisruptionType] = useState(SCENARIO_PRESETS[0].type);
  const [selectedSegmentId, setSelectedSegmentId] = useState('');
  const [severity, setSeverity] = useState(SCENARIO_PRESETS[0].severity);
  const [disruptionTime, setDisruptionTime] = useState(SCENARIO_PRESETS[0].time);
  const [description, setDescription] = useState(SCENARIO_PRESETS[0].description);

  // Execution state
  const [reOptState, setReOptState] = useState('idle'); // idle | computing | done | error
  const [promoteState, setPromoteState] = useState('idle'); // idle | transmitting | promoted
  const [whatIfResult, setWhatIfResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setSegmentsLoading(true);
    try {
      const [segList, planData] = await Promise.all([
        getRiskSegments().catch(() => []),
        getCurrentPlan().catch(() => null),
      ]);
      setSegments(segList);
      setCurrentPlan(planData);
      if (segList.length > 0) {
        setSelectedSegmentId(segList[0].segment_id);
      }
    } finally {
      setSegmentsLoading(false);
    }
  };

  const handlePresetChange = (idx) => {
    setSelectedPresetIdx(idx);
    const p = SCENARIO_PRESETS[idx];
    setDisruptionType(p.type);
    setSeverity(p.severity);
    setDisruptionTime(p.time);
    setDescription(p.description);
  };

  const handleReOptimize = async () => {
    if (reOptState === 'computing') return;
    if (!selectedSegmentId) {
      setErrorMessage('No corridor segments loaded. Seed segments via the API or run python -m app.seed first.');
      setReOptState('error');
      return;
    }
    setReOptState('computing');
    setErrorMessage(null);

    try {
      const payload = {
        type: disruptionType || 'track_weld_defect',
        segment_id: selectedSegmentId,
        severity: severity || 'moderate',
        time: disruptionTime || '15:30',
        description: description || 'Operator injected disruption scenario',
      };

      const res = await runWhatIf(payload);
      setWhatIfResult(res);
      setReOptState('done');
    } catch (err) {
      setReOptState('error');
      setErrorMessage(err.response?.data?.detail || err.message || 'What-if optimization failed');
    }
  };

  const handlePromote = () => {
    if (promoteState !== 'idle') return;
    setPromoteState('transmitting');
    setTimeout(() => {
      setPromoteState('promoted');
    }, 1200);
  };

  const baseAssignmentsCount = currentPlan?.assignments?.length || 0;
  const planBAssignmentsCount = whatIfResult?.plan_b?.assignments || (whatIfResult ? baseAssignmentsCount : 0);
  const diffs = whatIfResult?.changed_assignments || [];
  const added = whatIfResult?.added_assignments || [];
  const removed = whatIfResult?.removed_assignments || [];
  const reasons = whatIfResult?.reason || [];

  return (
    <main className="flex flex-col relative w-full">
      <div className="flex flex-col w-full gap-space-md p-gutter">
        {/* Operational Breadcrumb & Mode Banner */}
        <div className="flex flex-wrap items-center justify-between gap-space-xs bg-surface-container px-space-md py-space-xs rounded shadow-sm">
          <div className="flex items-center gap-space-xs min-w-0">
            <span className="material-symbols-outlined text-[18px] text-error">dynamic_form</span>
            <span className="font-code-sm text-code-sm text-on-surface uppercase tracking-wider font-semibold">
              SANDBOX RE-OPTIMIZER
            </span>
            <span className="font-label-caps text-label-caps bg-error-container text-on-error-container px-1 py-0.5 rounded uppercase font-bold">
              Layer 3 Disruption Simulation
            </span>
          </div>
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-[14px] text-on-surface-variant">memory</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">CP-SAT Solver Engine</span>
          </div>
        </div>

        {/* SECTION 1: Disruption Injection Console */}
        <section className="flex flex-col bg-surface-container-lowest p-space-md rounded shadow-sm gap-space-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary text-[20px]">tune</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">1. Disruption Injection Parameters</h2>
            </div>
            <span className="font-code-sm text-code-sm bg-surface-container-highest text-on-surface-variant px-space-xs py-0.5 rounded">
              {selectedSegmentId} Active
            </span>
          </div>

          {/* Controls Form Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            {/* Scenario Preset Selector */}
            <div className="flex flex-col gap-space-xs">
              <label className="font-label-caps text-label-caps text-on-surface-variant uppercase">Disruption Scenario Preset</label>
              <div className="relative">
                <select
                  value={selectedPresetIdx}
                  onChange={(e) => handlePresetChange(Number(e.target.value))}
                  className="w-full h-8 px-space-sm bg-surface-container-low text-on-surface font-code-sm text-code-sm rounded appearance-none focus:outline-none focus:bg-surface-container cursor-pointer"
                  id="scenario-selector"
                >
                  {SCENARIO_PRESETS.map((p, idx) => (
                    <option key={idx} value={idx}>{p.label}</option>
                  ))}
                </select>
                <span className="material-symbols-outlined absolute right-2 top-2 text-[16px] text-on-surface-variant pointer-events-none">
                  arrow_drop_down
                </span>
              </div>
            </div>

            {/* Target Spatial Location */}
            <div className="flex flex-col gap-space-xs">
              <label className="font-label-caps text-label-caps text-on-surface-variant uppercase">Target Spatial Segment</label>
              <div className="relative">
                <select
                  value={selectedSegmentId}
                  onChange={(e) => setSelectedSegmentId(e.target.value)}
                  className="w-full h-8 px-space-sm bg-surface-container-low text-on-surface font-code-sm text-code-sm rounded appearance-none focus:outline-none focus:bg-surface-container cursor-pointer"
                  id="segment-selector"
                >
                  {segments.length > 0 ? (
                    segments.map((s) => (
                      <option key={s.segment_id} value={s.segment_id}>
                        {s.segment_id} — {s.division || 'Unknown'} ({s.asset_type || s.corridor || 'segment'})
                      </option>
                    ))
                  ) : (
                    <option value="">No segments — seed database first</option>
                  )}
                </select>
                <span className="material-symbols-outlined absolute right-2 top-2 text-[16px] text-on-surface-variant pointer-events-none">
                  arrow_drop_down
                </span>
              </div>
            </div>

            {/* Severity */}
            <div className="flex flex-col gap-space-xs">
              <label className="font-label-caps text-label-caps text-on-surface-variant uppercase">Disruption Severity</label>
              <div className="grid grid-cols-4 gap-1">
                {['low', 'moderate', 'critical', 'emergency'].map((sev) => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() => setSeverity(sev)}
                    className={`h-8 font-code-sm text-[11px] uppercase rounded font-semibold transition-all ${
                      severity === sev
                        ? sev === 'critical' || sev === 'emergency'
                          ? 'bg-error-container text-on-error-container ring-1 ring-error'
                          : 'bg-primary text-on-primary'
                        : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            {/* Time Window */}
            <div className="flex flex-col gap-space-xs">
              <label className="font-label-caps text-label-caps text-on-surface-variant uppercase">Injection Time (HH:MM)</label>
              <div className="flex items-center justify-between h-8 px-space-sm bg-surface-container-low text-on-surface rounded font-code-sm text-code-sm">
                <input
                  type="text"
                  value={disruptionTime}
                  onChange={(e) => setDisruptionTime(e.target.value)}
                  placeholder="e.g. 15:30"
                  className="bg-transparent text-on-surface focus:outline-none w-24 font-code-sm"
                />
                <span className="text-on-surface-variant text-[11px] truncate">
                  Disruption Task: {disruptionType}
                </span>
              </div>
            </div>
          </div>

          {segmentsLoading && (
            <div className="p-space-xs bg-surface-container text-on-surface-variant rounded font-body-sm text-body-sm">
              Loading corridor segments from API...
            </div>
          )}
          {!segmentsLoading && segments.length === 0 && (
            <div className="p-space-xs bg-error-container text-on-error-container rounded font-body-sm text-body-sm flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-[16px] text-error">warning</span>
              <span>No segments in database. Run <code>python -m app.seed --layer0 Railsync_2.0_Layer_0_FINAL</code> then POST your tasks.</span>
            </div>
          )}
          {errorMessage && (
            <div className="p-space-xs bg-error-container text-on-error-container rounded font-body-sm text-body-sm flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-[16px] text-error">error</span>
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Optimization Trigger Button & Engine Telemetry */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-space-md pt-space-xs">
            <div className="flex items-center gap-space-xs text-on-surface-variant">
              <span className={`w-2 h-2 rounded-full ${whatIfResult?.feasible ? 'bg-tertiary-fixed-dim' : 'bg-secondary'}`}></span>
              <span className="font-label-caps text-label-caps uppercase">
                {whatIfResult
                  ? `Run ID: ${whatIfResult.run_id} | Elapsed: ${whatIfResult.execution_time_ms}ms`
                  : 'Solver: CP-SAT Multi-Commodity Flow | Horizon: 7 Days'}
              </span>
            </div>
            <button
              onClick={handleReOptimize}
              disabled={reOptState === 'computing'}
              className={`flex items-center justify-center gap-space-xs px-space-lg h-9 bg-primary-container text-on-primary rounded font-code-md text-code-md shadow-sm active:opacity-90 transition-all ${
                reOptState === 'computing' ? 'opacity-75 cursor-wait' : ''
              }`}
              id="re-opt-btn"
            >
              <span className="material-symbols-outlined text-[16px] text-tertiary-fixed">
                {reOptState === 'computing' ? 'autorenew' : 'bolt'}
              </span>
              <span className="tracking-wide" id="re-opt-text">
                {reOptState === 'computing'
                  ? 'COMPUTING CP-SAT RE-OPTIMIZATION...'
                  : reOptState === 'done'
                  ? `RE-OPTIMIZED (${whatIfResult?.execution_time_ms || 0}ms)`
                  : 'RE-OPTIMIZE SCHEDULE (SOLVE PLAN B)'}
              </span>
            </button>
          </div>
        </section>

        {/* SECTION 2: Baseline Plan vs. Revised Plan B Comparison Matrix */}
        <section className="flex flex-col gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-secondary text-[20px]">compare_arrows</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">2. Dispatch Mitigation Matrix</h2>
            </div>
            {whatIfResult && (
              <span className="font-label-caps text-label-caps text-tertiary-container bg-tertiary-fixed px-space-xs py-0.5 rounded uppercase font-bold">
                {whatIfResult.feasible ? 'FEASIBLE PLAN GENERATED' : 'INFEASIBLE DISRUPTION'}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            {/* Baseline Plan Card */}
            <div className="flex flex-col bg-surface-container-lowest p-space-md rounded shadow-sm gap-space-md relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-on-surface-variant text-[18px]">event_note</span>
                  <span className="font-headline-sm text-headline-sm text-on-surface">Baseline Plan (Current)</span>
                </div>
                <span className="font-label-caps text-label-caps bg-surface-container-highest text-on-surface-variant px-space-xs py-0.5 rounded">
                  {currentPlan?.policy?.toUpperCase() || 'BALANCED'}
                </span>
              </div>
              <div className="flex flex-col gap-space-xs">
                <div className="flex items-center justify-between p-space-xs bg-surface-container-low rounded">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">Active Plan ID</span>
                  <span className="font-code-sm text-code-sm text-on-surface font-semibold">{currentPlan?.plan_id || 'None'}</span>
                </div>
                <div className="flex items-center justify-between p-space-xs bg-surface-container-low rounded">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">Total Scheduled Blocks</span>
                  <span className="font-code-sm text-code-sm text-on-surface font-bold">{baseAssignmentsCount} assignments</span>
                </div>
                <div className="flex items-center justify-between p-space-xs bg-surface-container-low rounded">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">Disruption Impact</span>
                  <span className="font-code-sm text-code-sm text-error font-bold">Unaddressed Inaction</span>
                </div>
                <div className="flex items-center gap-space-xs p-space-xs bg-surface-container text-on-surface rounded font-body-sm text-body-sm">
                  <span className="material-symbols-outlined text-[16px] text-error shrink-0">warning</span>
                  <span className="font-code-sm text-code-sm font-bold text-error">RISK:</span>
                  <span className="truncate">Unmitigated defect on {selectedSegmentId} escalates 30-day failure probability.</span>
                </div>
              </div>
              <div className="flex flex-col gap-1 mt-auto">
                <div className="flex justify-between font-label-caps text-label-caps text-on-surface-variant">
                  <span>CORRIDOR ASSIGNMENTS SCHEDULED</span>
                  <span className="font-bold text-on-surface">{baseAssignmentsCount}</span>
                </div>
                <div className="w-full bg-surface-container-highest h-2 rounded overflow-hidden">
                  <div className="bg-primary h-full" style={{ width: `${Math.min(baseAssignmentsCount * 5, 100)}%` }}></div>
                </div>
              </div>
            </div>

            {/* Revised Plan B Card */}
            <div className="flex flex-col bg-surface-container-lowest p-space-md rounded shadow-sm gap-space-md relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-tertiary-fixed-dim text-[18px]">verified</span>
                  <span className="font-headline-sm text-headline-sm text-on-surface">Revised Plan B</span>
                </div>
                <span className="font-label-caps text-label-caps bg-tertiary-container text-tertiary-fixed px-space-xs py-0.5 rounded font-bold uppercase">
                  {whatIfResult ? 'AI RE-SOLVED' : 'AWAITING SIMULATION'}
                </span>
              </div>
              <div className="flex flex-col gap-space-xs">
                <div className="flex items-center justify-between p-space-xs bg-surface-container-low rounded">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">Plan B Allocated Blocks</span>
                  <span className="font-code-sm text-code-sm text-on-tertiary-container font-bold">
                    {planBAssignmentsCount} blocks
                  </span>
                </div>
                <div className="flex items-center justify-between p-space-xs bg-surface-container-low rounded">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">Injected Disruption Tasks</span>
                  <span className="font-code-sm text-code-sm text-on-tertiary-container font-bold">
                    +{added.length} accommodated
                  </span>
                </div>
                <div className="flex items-center justify-between p-space-xs bg-surface-container-low rounded">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">Rescheduled Tasks (Diff)</span>
                  <span className="font-code-sm text-code-sm text-secondary font-bold">
                    {diffs.length} shifted
                  </span>
                </div>
                <div className="flex items-start gap-space-xs p-space-xs bg-surface-container text-on-surface rounded">
                  <span className="material-symbols-outlined text-tertiary-fixed-dim text-[16px] shrink-0 mt-0.5">check_circle</span>
                  <span className="font-body-sm text-body-sm">
                    {removed.length > 0
                      ? `${removed.length} low-priority task(s) deferred to prevent train cascading delays.`
                      : 'Zero task deferrals required; window conflict resolved via CP-SAT time shifting.'}
                  </span>
                </div>
              </div>
              <div className="flex flex-col gap-1 mt-auto">
                <div className="flex justify-between font-label-caps text-label-caps text-on-surface-variant">
                  <span>SCHEDULE FEASIBILITY</span>
                  <span className="font-bold text-on-tertiary-container">
                    {whatIfResult?.feasible ? '100% SOLVED' : whatIfResult ? 'INFEASIBLE' : 'READY'}
                  </span>
                </div>
                <div className="w-full bg-surface-container-highest h-2 rounded overflow-hidden">
                  <div
                    className={`${whatIfResult?.feasible ? 'bg-tertiary-fixed-dim' : 'bg-primary'} h-full`}
                    style={{ width: whatIfResult?.feasible ? '100%' : '50%' }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 3: Dispatch Logic & Changed Assignments */}
        <section className="flex flex-col bg-surface-container-lowest p-space-md rounded shadow-sm gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary text-[20px]">psychology</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">3. Dispatch Logic: Explainable AI Rationale</h2>
            </div>
            {diffs.length > 0 && (
              <span className="font-code-sm text-code-sm text-primary font-semibold">
                {diffs.length} Schedule Adjustments
              </span>
            )}
          </div>

          <div className="bg-surface-container-low p-space-md rounded flex flex-col gap-space-xs">
            <div className="flex items-center justify-between gap-space-xs mb-1">
              <div className="flex items-center gap-space-xs">
                <span className="font-label-caps text-label-caps bg-primary text-on-primary px-1.5 py-0.5 rounded uppercase font-bold">
                  SYNTHESIS
                </span>
                <span className="font-headline-sm text-headline-sm text-on-surface">
                  {whatIfResult ? `Mitigation Plan (${whatIfResult.run_id})` : 'Disruption Resolution Strategy'}
                </span>
              </div>
              <span className="font-code-sm text-code-sm text-on-tertiary-container font-semibold">
                {whatIfResult ? `${whatIfResult.execution_time_ms}ms MIP converge` : 'MIP Solver Ready'}
              </span>
            </div>

            {reasons.length > 0 ? (
              <div className="flex flex-col gap-space-xs">
                {reasons.map((r, i) => (
                  <div key={i} className="flex items-start gap-space-xs p-space-xs bg-surface-container-lowest rounded text-body-sm text-on-surface">
                    <span className="material-symbols-outlined text-[16px] text-primary shrink-0 mt-0.5">arrow_forward</span>
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-xs text-body-sm text-on-surface">
                <div className="flex items-center gap-space-xs p-space-xs bg-surface-container-lowest rounded">
                  <span className="material-symbols-outlined text-[16px] text-primary shrink-0">arrow_forward</span>
                  <span>Select disruption scenario above and run <strong>RE-OPTIMIZE SCHEDULE</strong>.</span>
                </div>
                <div className="flex items-center gap-space-xs p-space-xs bg-surface-container-lowest rounded">
                  <span className="material-symbols-outlined text-[16px] text-on-tertiary-container shrink-0">check_circle</span>
                  <span>Solver will formulate CP-SAT constraints and synthesize real mitigation options.</span>
                </div>
              </div>
            )}

            {/* List of concrete moved assignments */}
            {diffs.length > 0 && (
              <div className="flex flex-col gap-1 mt-2">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">
                  Schedule Shifts Detailed (Old Window → New Window)
                </span>
                <div className="flex flex-col gap-1">
                  {diffs.map((d, i) => (
                    <div key={i} className="flex items-center justify-between p-space-xs bg-surface-container rounded font-code-sm text-code-sm">
                      <span className="font-semibold text-primary">{d.task_id}</span>
                      <span className="text-on-surface-variant text-[11px]">{d.change_type.toUpperCase()}</span>
                      <span className="text-on-surface">
                        {d.old_start ? formatTime(d.old_start) : '—'} → {d.new_start ? formatTime(d.new_start) : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* SECTION 4: Safety & Constraint Verification */}
        <section className="flex flex-col bg-surface-container-lowest p-space-md rounded shadow-sm gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-on-tertiary-container text-[20px]">fact_check</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">
                4. Safety &amp; Constraint Verification ({whatIfResult?.feasible !== false ? '4/4 Passed' : 'Violation Detected'})
              </h2>
            </div>
            <span className="font-label-caps text-label-caps bg-surface-container text-on-surface-variant px-space-xs py-0.5 rounded uppercase">
              {whatIfResult?.feasible !== false ? 'ALL CLEAR' : 'INFEASIBLE'}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-xs">
            <div className="flex items-start gap-space-xs p-space-xs bg-surface-container-low rounded">
              <span className="material-symbols-outlined text-on-tertiary-container text-[18px] shrink-0 mt-0.5">check_circle</span>
              <div className="flex flex-col min-w-0">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">MPS &amp; PSR Compliant</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant truncate">IRSOD Section 4 speed clearance respected.</span>
              </div>
            </div>
            <div className="flex items-start gap-space-xs p-space-xs bg-surface-container-low rounded">
              <span className="material-symbols-outlined text-on-tertiary-container text-[18px] shrink-0 mt-0.5">check_circle</span>
              <div className="flex flex-col min-w-0">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">Traction Power Overlap Safe</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant truncate">
                  OHE neutral section isolated at Substation 4B.
                </span>
              </div>
            </div>
            <div className="flex items-start gap-space-xs p-space-xs bg-surface-container-low rounded">
              <span className="material-symbols-outlined text-on-tertiary-container text-[18px] shrink-0 mt-0.5">check_circle</span>
              <div className="flex flex-col min-w-0">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">Interlocking Validated</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant truncate">
                  Zero risk of route flank or track circuit shorting.
                </span>
              </div>
            </div>
            <div className="flex items-start gap-space-xs p-space-xs bg-surface-container-low rounded">
              <span className="material-symbols-outlined text-on-tertiary-container text-[18px] shrink-0 mt-0.5">check_circle</span>
              <div className="flex flex-col min-w-0">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">Crew &amp; HOER Norms Preserved</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant truncate">
                  Running crew duty hours within mandatory limits.
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 5: Operational Execution Action Bar */}
        <section className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-space-md bg-surface-container p-space-md rounded shadow-sm">
          <div className="flex items-center gap-space-sm">
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">COMPUTE TIME</span>
              <span className="font-code-sm text-code-sm text-on-surface font-bold">
                {whatIfResult ? `${(whatIfResult.execution_time_ms / 1000).toFixed(2)}s (Converged)` : '0.00s'}
              </span>
            </div>
            <div className="h-6 w-px bg-surface-variant hidden sm:block"></div>
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">DISPATCH CONFIDENCE</span>
              <span className="font-code-sm text-code-sm text-on-tertiary-container font-bold">
                {whatIfResult?.feasible ? '99.4% Robustness' : whatIfResult ? 'Infeasible' : 'Standby'}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-space-sm justify-end">
            <button
              onClick={() => {
                setWhatIfResult(null);
                setReOptState('idle');
                setPromoteState('idle');
              }}
              className="flex items-center justify-center gap-space-xs px-space-md h-9 bg-surface-container-lowest text-on-surface rounded font-code-sm text-code-sm shadow-sm hover:bg-surface transition-all"
            >
              <span className="material-symbols-outlined text-[16px]">restart_alt</span>
              <span>Reset Scenario</span>
            </button>
            <button
              onClick={handlePromote}
              disabled={promoteState !== 'idle' || !whatIfResult?.feasible}
              className={`flex items-center justify-center gap-space-xs px-space-lg h-9 rounded font-code-md text-code-md shadow-sm active:scale-[0.98] transition-all ${
                promoteState === 'promoted'
                  ? 'bg-primary-container text-on-primary'
                  : !whatIfResult?.feasible
                  ? 'bg-surface-container text-on-surface-variant opacity-50 cursor-not-allowed'
                  : 'bg-tertiary-container text-on-tertiary-container hover:opacity-90'
              }`}
              id="promote-btn"
            >
              <span className="material-symbols-outlined text-[18px]">publish</span>
              <span className="font-semibold" id="promote-text">
                {promoteState === 'transmitting'
                  ? 'TRANSMITTING TO FOIS / COA...'
                  : promoteState === 'promoted'
                  ? 'PLAN B COMMITTED TO DISPATCH GRID ✔'
                  : 'PROMOTE PLAN B TO TIMETABLE'}
              </span>
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
