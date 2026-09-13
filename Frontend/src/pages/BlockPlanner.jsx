import React, { useState, useEffect } from 'react';
import {
  getCurrentPlan, runOptimization,
  formatTime, formatDuration, deptLabel,
} from '../services/api';

export default function BlockPlanner() {
  const [deptFilter, setDeptFilter] = useState('ALL');
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);

  useEffect(() => {
    loadPlan();
  }, []);

  const loadPlan = async () => {
    setLoading(true);
    try {
      const data = await getCurrentPlan();
      setPlan(data);
    } catch {
      setPlan(null);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async (policy = 'balanced') => {
    if (optimizing) return;
    setOptimizing(true);
    try {
      await runOptimization(policy, 'both');
      await loadPlan();
    } catch (err) {
      alert('Optimization failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setOptimizing(false);
    }
  };

  const assignments = plan?.assignments || [];

  // Department breakdown
  const allDepts = [...new Set(assignments.map(a => a.department))];

  // Filter
  const filtered = deptFilter === 'ALL'
    ? assignments
    : assignments.filter(a => a.department === deptFilter);

  // Group by day (from block_start)
  const groupByDay = (items) => {
    const groups = {};
    items.forEach(a => {
      const day = new Date(a.block_start).toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short' });
      if (!groups[day]) groups[day] = [];
      groups[day].push(a);
    });
    return groups;
  };

  const dayGroups = groupByDay(filtered);
  const now = new Date();

  if (loading) {
    return (
      <main className="flex flex-col relative w-full">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-space-sm">
            <span className="material-symbols-outlined text-[32px] text-primary animate-spin">autorenew</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">Loading block plan from Layer 3...</span>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col relative w-full">
      <div className="flex flex-col w-full">
        {/* Operations Strip */}
        <section className="p-gutter bg-surface-container-low flex flex-col gap-space-sm shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary text-[18px]">calendar_today</span>
              <span className="font-headline-sm text-headline-sm text-primary">
                {now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', weekday: 'short' }).toUpperCase()}
              </span>
              {plan && (
                <span className="font-label-caps text-label-caps bg-primary text-on-primary px-space-xs py-0.5 rounded ml-space-xs">
                  {plan.plan_id}
                </span>
              )}
            </div>
            <div className="flex items-center gap-space-xs">
              {plan && (
                <span className="font-code-sm text-code-sm text-on-surface-variant bg-surface-container-highest px-space-sm py-0.5 rounded">
                  Policy: {plan.policy} • {plan.total_assignments} blocks
                </span>
              )}
            </div>
          </div>

          {/* Dept Filters */}
          <div className="flex items-center gap-space-xs overflow-x-auto no-scrollbar py-0.5">
            <button
              onClick={() => setDeptFilter('ALL')}
              className={`flex items-center gap-space-xs px-space-sm py-1 rounded font-code-sm text-code-sm shrink-0 transition-colors ${
                deptFilter === 'ALL' ? 'bg-primary text-on-primary shadow-sm' : 'bg-surface-container-highest text-on-surface-variant'
              }`}
            >
              DEPTS: ALL ({allDepts.length})
            </button>
            {allDepts.map(dept => (
              <button
                key={dept}
                onClick={() => setDeptFilter(dept)}
                className={`flex items-center gap-space-xs px-space-sm py-1 rounded font-code-sm text-code-sm shrink-0 transition-colors ${
                  deptFilter === dept ? 'bg-primary text-on-primary shadow-sm' : 'bg-surface-container-highest text-on-surface-variant'
                }`}
              >
                {dept}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-space-xs">
              <button
                onClick={() => handleOptimize('balanced')}
                disabled={optimizing}
                className="flex items-center gap-space-xs px-space-md py-1 rounded bg-primary text-on-primary font-code-sm text-code-sm font-bold shadow-sm"
              >
                <span className={`material-symbols-outlined text-[14px] ${optimizing ? 'animate-spin' : ''}`}>
                  {optimizing ? 'autorenew' : 'play_arrow'}
                </span>
                {optimizing ? 'OPTIMIZING...' : 'RE-OPTIMIZE'}
              </button>
            </div>
          </div>
        </section>

        {/* Block Schedule */}
        <div className="p-gutter flex flex-col gap-space-md">
          {!plan ? (
            <div className="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm text-center flex flex-col items-center gap-space-md">
              <span className="material-symbols-outlined text-[48px] text-on-surface-variant">event_busy</span>
              <div className="flex flex-col gap-space-xs">
                <span className="font-headline-sm text-headline-sm text-on-surface">No Active Block Plan</span>
                <span className="font-body-md text-body-md text-on-surface-variant">
                  Run the optimization engine to generate block assignments from Layer 3.
                </span>
              </div>
              <button
                onClick={() => handleOptimize('balanced')}
                disabled={optimizing}
                className="px-space-lg py-space-sm rounded bg-primary text-on-primary font-code-md text-code-md font-bold shadow-sm flex items-center gap-space-xs"
              >
                <span className="material-symbols-outlined text-[18px]">auto_fix_high</span>
                GENERATE BLOCK PLAN
              </button>
            </div>
          ) : (
            Object.entries(dayGroups).map(([day, dayAssignments]) => (
              <div key={day} className="flex flex-col gap-space-xs">
                <div className="flex items-center gap-space-xs">
                  <span className="font-headline-sm text-headline-sm text-primary">{day}</span>
                  <span className="font-label-caps text-label-caps bg-surface-container-high text-on-surface-variant px-space-xs py-0.5 rounded">
                    {dayAssignments.length} BLOCKS
                  </span>
                </div>

                {/* Block Cards */}
                {dayAssignments.map((a, i) => (
                  <div
                    key={a.task_id + i}
                    className="bg-surface-container-lowest rounded-lg p-space-md shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm"
                  >
                    <div className="flex items-start gap-space-sm min-w-0">
                      <div className={`w-1 h-12 rounded-full shrink-0 ${
                        a.risk_30d >= 0.7 ? 'bg-error' : a.risk_30d >= 0.4 ? 'bg-secondary' : 'bg-tertiary-fixed-dim'
                      }`}></div>
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <div className="flex items-center gap-space-xs flex-wrap">
                          <span className="font-code-lg text-code-lg font-bold text-primary">{a.task_id}</span>
                          <span className="font-label-caps text-label-caps bg-surface-container px-1 py-0.5 rounded text-on-surface font-semibold">
                            {a.department}
                          </span>
                          {a.consolidation_group && (
                            <span className="font-label-caps text-label-caps bg-secondary-container text-on-secondary-container px-1 py-0.5 rounded">
                              GROUP: {a.consolidation_group}
                            </span>
                          )}
                        </div>
                        <span className="font-code-sm text-code-sm text-on-surface-variant">
                          Segment: {a.segment_id} {a.reason ? `• ${a.reason}` : ''}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-space-md shrink-0">
                      <div className="text-right">
                        <span className="font-label-caps text-label-caps text-on-surface-variant block">WINDOW</span>
                        <span className="font-code-md text-code-md text-on-surface font-bold">
                          {formatTime(a.block_start)} - {formatTime(a.block_end)}
                        </span>
                      </div>
                      <div className="h-8 w-[1px] bg-outline-variant"></div>
                      <div className="text-right">
                        <span className="font-label-caps text-label-caps text-on-surface-variant block">DURATION</span>
                        <span className="font-code-md text-code-md text-on-surface font-bold">{formatDuration(a.duration_hrs)}</span>
                      </div>
                      <div className="h-8 w-[1px] bg-outline-variant"></div>
                      <div className="text-right">
                        <span className="font-label-caps text-label-caps text-on-surface-variant block">RISK</span>
                        <span className={`font-code-md text-code-md font-bold ${
                          a.risk_30d >= 0.7 ? 'text-error' : a.risk_30d >= 0.4 ? 'text-secondary' : 'text-on-tertiary-container'
                        }`}>
                          {a.risk_30d != null ? `${(a.risk_30d * 100).toFixed(0)}%` : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}

          {plan && filtered.length === 0 && (
            <div className="text-center py-space-md font-code-sm text-code-sm text-on-surface-variant">
              No blocks for department: {deptFilter}
            </div>
          )}
        </div>

        {/* Summary Footer */}
        {plan && (
          <div className="p-gutter bg-surface-container-lowest shadow-[0_-2px_10px_rgba(0,0,0,0.06)] sticky bottom-0 z-40">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">summarize</span>
                <div className="flex flex-col">
                  <span className="font-headline-sm text-headline-sm text-on-surface font-bold">
                    {plan.total_assignments} Total Blocks Scheduled
                  </span>
                  <span className="font-code-sm text-code-sm text-on-surface-variant">
                    Policy: {plan.policy} • Robustness: {plan.robustness_score ? `${(plan.robustness_score * 100).toFixed(0)}%` : '—'}
                    {plan.execution_time_ms && ` • Solved in ${plan.execution_time_ms}ms`}
                  </span>
                </div>
              </div>
              <button onClick={loadPlan} className="font-code-sm text-code-sm text-primary font-bold hover:underline flex items-center gap-0.5">
                <span className="material-symbols-outlined text-[14px]">refresh</span> REFRESH
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
