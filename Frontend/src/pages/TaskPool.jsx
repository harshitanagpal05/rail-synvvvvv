import React, { useState, useEffect } from 'react';
import {
  getTasks, runNegotiation,
  criticalityLabel, deptLabel, formatDuration,
} from '../services/api';

export default function TaskPool() {
  const [toastMessage, setToastMessage] = useState(null);
  const [filterDept, setFilterDept] = useState('All');

  // Real data state
  const [tasks, setTasks] = useState([]);
  const [negotiation, setNegotiation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [negotiating, setNegotiating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [taskData, negData] = await Promise.all([
        getTasks().catch(() => []),
        runNegotiation().catch(() => null),
      ]);
      setTasks(taskData);
      setNegotiation(negData);
    } catch {} finally {
      setLoading(false);
    }
  };

  const handleReNegotiate = async () => {
    if (negotiating) return;
    setNegotiating(true);
    try {
      const result = await runNegotiation();
      setNegotiation(result);
      showToast(`Negotiation complete: ${result.total_tasks} tasks scored, ${result.inflated_count} inflated claims detected.`);
    } catch (err) {
      showToast('Negotiation failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setNegotiating(false);
    }
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4500);
  };

  // Merge tasks with negotiation scores
  const scoredTasks = negotiation?.scored_tasks || [];
  const getScoredData = (taskId) => scoredTasks.find(s => s.task_id === taskId);

  // Stats
  const totalTasks = tasks.length;
  const inflatedCount = negotiation?.inflated_count || 0;
  const consolidationGroups = negotiation?.consolidation_groups || 0;
  const approvedCount = scoredTasks.filter(s => !s.inflated_claim && s.weighted_priority >= 0.5).length;

  // Filtered tasks
  const filteredTasks = filterDept === 'All'
    ? tasks
    : filterDept === 'Critical'
      ? tasks.filter(t => t.claimed_criticality <= 2)
      : tasks.filter(t => t.department === filterDept);

  if (loading) {
    return (
      <main className="flex flex-col relative w-full">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-space-sm">
            <span className="material-symbols-outlined text-[32px] text-primary animate-spin">autorenew</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">Running Layer 2 negotiation engine...</span>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col relative w-full">
      <div className="flex flex-col w-full">
        {/* Toast */}
        {toastMessage && (
          <div className="mx-gutter mt-space-sm px-space-md py-space-sm rounded-lg bg-primary-container text-on-primary flex items-center justify-between shadow-md transition-all">
            <div className="flex items-center gap-space-sm">
              <span className="material-symbols-outlined text-tertiary-fixed text-[18px]">verified</span>
              <span className="font-code-sm text-code-sm">{toastMessage}</span>
            </div>
            <button className="text-on-primary-container hover:text-on-primary" onClick={() => setToastMessage(null)}>
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        )}

        {/* Operational Context Banner */}
        <div className="px-gutter pt-space-md pb-space-sm flex flex-col gap-space-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="font-label-caps text-label-caps bg-secondary-container text-on-secondary-fixed px-space-xs py-0.5 rounded">
                LAYER 2 NEGOTIATION
              </span>
              {negotiation && (
                <span className="font-label-caps text-label-caps bg-surface-container-highest text-on-surface-variant px-space-xs py-0.5 rounded">
                  RUN: {negotiation.negotiation_run_id}
                </span>
              )}
            </div>
            <div className="flex items-center gap-space-xs">
              <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim animate-pulse"></span>
              <span className="font-code-sm text-code-sm text-on-surface-variant font-medium">EVIDENCE AUDITOR</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">Maintenance Possession Negotiation</h1>
            <button
              onClick={handleReNegotiate}
              className="font-code-sm text-code-sm bg-primary text-on-primary px-space-md py-1 rounded flex items-center gap-space-xs"
              disabled={negotiating}
            >
              <span className={`material-symbols-outlined text-[14px] ${negotiating ? 'animate-spin' : ''}`}>
                {negotiating ? 'autorenew' : 'refresh'}
              </span>
              <span>{negotiating ? 'NEGOTIATING...' : 'RE-NEGOTIATE'}</span>
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="px-gutter py-space-xs">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-xs">
            <div className="bg-surface-container-lowest p-space-sm rounded-lg flex flex-col justify-between shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-label-caps text-label-caps text-on-surface-variant">TOTAL SUBMITTED</span>
                <span className="material-symbols-outlined text-on-surface-variant text-[16px]">format_list_bulleted</span>
              </div>
              <div className="flex items-baseline gap-space-xs mt-space-xs">
                <span className="font-headline-xl text-headline-xl text-primary font-bold">{totalTasks}</span>
                <span className="font-code-sm text-code-sm text-on-surface-variant">Demands</span>
              </div>
              <div className="w-full bg-surface-container h-1 rounded-full overflow-hidden mt-space-xs">
                <div className="bg-primary h-full w-full"></div>
              </div>
            </div>

            <div className="bg-surface-container-lowest p-space-sm rounded-lg flex flex-col justify-between shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-label-caps text-label-caps text-on-tertiary-container">APPROVED</span>
                <span className="material-symbols-outlined text-on-tertiary-container text-[16px]">check_circle</span>
              </div>
              <div className="flex items-baseline gap-space-xs mt-space-xs">
                <span className="font-headline-xl text-headline-xl text-on-tertiary-container font-bold">{approvedCount}</span>
                <span className="font-code-sm text-code-sm text-on-surface-variant">Scored high</span>
              </div>
              <div className="w-full bg-surface-container h-1 rounded-full overflow-hidden mt-space-xs">
                <div className="bg-tertiary-fixed-dim h-full" style={{ width: `${totalTasks > 0 ? (approvedCount / totalTasks * 100) : 0}%` }}></div>
              </div>
            </div>

            <div className="bg-surface-container-lowest p-space-sm rounded-lg flex flex-col justify-between shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-label-caps text-label-caps text-on-secondary-fixed-variant">SYNERGY GROUPS</span>
                <span className="material-symbols-outlined text-on-secondary-fixed-variant text-[16px]">merge_type</span>
              </div>
              <div className="flex items-baseline gap-space-xs mt-space-xs">
                <span className="font-headline-xl text-headline-xl text-on-secondary-fixed font-bold">{consolidationGroups}</span>
                <span className="font-code-sm text-code-sm text-on-surface-variant">Coordinated</span>
              </div>
              <div className="w-full bg-surface-container h-1 rounded-full overflow-hidden mt-space-xs">
                <div className="bg-secondary-fixed-dim h-full" style={{ width: `${totalTasks > 0 ? (consolidationGroups / totalTasks * 100) : 0}%` }}></div>
              </div>
            </div>

            <div className="bg-surface-container-lowest p-space-sm rounded-lg flex flex-col justify-between shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-label-caps text-label-caps text-error">INFLATED / AUDIT</span>
                <span className="material-symbols-outlined text-error text-[16px]">gavel</span>
              </div>
              <div className="flex items-baseline gap-space-xs mt-space-xs">
                <span className="font-headline-xl text-headline-xl text-error font-bold">{inflatedCount}</span>
                <span className="font-code-sm text-code-sm text-error">Flagged AI</span>
              </div>
              <div className="w-full bg-surface-container h-1 rounded-full overflow-hidden mt-space-xs">
                <div className="bg-error h-full" style={{ width: `${totalTasks > 0 ? (inflatedCount / totalTasks * 100) : 0}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Task List */}
        <div className="px-gutter pt-space-md pb-space-lg flex flex-col gap-space-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="font-headline-sm text-headline-sm text-on-surface">Department Demands Analysis</span>
              <span className="font-label-caps text-label-caps bg-surface-container-high text-on-surface-variant px-space-xs py-0.5 rounded">
                EVIDENCE AUDITED
              </span>
            </div>
            <div className="flex items-center gap-space-xs">
              {['All', 'Critical', 'TRACK', 'OHE', 'SIG'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilterDept(f)}
                  className={`font-code-sm text-code-sm px-space-sm py-1 rounded transition-colors ${
                    filterDept === f ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {filteredTasks.length === 0 ? (
            <div className="bg-surface-container-lowest rounded-xl p-space-md shadow-sm text-center text-on-surface-variant font-code-sm text-code-sm">
              No tasks found for this filter.
            </div>
          ) : (
            filteredTasks.map(task => {
              const scored = getScoredData(task.task_id);
              const isInflated = scored?.inflated_claim || false;
              const evidenceScore = scored?.evidence_score ?? null;
              const priority = scored?.weighted_priority ?? null;
              const critLabel = criticalityLabel(task.claimed_criticality);

              return (
                <div
                  key={task.task_id}
                  className={`bg-surface-container-lowest rounded-xl p-space-md shadow-sm flex flex-col gap-space-sm ${
                    isInflated ? 'ring-1 ring-error/20' : ''
                  }`}
                >
                  <div className="flex items-start justify-between flex-wrap gap-space-xs">
                    <div className="flex items-center gap-space-xs flex-wrap">
                      <span className="font-code-lg text-code-lg text-primary font-bold">{task.task_id}</span>
                      <span className="font-label-caps text-label-caps bg-surface-container-high text-on-surface px-space-xs py-0.5 rounded uppercase">
                        {deptLabel(task.department)}
                      </span>
                      <span className={`font-code-sm text-code-sm px-space-xs py-0.5 rounded font-semibold ${
                        task.claimed_criticality <= 2
                          ? 'bg-error-container text-on-error-container'
                          : 'bg-secondary-container text-on-secondary-fixed'
                      }`}>
                        {critLabel} (LVL {task.claimed_criticality})
                      </span>
                      {isInflated && (
                        <span className="font-code-sm text-code-sm bg-error text-on-error px-space-xs py-0.5 rounded font-bold flex items-center gap-0.5">
                          <span className="material-symbols-outlined text-[12px]">warning</span> INFLATED CLAIM
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-space-xs">
                      <span className="font-label-caps text-label-caps text-on-surface-variant">EVIDENCE</span>
                      <span className={`font-code-md text-code-md px-space-xs py-0.5 rounded font-bold ${
                        evidenceScore != null && evidenceScore >= 70
                          ? 'bg-tertiary-container text-tertiary-fixed'
                          : 'bg-error-container text-on-error-container'
                      }`}>
                        {evidenceScore != null ? `${(evidenceScore * 100).toFixed(0)} / 100` : '—'}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-space-xs">
                    <div className="flex items-center gap-space-xs text-on-surface font-headline-sm text-headline-sm">
                      <span className="material-symbols-outlined text-[18px] text-secondary">construction</span>
                      <span>{task.task_type}</span>
                    </div>
                    <div className="flex items-center gap-space-md text-on-surface-variant font-code-sm text-code-sm flex-wrap">
                      <span>Segment: {task.segment_id}</span>
                      <span>•</span>
                      <span>Min Duration: {formatDuration(task.min_duration_hrs)}</span>
                      {task.overdue && (
                        <>
                          <span>•</span>
                          <span className="text-error font-semibold">OVERDUE</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Negotiation Result */}
                  {scored && (
                    <div className={`rounded p-space-sm flex items-center justify-between flex-wrap gap-space-xs ${
                      isInflated ? 'bg-error-container/30' : 'bg-surface-container'
                    }`}>
                      <div className="flex items-center gap-space-xs">
                        <span className={`material-symbols-outlined text-[16px] ${isInflated ? 'text-error' : 'text-on-tertiary-container'}`}>
                          {isInflated ? 'gavel' : 'layers'}
                        </span>
                        <span className="font-body-md text-body-md text-on-surface">
                          <strong className="font-semibold">AI Assessment:</strong>{' '}
                          {isInflated
                            ? `Claim appears inflated. Evidence score: ${(evidenceScore * 100).toFixed(0)}/100. Recommend downgrade.`
                            : `Priority score: ${(priority * 100).toFixed(0)}/100. ${scored.consolidation_group ? `Consolidation group: ${scored.consolidation_group}` : 'Independent scheduling.'}`
                          }
                        </span>
                      </div>
                      <span className={`font-label-caps text-label-caps px-space-xs py-0.5 rounded ${
                        isInflated
                          ? 'bg-error-container text-on-error-container'
                          : 'bg-tertiary-container text-tertiary-fixed'
                      }`}>
                        {isInflated ? 'FLAGGED' : `PRIORITY: ${priority >= 0.7 ? 'HIGH' : priority >= 0.4 ? 'MEDIUM' : 'LOW'}`}
                      </span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </main>
  );
}
