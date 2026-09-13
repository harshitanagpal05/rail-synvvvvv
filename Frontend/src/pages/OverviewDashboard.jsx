import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  getHealth, getRiskSegments, getCurrentPlan, getTasks, runOptimization,
  getRealtimeStatus, getNetworkMap,
  riskLevel, formatTime, deptLabel, formatDuration,
} from '../services/api';
import NetworkMap from '../components/NetworkMap';
import GeoRailMap from '../components/GeoRailMap';
import SimulationBar from '../components/SimulationBar';

export default function OverviewDashboard() {
  const [optimizingState, setOptimizingState] = useState('idle');
  const [activeFilter, setActiveFilter] = useState('ALL DEPTS');
  const [selectedNode, setSelectedNode] = useState(null);
  const [mapViewMode, setMapViewMode] = useState('geo'); // 'geo' or 'schematic'

  // Real data state
  const [health, setHealth] = useState(null);
  const [risks, setRisks] = useState([]);
  const [plan, setPlan] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [realtime, setRealtime] = useState(null);
  const [network, setNetwork] = useState(null);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadRealtime, 5000); // Super fast polling for "Live" loop effect
    return () => clearInterval(interval);
  }, []);

  const loadRealtime = async () => {
    try {
      const rtData = await getRealtimeStatus();
      setRealtime(rtData);
      const nwData = await getNetworkMap();
      setNetwork(nwData);
    } catch (e) {
      console.warn("Could not fetch realtime status");
    }
  };

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, riskData, taskData, rtData, nwData] = await Promise.all([
        getHealth().catch(() => null),
        getRiskSegments().catch(() => []),
        getTasks().catch(() => []),
        getRealtimeStatus().catch(() => null),
        getNetworkMap().catch(() => null),
      ]);
      let planData = null;
      try { planData = await getCurrentPlan(); } catch {}

      setHealth(healthData);
      setRisks(riskData);
      setTasks(taskData);
      setPlan(planData);
      setRealtime(rtData);
      setNetwork(nwData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const triggerOptimization = async () => {
    if (optimizingState !== 'idle') return;
    setOptimizingState('solving');
    try {
      const result = await runOptimization('balanced', 'both');
      setOptimizingState('optimized');
      try { 
        const newPlan = await getCurrentPlan(); setPlan(newPlan);
        const nwData = await getNetworkMap(); setNetwork(nwData);
      } catch {}
      setTimeout(() => setOptimizingState('idle'), 2500);
    } catch (err) {
      setOptimizingState('idle');
      alert('Optimization failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const inspectNode = (stationCode) => {
    setSelectedNode(stationCode);
  };

  // Computed KPIs from real data
  const highRiskSegments = risks.filter(r => r.risk_30d >= 0.4);
  const criticalSegments = risks.filter(r => r.risk_30d >= 0.7);
  const assignments = plan?.assignments || [];
  const todayBlocks = assignments.length;
  const avgRisk = risks.length > 0 ? (risks.reduce((s, r) => s + (1 - r.risk_30d), 0) / risks.length * 100).toFixed(1) : '—';

  // Department breakdown from assignments
  const deptCounts = {};
  assignments.forEach(a => { deptCounts[a.department] = (deptCounts[a.department] || 0) + 1; });

  const filteredAssignments = activeFilter === 'CRITICAL ONLY'
    ? assignments.filter(a => a.priority === 'CRITICAL')
    : activeFilter === 'ALL DEPTS'
      ? assignments
      : assignments.filter(a => a.department === activeFilter);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <span className="material-symbols-outlined text-4xl animate-spin text-primary">sync</span>
          <p className="mt-4 text-on-surface-variant font-medium">Booting Command Center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-6 max-w-[1600px] mx-auto w-full fade-in pb-12">
      
      {/* Top Ministry of Railways Command Banner */}
      <div className="bg-gradient-to-r from-[#070d1a] via-[#0f172a] to-[#070d1a] border border-cyan-500/30 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-2xl relative overflow-hidden">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-primary/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-black text-xl shadow-inner font-serif">
            IR
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-bold tracking-widest text-amber-400 uppercase">
                Government of India · Ministry of Railways (CRIS / RDSO)
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold">
                RESTRICTED COCC
              </span>
            </div>
            <h1 className="text-xl md:text-2xl font-black text-white tracking-tight flex items-center gap-2 mt-0.5">
              RailSync Centralized Operations Control Centre
            </h1>
            <p className="text-xs text-slate-400 font-mono">
              National Real-Time Asset Health, Live Weather Calibration & Autonomous Dynamic Block Allocation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/digital-twin"
            className="px-3.5 py-2 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 text-xs font-mono font-bold flex items-center gap-1.5 transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-sm">hub</span>
            Asset Digital Twin
          </Link>
          <Link
            to="/whatif"
            className="px-3.5 py-2 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/40 text-purple-400 text-xs font-mono font-bold flex items-center gap-1.5 transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-sm">science</span>
            What-If Simulator
          </Link>
        </div>
      </div>
      
      {/* Live Operations Bar */}
      {realtime && (
        <div className="bg-surface-container-high rounded-xl p-3 flex items-center justify-between border border-primary/20 shadow-lg shadow-primary/5">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 bg-error/10 px-3 py-1.5 rounded-lg border border-error/20">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-error opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-error"></span>
              </span>
              <span className="font-bold text-sm tracking-widest text-error">LIVE</span>
            </div>
            
            <div className="flex items-center gap-2 text-sm">
              <span className="material-symbols-outlined text-[18px] text-on-surface-variant">schedule</span>
              <span className="font-bold tracking-wider text-on-surface">{new Date(realtime.timestamp_ist).toLocaleTimeString('en-IN', {hour: '2-digit', minute:'2-digit', second:'2-digit', hour12: false})} IST</span>
            </div>
            
            <div className="h-4 w-[1px] bg-outline-variant"></div>
            
            <div className="flex items-center gap-2 text-sm">
              <span className="material-symbols-outlined text-[18px] text-primary">rainy</span>
              <span className="font-medium text-on-surface">Monsoon: {realtime.monsoon_status.active ? 'Active' : 'Inactive'}</span>
            </div>

            <div className="h-4 w-[1px] bg-outline-variant"></div>

            <div className="flex items-center gap-2 text-sm">
              <span className="material-symbols-outlined text-[18px] text-tertiary">train</span>
              <span className="font-medium text-on-surface">{realtime.active_trains.count} Trains Active</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-sm bg-surface px-4 py-2 rounded-lg border border-outline-variant/30">
            <span className="material-symbols-outlined text-[18px] text-secondary animate-pulse">handyman</span>
            <span className="text-on-surface-variant font-medium">Current Block:</span>
            <span className="font-bold text-on-surface">{realtime.current_block_window.window}</span>
          </div>
        </div>
      )}

      {/* SIH Hackathon Emergency Simulation Bar */}
      <SimulationBar onIncidentTriggered={() => { loadRealtime(); loadDashboardData(); }} />

      {/* Map View Mode Switcher */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-on-surface-variant uppercase tracking-wider">
            Display Mode:
          </span>
          <div className="flex bg-surface-container rounded-xl p-1 border border-outline-variant/40">
            <button
              onClick={() => setMapViewMode('geo')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                mapViewMode === 'geo'
                  ? 'bg-primary text-on-primary shadow-md shadow-primary/20'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-sm">map</span>
              India Geographic GIS
            </button>
            <button
              onClick={() => setMapViewMode('schematic')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                mapViewMode === 'schematic'
                  ? 'bg-primary text-on-primary shadow-md shadow-primary/20'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-sm">schema</span>
              Corridor Schematics
            </button>
          </div>
        </div>

        <div className="text-xs font-mono text-on-surface-variant hidden md:block">
          All 6 Golden Quadrilateral & Diagonal Corridors · 120 Track Segments Active
        </div>
      </div>

      {/* Centerpiece Map View */}
      {mapViewMode === 'geo' ? (
        <GeoRailMap networkData={network} />
      ) : (
        <NetworkMap networkData={network} />
      )}

      {/* Secondary Data layer */}
      <div className="grid grid-cols-12 gap-6 h-[400px]">
        {/* Risk & Safety */}
        <div className="col-span-4 bg-surface-container-low rounded-2xl p-6 border border-outline-variant/30 flex flex-col">
          <h2 className="text-lg font-semibold text-on-surface flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-error">warning</span>
            Risk & Safety
          </h2>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-surface-container rounded-xl p-4 border border-outline-variant/30">
              <div className="text-3xl font-bold text-on-surface">{highRiskSegments.length}</div>
              <div className="text-sm font-medium text-on-surface-variant">High Risk Assets</div>
            </div>
            <div className="bg-error/10 rounded-xl p-4 border border-error/20">
              <div className="text-3xl font-bold text-error">{criticalSegments.length}</div>
              <div className="text-sm font-medium text-error">Critical Assets</div>
            </div>
          </div>

          <h3 className="text-sm font-bold text-on-surface-variant uppercase tracking-wider mb-3">Top Critical Segments</h3>
          <div className="flex flex-col gap-2 overflow-y-auto pr-2 custom-scrollbar">
            {criticalSegments.slice(0, 4).map(s => (
              <div key={s.segment_id} className="flex justify-between items-center p-3 bg-surface-container rounded-lg border border-outline-variant/20 hover:border-error/30 transition-colors">
                <div>
                  <div className="font-medium text-on-surface text-sm">{s.division} {s.asset_type}</div>
                  <div className="text-xs text-on-surface-variant">{s.segment_id}</div>
                </div>
                <div className="flex items-center gap-2 bg-error/10 px-2 py-1 rounded text-error font-bold text-sm border border-error/20">
                  {Math.round(s.risk_30d * 100)}%
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CP-SAT Assignments */}
        <div className="col-span-8 bg-surface-container-low rounded-2xl p-6 border border-outline-variant/30 flex flex-col">
                    <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">auto_fix_high</span>
              CP-SAT Maintenance Plan
            </h2>
            
            <button 
              onClick={triggerOptimization}
              disabled={optimizingState !== 'idle'}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium text-sm transition-all ${
                optimizingState === 'idle' 
                  ? 'bg-primary text-on-primary hover:bg-primary-container hover:text-on-primary-container shadow-lg shadow-primary/20' 
                  : optimizingState === 'solving' 
                  ? 'bg-surface-variant text-on-surface-variant cursor-wait' 
                  : 'bg-primary text-on-primary'
              }`}
            >
              {optimizingState === 'idle' && <><span className="material-symbols-outlined text-[18px]">memory</span> Reroute Traffic & Plan Blocks</>}
              {optimizingState === 'solving' && <><span className="material-symbols-outlined text-[18px] animate-spin">sync</span> Running CP-SAT Solver...</>}
              {optimizingState === 'optimized' && <><span className="material-symbols-outlined text-[18px]">check_circle</span> Plan Locked</>}
            </button>
          </div>

          <div className="flex gap-2 mb-4 overflow-x-auto pb-2 custom-scrollbar">
            {['ALL DEPTS', 'CRITICAL ONLY', 'TRACK', 'OHE', 'SIG', 'TELE', 'BRIDGE'].map(f => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${
                  activeFilter === f 
                    ? f === 'CRITICAL ONLY' ? 'bg-error text-on-error' : 'bg-secondary text-on-secondary'
                    : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-highest border border-outline-variant/30'
                }`}
              >
                {f} {f !== 'ALL DEPTS' && f !== 'CRITICAL ONLY' && `(${deptCounts[f] || 0})`}
              </button>
            ))}
          </div>

          <div className="bg-surface rounded-xl border border-outline-variant/30 flex-1 overflow-hidden flex flex-col">
            <div className="grid grid-cols-12 gap-4 p-3 border-b border-outline-variant/30 bg-surface-container-lowest text-xs font-bold text-on-surface-variant uppercase tracking-wider">
              <div className="col-span-2">Task ID</div>
              <div className="col-span-2">Location</div>
              <div className="col-span-3">Department</div>
              <div className="col-span-4">Scheduled Block</div>
              <div className="col-span-1 text-center">Dur.</div>
            </div>
            
            <div className="overflow-y-auto flex-1 custom-scrollbar">
              {filteredAssignments.length === 0 ? (
                <div className="p-8 text-center text-on-surface-variant italic flex flex-col items-center justify-center h-full">
                  <span className="material-symbols-outlined text-4xl mb-2 opacity-50">task</span>
                  No assignments in current plan. Run optimizer.
                </div>
              ) : (
                filteredAssignments.map((a, i) => (
                  <div key={i} className="grid grid-cols-12 gap-4 p-3 border-b border-outline-variant/10 items-center text-sm hover:bg-surface-container-lowest transition-colors">
                    <div className="col-span-2 font-mono text-xs text-on-surface-variant">{a.task_id}</div>
                    <div className="col-span-2 font-medium text-on-surface">{a.segment_id}</div>
                    <div className="col-span-3">
                      <span className="px-2 py-1 rounded bg-surface-variant text-on-surface-variant text-xs font-bold">
                        {deptLabel(a.department)}
                      </span>
                    </div>
                    <div className="col-span-4 flex items-center gap-2">
                      <span className="material-symbols-outlined text-[16px] text-primary">event_available</span>
                      <span className="font-medium text-on-surface">
                        {new Date(a.block_start).toLocaleDateString('en-IN', {month:'short', day:'numeric'})}
                        <span className="mx-1 text-on-surface-variant">|</span>
                        {formatTime(a.block_start)} - {formatTime(a.block_end)}
                      </span>
                    </div>
                    <div className="col-span-1 text-center font-bold text-on-surface-variant">
                      {a.duration_hrs}h
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

