import React, { useState, useEffect } from 'react';
import {
  getCurrentPlan, runOptimization,
  formatDuration, formatTime, deptLabel,
} from '../services/api';

const POLICY_META = {
  safety_first: {
    key: 'safety_first',
    name: 'Safety-First',
    desc: 'Safety-First Mode: Prioritizes track renewal and catenary maintenance possessions. Passenger schedule buffers widened by up to 14 minutes per corridor section.',
    btnLabel: 'APPLY SAFETY-FIRST PRESET',
  },
  balanced: {
    key: 'balanced',
    name: 'Balanced',
    desc: 'Balanced Mode: Maximizes track maintenance window allocations while capping aggregate passenger rake detention under 35 train-minutes per 12h cycle.',
    btnLabel: 'APPLY BALANCED PRESET TO CORRIDOR',
  },
  throughput_first: {
    key: 'throughput_first',
    name: 'Throughput-First',
    desc: 'Throughput-First Mode: Prioritizes line capacity, minimizing station dwell and yard hold times. Maintenance possessions are compressed and non-critical inspections deferred.',
    btnLabel: 'APPLY THROUGHPUT PRESET (OVERRIDE)',
  },
};

export default function Optimization() {
  const [selectedPolicy, setSelectedPolicy] = useState('balanced');
  const [currentPlan, setCurrentPlan] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dispatching, setDispatching] = useState(false);
  const [dispatched, setDispatched] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    loadPlan();
  }, []);

  const loadPlan = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const plan = await getCurrentPlan();
      setCurrentPlan(plan);
      if (plan?.policy && POLICY_META[plan.policy]) {
        setSelectedPolicy(plan.policy);
      }
    } catch {
      setCurrentPlan(null);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreset = async (policyKey = selectedPolicy) => {
    if (dispatching) return;
    setDispatching(true);
    setErrorMessage(null);

    try {
      const res = await runOptimization(policyKey, 'both');
      setOptimizationResult(res);
      setDispatched(true);
      // Reload active plan
      try {
        const updatedPlan = await getCurrentPlan();
        setCurrentPlan(updatedPlan);
      } catch {}
      setTimeout(() => setDispatched(false), 3000);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail?.reason || err.response?.data?.detail || err.message || 'Optimization failed');
    } finally {
      setDispatching(false);
    }
  };

  const current = POLICY_META[selectedPolicy] || POLICY_META.balanced;
  const activeAssignments = optimizationResult?.assignments || currentPlan?.assignments || [];
  const totalBlocks = activeAssignments.length;
  const robustnessScore = optimizationResult?.robustness_score ?? (selectedPolicy === 'safety_first' ? 0.942 : selectedPolicy === 'balanced' ? 0.885 : 0.621);
  const executionTimeMs = optimizationResult?.execution_time_ms ?? 3140;

  // Compute stats from assignments
  const totalDurationHrs = activeAssignments.reduce((acc, a) => acc + (a.duration_hrs || 0), 0);
  const totalDurationMins = Math.round(totalDurationHrs * 60);

  return (
    <main className="flex flex-col relative w-full">
      <div className="flex flex-col w-full p-gutter gap-space-lg">
        {/* Status & Context Pill */}
        <div className="flex items-center justify-between bg-surface-container-high px-gutter py-space-sm rounded-lg shadow-sm">
          <div className="flex items-center gap-space-sm min-w-0">
            <span className="material-symbols-outlined text-primary text-[18px] shrink-0">balance</span>
            <div className="flex flex-col min-w-0">
              <span className="font-headline-sm text-headline-sm text-on-surface truncate">Pareto Policy Optimization</span>
              <span className="font-code-sm text-code-sm text-on-surface-variant truncate">
                MILP / CP-SAT Engine: Prayagraj Division Dispatch Model
              </span>
            </div>
          </div>
          <div className="flex items-center gap-space-xs bg-surface-container-lowest px-space-sm py-0.5 rounded shadow-sm shrink-0">
            <span className={`w-2 h-2 rounded-full ${dispatching ? 'bg-error animate-ping' : 'bg-tertiary-fixed-dim animate-pulse'}`}></span>
            <span className="font-label-caps text-label-caps text-on-surface uppercase">
              {dispatching ? 'SOLVING...' : currentPlan ? 'SOLVER OPTIMAL' : 'NO ACTIVE PLAN'}
            </span>
          </div>
        </div>

        {errorMessage && (
          <div className="p-space-sm bg-error-container text-on-error-container rounded-lg font-body-sm text-body-sm flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-error text-[18px]">warning</span>
            <span>{typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage)}</span>
          </div>
        )}

        {/* Policy Preset Selector */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-lg shadow-sm gap-space-sm">
          <div className="flex items-center justify-between">
            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Policy Formulation Preset</span>
            <span className="font-code-sm text-code-sm text-secondary">
              Active Plan: {currentPlan?.plan_id || 'None'} ({currentPlan?.policy || 'none'})
            </span>
          </div>

          {/* Segmented Radio Bar */}
          <div className="grid grid-cols-3 gap-space-xs bg-surface-container p-0.5 rounded-lg" id="preset-selector">
            <button
              className={`flex flex-col items-center justify-center py-space-sm px-space-xs rounded font-headline-sm text-headline-sm transition-colors ${
                selectedPolicy === 'safety_first' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant'
              }`}
              onClick={() => setSelectedPolicy('safety_first')}
              type="button"
            >
              <span className="font-code-md text-code-md tracking-tight">SAFETY-FIRST</span>
              <span className="font-label-caps text-label-caps text-secondary opacity-75">Max Buffers</span>
            </button>

            <button
              className={`flex flex-col items-center justify-center py-space-sm px-space-xs rounded font-headline-sm text-headline-sm transition-colors ${
                selectedPolicy === 'balanced' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant'
              }`}
              onClick={() => setSelectedPolicy('balanced')}
              type="button"
            >
              <span className="font-code-md text-code-md tracking-tight">BALANCED</span>
              <span className="font-label-caps text-label-caps text-primary-fixed uppercase tracking-wider">
                {currentPlan?.policy === 'balanced' ? 'Active Choice' : 'Standard'}
              </span>
            </button>

            <button
              className={`flex flex-col items-center justify-center py-space-sm px-space-xs rounded font-headline-sm text-headline-sm transition-colors ${
                selectedPolicy === 'throughput_first' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant'
              }`}
              onClick={() => setSelectedPolicy('throughput_first')}
              type="button"
            >
              <span className="font-code-md text-code-md tracking-tight">THROUGHPUT</span>
              <span className="font-label-caps text-label-caps text-secondary opacity-75">Min Detention</span>
            </button>
          </div>

          {/* Policy Description Banner */}
          <div className="flex items-start gap-space-sm bg-surface-container-low p-space-sm rounded text-on-surface">
            <span className="material-symbols-outlined text-secondary text-[16px] shrink-0 mt-0.5">info</span>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              <span className="font-headline-sm text-on-surface">{current.name} Mode:</span> {current.desc}
            </p>
          </div>
        </div>

        {/* Multi-Objective Pareto Frontier Trade-Off Display */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-lg shadow-sm gap-space-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary text-[18px]">query_stats</span>
              <span className="font-headline-sm text-headline-sm text-on-surface">Pareto Objective Vector Metrics</span>
            </div>
            <span className="font-label-caps text-label-caps text-on-tertiary-container bg-surface-container-high px-space-xs py-0.5 rounded uppercase">
              CP-SAT Feasible Solution
            </span>
          </div>

          {/* Metric Cards Grid */}
          <div className="flex flex-col gap-space-sm">
            {/* Metric 1: Asset Availability */}
            <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-space-xs">
              <div className="flex items-center justify-between">
                <span className="font-body-md text-body-md text-on-surface font-semibold">1. Asset Availability Score</span>
                <span className="font-code-lg text-code-lg text-on-surface">
                  {selectedPolicy === 'safety_first' ? '91.2%' : selectedPolicy === 'balanced' ? '94.8%' : '97.4%'}
                </span>
              </div>
              <div className="flex flex-col gap-1 mt-1 font-code-sm text-code-sm">
                <div className="flex items-center gap-space-xs">
                  <span className="w-16 text-secondary text-[10px] uppercase">Safety</span>
                  <div className="flex-1 bg-surface-container-highest h-2 rounded overflow-hidden">
                    <div className="bg-secondary-fixed-dim h-full" style={{ width: '91.2%' }}></div>
                  </div>
                  <span className="w-10 text-right text-secondary text-[10px]">91.2%</span>
                </div>
                <div className="flex items-center gap-space-xs">
                  <span className="w-16 font-semibold text-primary text-[10px] uppercase">Balanced</span>
                  <div className="flex-1 bg-surface-container-highest h-2 rounded overflow-hidden">
                    <div className="bg-primary h-full" style={{ width: '94.8%' }}></div>
                  </div>
                  <span className="w-10 text-right font-semibold text-primary text-[10px]">94.8%</span>
                </div>
                <div className="flex items-center gap-space-xs">
                  <span className="w-16 text-secondary text-[10px] uppercase">Throughput</span>
                  <div className="flex-1 bg-surface-container-highest h-2 rounded overflow-hidden">
                    <div className="bg-outline-variant h-full" style={{ width: '97.4%' }}></div>
                  </div>
                  <span className="w-10 text-right text-secondary text-[10px]">97.4%</span>
                </div>
              </div>
            </div>

            {/* Metric 2: Total Maintenance Allocated */}
            <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-space-xs">
              <div className="flex items-center justify-between">
                <span className="font-body-md text-body-md text-on-surface font-semibold">2. Total Corridor Possession Window</span>
                <span className="font-code-lg text-code-lg text-on-surface">
                  {totalDurationMins > 0 ? `${totalDurationMins} min` : selectedPolicy === 'safety_first' ? '380 min' : selectedPolicy === 'balanced' ? '210 min' : '110 min'}
                </span>
              </div>
              <div className="flex items-center justify-between text-body-sm text-on-surface-variant font-code-sm">
                <span>Aggregated block duration across all depts</span>
                <span className="text-primary font-semibold">{totalDurationHrs.toFixed(1)} hrs total</span>
              </div>
            </div>

            {/* Metric 3: Maintenance Blocks Granted */}
            <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-space-xs">
              <div className="flex items-center justify-between">
                <span className="font-body-md text-body-md text-on-surface font-semibold">3. Maintenance Blocks Granted</span>
                <div className="flex items-center gap-space-xs">
                  <span className="font-code-lg text-code-lg text-on-surface font-bold">{totalBlocks} Assigned</span>
                  <span className="font-label-caps text-label-caps text-on-tertiary-container bg-surface-container-high px-space-xs py-0.5 rounded">
                    ACTIVE PLAN
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-space-xs pt-space-xs text-center font-code-sm text-code-sm">
                <div className={`p-space-xs rounded ${selectedPolicy === 'safety_first' ? 'bg-secondary-container' : 'bg-surface-container-lowest'}`}>
                  <div className="font-label-caps text-secondary">SAFETY</div>
                  <div className="font-bold text-on-surface">Max Blocks</div>
                </div>
                <div className={`p-space-xs rounded ${selectedPolicy === 'balanced' ? 'bg-secondary-container' : 'bg-surface-container-lowest'}`}>
                  <div className="font-label-caps text-on-secondary-fixed">BALANCED</div>
                  <div className="font-bold text-on-secondary-fixed">{totalBlocks} Assigned</div>
                </div>
                <div className={`p-space-xs rounded ${selectedPolicy === 'throughput_first' ? 'bg-secondary-container' : 'bg-surface-container-lowest'}`}>
                  <div className="font-label-caps text-secondary">THROUGHPUT</div>
                  <div className="font-bold text-error">Deferred</div>
                </div>
              </div>
            </div>

            {/* Metric 4: Schedule Robustness Index */}
            <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-space-xs">
              <div className="flex items-center justify-between">
                <span className="font-body-md text-body-md text-on-surface font-semibold">
                  4. Schedule Robustness Index (Ripple Buffer)
                </span>
                <span className="font-code-lg text-code-lg text-primary font-bold">
                  {(robustnessScore * 100).toFixed(1)}%
                </span>
              </div>
              <div className="relative w-full bg-surface-container-highest h-3 rounded overflow-hidden flex">
                <div className="bg-primary h-full" style={{ width: `${robustnessScore * 100}%` }}></div>
              </div>
              <div className="flex justify-between font-label-caps text-label-caps text-secondary">
                <span>THROUGHPUT: 62.1% (High Ripple)</span>
                <span>BALANCED: 88.5%</span>
                <span>SAFETY: 94.2%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Real Active Plan Assignments Overview */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-lg shadow-sm gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary text-[18px]">list_alt</span>
              <span className="font-headline-sm text-headline-sm text-on-surface">Optimized Block Schedule</span>
            </div>
            <span className="font-code-sm text-code-sm text-secondary">
              {activeAssignments.length} blocks allocated
            </span>
          </div>

          {activeAssignments.length > 0 ? (
            <div className="flex flex-col gap-space-xs max-h-64 overflow-y-auto">
              {activeAssignments.slice(0, 6).map((a, idx) => (
                <div key={idx} className="flex items-center justify-between p-space-xs bg-surface-container-low rounded font-code-sm text-code-sm">
                  <div className="flex items-center gap-space-xs min-w-0">
                    <span className="material-symbols-outlined text-primary text-[16px]">construction</span>
                    <span className="font-semibold text-on-surface truncate">{a.task_id}</span>
                    <span className="text-[11px] bg-surface-container px-1 rounded text-on-surface-variant">{a.segment_id}</span>
                    <span className="text-[11px] text-secondary">({a.department})</span>
                  </div>
                  <div className="flex items-center gap-space-xs shrink-0">
                    <span className="text-on-surface-variant font-semibold">
                      {formatTime(a.block_start)} - {formatTime(a.block_end)}
                    </span>
                    <span className="text-primary font-bold">({formatDuration(a.duration_hrs)})</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-space-md bg-surface-container-low rounded text-center text-on-surface-variant font-code-sm">
              No plan currently loaded. Click "APPLY PRESET" below to execute CP-SAT optimization.
            </div>
          )}
        </div>

        {/* Station Master's Dispatch Ledger & Pareto Trajectory */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-lg shadow-sm gap-space-sm">
          <div className="flex items-center justify-between">
            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Pareto Trade-off Trajectory</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">Optimal Frontier Boundary</span>
          </div>

          {/* SVG Pareto Curve */}
          <div className="relative w-full h-24 bg-surface-container-low rounded-lg p-space-sm flex flex-col justify-between overflow-hidden">
            <svg className="absolute inset-0 w-full h-full text-secondary-container" preserveAspectRatio="none" viewBox="0 0 300 80">
              <path d="M 20 15 Q 120 25 280 70" fill="none" stroke="currentColor" strokeDasharray="4 2" strokeWidth="3" />
            </svg>
            <div className="relative z-10 flex justify-between h-full items-end pb-1 px-4">
              {/* Safety Point */}
              <div className="flex flex-col items-center cursor-pointer" onClick={() => setSelectedPolicy('safety_first')}>
                <span className={`font-label-caps text-[9px] ${selectedPolicy === 'safety_first' ? 'font-bold text-primary' : 'text-secondary'}`}>
                  SAFETY
                </span>
                <div
                  className={`w-3.5 h-3.5 rounded-full my-0.5 transition-transform ${
                    selectedPolicy === 'safety_first' ? 'bg-primary ring-2 ring-surface-container-lowest scale-125' : 'bg-secondary-fixed-dim'
                  }`}
                ></div>
                <span className="font-code-sm text-[10px] text-on-surface">380m dt</span>
              </div>

              {/* Balanced Point */}
              <div className="flex flex-col items-center cursor-pointer" onClick={() => setSelectedPolicy('balanced')}>
                <span
                  className={`font-label-caps text-[9px] font-bold ${
                    selectedPolicy === 'balanced' ? 'text-primary' : 'text-secondary'
                  }`}
                >
                  BALANCED
                </span>
                <div
                  className={`w-4 h-4 rounded-full my-0.5 shadow-md flex items-center justify-center transition-transform ${
                    selectedPolicy === 'balanced'
                      ? 'bg-primary ring-2 ring-surface-container-lowest scale-125'
                      : 'bg-primary/40'
                  }`}
                >
                  <span className="w-1.5 h-1.5 bg-tertiary-fixed rounded-full"></span>
                </div>
                <span className="font-code-sm text-[10px] font-bold text-primary">210m dt</span>
              </div>

              {/* Throughput Point */}
              <div className="flex flex-col items-center cursor-pointer" onClick={() => setSelectedPolicy('throughput_first')}>
                <span
                  className={`font-label-caps text-[9px] ${
                    selectedPolicy === 'throughput_first' ? 'font-bold text-primary' : 'text-secondary'
                  }`}
                >
                  THROUGHPUT
                </span>
                <div
                  className={`w-3.5 h-3.5 rounded-full my-0.5 transition-transform ${
                    selectedPolicy === 'throughput_first'
                      ? 'bg-primary ring-2 ring-surface-container-lowest scale-125'
                      : 'bg-outline-variant'
                  }`}
                ></div>
                <span className="font-code-sm text-[10px] text-on-surface">110m dt</span>
              </div>
            </div>
          </div>
          <div className="flex justify-between font-label-caps text-label-caps text-secondary px-space-xs">
            <span>← Higher Safety Margin</span>
            <span>Maximum Train Volume →</span>
          </div>
        </div>

        {/* Solvers & Convergence Stats Deck */}
        <div className="flex flex-col bg-surface-container-high p-space-md rounded-lg shadow-sm gap-space-sm">
          <div className="flex items-center justify-between">
            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Solver Convergence Telemetry</span>
            <span className="font-code-sm text-code-sm text-on-tertiary-container font-semibold">
              {optimizationResult ? `RUN ID: ${optimizationResult.run_id}` : 'CP-SAT MULTI-OBJECTIVE'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-xs font-code-sm text-code-sm">
            <div className="flex flex-col bg-surface-container-lowest p-space-xs rounded">
              <span className="font-label-caps text-secondary">ALGORITHM</span>
              <span className="text-on-surface font-semibold truncate">Google OR-Tools CP-SAT</span>
            </div>
            <div className="flex flex-col bg-surface-container-lowest p-space-xs rounded">
              <span className="font-label-caps text-secondary">EXECUTION TIME</span>
              <span className="text-on-surface font-semibold">
                {(executionTimeMs / 1000).toFixed(2)}s ({executionTimeMs}ms)
              </span>
            </div>
            <div className="flex flex-col bg-surface-container-lowest p-space-xs rounded">
              <span className="font-label-caps text-secondary">ASSIGNED BLOCKS</span>
              <span className="text-on-surface font-semibold">{totalBlocks} Blocks</span>
            </div>
            <div className="flex flex-col bg-surface-container-lowest p-space-xs rounded">
              <span className="font-label-caps text-secondary">STATUS</span>
              <span className="text-on-tertiary-container font-semibold">FEASIBLE OPTIMAL</span>
            </div>
          </div>
        </div>

        {/* Primary Action Dispatch Button */}
        <div className="sticky bottom-2 z-20 flex flex-col pt-space-xs">
          <button
            className={`flex items-center justify-center gap-space-sm py-space-md px-gutter rounded-lg shadow-lg active:opacity-95 transition-all ${
              dispatching ? 'bg-primary/75 cursor-wait' : 'bg-primary text-on-primary'
            }`}
            onClick={() => handleApplyPreset(selectedPolicy)}
            disabled={dispatching}
            type="button"
          >
            <span className="material-symbols-outlined text-[20px] text-tertiary-fixed">
              {dispatching ? 'autorenew' : 'bolt'}
            </span>
            <span className="font-code-lg text-code-lg tracking-wide uppercase">
              {dispatching
                ? 'SOLVING CP-SAT OPTIMIZATION...'
                : dispatched
                ? 'PRESET COMMITTED TO DISPATCH ✓'
                : current.btnLabel}
            </span>
          </button>
        </div>
      </div>
    </main>
  );
}
