import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  getRiskSegments, getSegmentRisk, getCurrentPlan,
  riskLevel, formatTime, formatDuration,
} from '../services/api';

export default function DigitalTwin() {
  const [twinMode, setTwinMode] = useState('realtime');
  const [activeLayers, setActiveLayers] = useState(['P-Way Track']);
  const [selectedSegId, setSelectedSegId] = useState(null);

  // Real data
  const [segments, setSegments] = useState([]);
  const [segmentDetail, setSegmentDetail] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [segData, planData] = await Promise.all([
        getRiskSegments().catch(() => []),
        getCurrentPlan().catch(() => null),
      ]);
      setSegments(segData);
      setPlan(planData);
      // Auto-select the highest risk segment
      if (segData.length > 0) {
        const highest = segData.reduce((a, b) => a.risk_30d > b.risk_30d ? a : b);
        selectSegment(highest.segment_id);
      }
    } catch {} finally {
      setLoading(false);
    }
  };

  const selectSegment = async (segId) => {
    setSelectedSegId(segId);
    setDetailLoading(true);
    try {
      const detail = await getSegmentRisk(segId);
      setSegmentDetail(detail);
    } catch {
      setSegmentDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const toggleLayer = (layerName) => {
    setActiveLayers((prev) =>
      prev.includes(layerName) ? prev.filter((l) => l !== layerName) : [...prev, layerName]
    );
  };

  const triggerBlockAssign = () => {
    alert(`Block Assignment Window Initialized for ${selectedSegId}. Dispatching to optimization engine.`);
  };

  const exportTelemetry = () => {
    alert('Exporting Digital Twin Risk & Telemetry Data (JSON format)...');
  };

  // Sort segments by risk descending
  const sortedSegments = [...segments].sort((a, b) => b.risk_30d - a.risk_30d);
  const criticalSegs = sortedSegments.filter(s => s.risk_30d >= 0.7);
  const highSegs = sortedSegments.filter(s => s.risk_30d >= 0.4 && s.risk_30d < 0.7);
  const normalSegs = sortedSegments.filter(s => s.risk_30d < 0.4);

  // Get assignments for selected segment
  const segAssignments = plan?.assignments?.filter(a => a.segment_id === selectedSegId) || [];
  const rl = segmentDetail ? riskLevel(segmentDetail.risk_30d) : null;
  const isCritical = rl?.label === 'CRITICAL';

  if (loading) {
    return (
      <main className="flex flex-col relative w-full">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-space-sm">
            <span className="material-symbols-outlined text-[32px] text-primary animate-spin">autorenew</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">Loading Digital Twin from Layer 1 ML predictions...</span>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col relative w-full">
      <div className="flex flex-col w-full gap-space-md p-gutter">
        {/* TOP BAR */}
        <div className="flex flex-col gap-space-sm bg-surface-container-lowest p-space-md rounded-lg shadow-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-xs">
            <div className="flex items-center gap-space-xs min-w-0">
              <span className="material-symbols-outlined text-[20px] text-primary shrink-0" style={{ fontVariationSettings: "'FILL' 1" }}>alt_route</span>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-space-xs">
                  <span className="font-headline-sm text-headline-sm text-on-surface truncate">
                    Digital Twin — ML Risk Predictions (Layer 1)
                  </span>
                  <span className="font-label-caps text-label-caps bg-secondary-container text-on-secondary-container px-1 py-0.5 rounded uppercase">
                    {segments.length} SEGMENTS
                  </span>
                </div>
                <span className="font-code-sm text-code-sm text-secondary">
                  {criticalSegs.length} Critical • {highSegs.length} High • {normalSegs.length} Normal
                </span>
              </div>
            </div>

            <div className="flex items-center p-0.5 bg-surface-container-high rounded-lg w-full sm:w-auto self-stretch sm:self-auto">
              <button
                className={`flex-1 sm:flex-initial flex items-center justify-center gap-space-xs px-space-md py-1 rounded transition-all font-code-sm text-code-sm ${
                  twinMode === 'realtime' ? 'bg-surface-container-lowest text-primary shadow-sm font-semibold' : 'text-secondary'
                }`}
                onClick={() => setTwinMode('realtime')}
              >
                <span className="w-2 h-2 rounded-full bg-on-tertiary-container animate-pulse"></span>
                <span>RISK VIEW</span>
              </button>
              <button
                className={`flex-1 sm:flex-initial flex items-center justify-center gap-space-xs px-space-md py-1 rounded transition-all font-code-sm text-code-sm ${
                  twinMode === 'planned' ? 'bg-surface-container-lowest text-primary shadow-sm font-semibold' : 'text-secondary'
                }`}
                onClick={() => setTwinMode('planned')}
              >
                <span className="material-symbols-outlined text-[14px]">event_repeat</span>
                <span>PLAN VIEW</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-space-xs overflow-x-auto no-scrollbar pt-space-xs">
            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase shrink-0 mr-1">LAYER:</span>
            {[
              { id: 'P-Way Track', icon: 'linear_scale' },
              { id: 'OHE Traction', icon: 'electric_bolt' },
              { id: 'S&T Signalling', icon: 'traffic' },
            ].map((layer) => {
              const active = activeLayers.includes(layer.id);
              return (
                <button
                  key={layer.id}
                  onClick={() => toggleLayer(layer.id)}
                  className={`flex items-center gap-1 px-space-md py-1 rounded font-code-sm text-code-sm transition-colors ${
                    active ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant'
                  }`}
                >
                  <span className="material-symbols-outlined text-[14px]">{layer.icon}</span>
                  <span>{layer.id}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* SEGMENT RISK GRID */}
        <div className="flex flex-col bg-surface-container-lowest rounded-lg shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-space-md py-space-sm bg-surface-container">
            <div className="flex items-center gap-space-xs min-w-0">
              <span className="material-symbols-outlined text-[16px] text-primary">hub</span>
              <span className="font-headline-sm text-headline-sm text-on-surface truncate">Segment Risk Map</span>
            </div>
            <span className="font-code-sm text-code-sm text-secondary">Click segment to inspect</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-space-xs p-space-md">
            {sortedSegments.map(seg => {
              const segRl = riskLevel(seg.risk_30d);
              const isSelected = selectedSegId === seg.segment_id;
              const segCrit = segRl.label === 'CRITICAL';
              return (
                <div
                  key={seg.segment_id}
                  onClick={() => selectSegment(seg.segment_id)}
                  className={`cursor-pointer p-space-sm rounded-lg flex flex-col gap-1 transition-all ${
                    segCrit ? 'bg-error-container/40' : 'bg-surface-container-low'
                  } ${isSelected ? 'ring-2 ring-primary shadow-md scale-[1.02]' : 'hover:shadow-sm'}`}
                >
                  <div className="flex items-center gap-1">
                    <span className={`w-2.5 h-2.5 rounded-full ${
                      segCrit ? 'bg-error animate-pulse' : segRl.label === 'HIGH' ? 'bg-secondary' : 'bg-tertiary-container'
                    }`}></span>
                    <span className={`font-code-sm text-code-sm font-bold ${segCrit ? 'text-error' : 'text-on-surface'}`}>
                      {seg.segment_id.length > 12 ? seg.segment_id.slice(0, 12) + '…' : seg.segment_id}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={`font-label-caps text-label-caps font-bold ${
                      segCrit ? 'text-error' : segRl.label === 'HIGH' ? 'text-on-secondary-fixed-variant' : 'text-on-tertiary-container'
                    }`}>
                      {(seg.risk_30d * 100).toFixed(1)}%
                    </span>
                    <span className={`font-label-caps text-label-caps px-1 py-0.5 rounded text-[9px] ${
                      segCrit ? 'bg-error text-on-error' : segRl.label === 'HIGH' ? 'bg-secondary-container text-on-secondary-container' : 'bg-tertiary-container text-tertiary-fixed'
                    }`}>
                      {segRl.label}
                    </span>
                  </div>
                  <span className="font-body-sm text-body-sm text-on-surface-variant truncate text-[10px]">
                    ↓ {seg.expected_downtime_days?.toFixed(1)}d • {formatDuration(seg.preventive_block_duration_hrs)}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center justify-between gap-space-xs px-space-md py-space-xs bg-surface-container-high text-on-surface-variant font-code-sm text-code-sm">
            <div className="flex items-center gap-space-md">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-on-tertiary-container"></span> Low Risk</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-secondary"></span> High Risk</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-error"></span> Critical</span>
            </div>
            <span className="font-label-caps text-label-caps uppercase text-secondary">DATA FROM TRAINED ML MODEL</span>
          </div>
        </div>

        {/* INSPECTOR PANEL */}
        {segmentDetail && (
          <div className="flex flex-col bg-surface-container-lowest rounded-lg shadow-sm overflow-hidden transition-all duration-200">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-xs p-space-md bg-surface-container">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className={`w-9 h-9 rounded flex items-center justify-center shrink-0 ${
                  isCritical ? 'bg-error-container text-error' : 'bg-primary-container text-primary-fixed'
                }`}>
                  <span className="material-symbols-outlined text-[22px]">troubleshoot</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-space-xs">
                    <span className="font-headline-md text-headline-md text-on-surface truncate">{segmentDetail.segment_id}</span>
                    <span className={`font-label-caps text-label-caps px-1.5 py-0.5 rounded uppercase font-bold ${
                      isCritical ? 'bg-error text-on-error' : 'bg-primary text-on-primary'
                    }`}>
                      {rl.label} RISK
                    </span>
                  </div>
                  <span className="font-code-sm text-code-sm text-secondary truncate">
                    Model: {segmentDetail.model_version || 'Layer 1 ML'} • Confidence: {segmentDetail.confidence}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0">
                <span className={`font-code-sm text-code-sm font-bold ${isCritical ? 'text-error' : 'text-on-surface'}`}>
                  30d Risk: {(segmentDetail.risk_30d * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md p-space-md bg-surface-container-low">
              {/* Risk Metrics */}
              <div className="flex flex-col gap-space-sm bg-surface-container-lowest p-space-md rounded shadow-sm">
                <div className="flex items-center gap-space-xs pb-1">
                  <span className={`w-2 h-2 rounded-full ${isCritical ? 'bg-error animate-ping' : 'bg-on-tertiary-container'}`}></span>
                  <span className={`font-label-caps text-label-caps uppercase font-bold ${isCritical ? 'text-error' : 'text-secondary'}`}>
                    ML RISK PREDICTION
                  </span>
                </div>
                <div className="flex flex-col gap-space-xs">
                  <div className="flex items-center justify-between p-space-xs bg-surface-container rounded">
                    <span className="font-body-sm text-body-sm text-on-surface-variant">30-Day Failure Risk:</span>
                    <span className={`font-code-md text-code-md font-bold ${isCritical ? 'text-error' : 'text-on-surface'}`}>
                      {(segmentDetail.risk_30d * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-space-xs bg-surface-container rounded">
                    <span className="font-body-sm text-body-sm text-on-surface-variant">Expected Downtime:</span>
                    <span className="font-code-md text-code-md font-bold text-on-surface">
                      {segmentDetail.expected_downtime_days?.toFixed(1)} days
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-space-xs bg-surface-container rounded">
                    <span className="font-body-sm text-body-sm text-on-surface-variant">Preventive Block Duration:</span>
                    <span className="font-code-md text-code-md text-on-surface font-semibold">
                      {formatDuration(segmentDetail.preventive_block_duration_hrs)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-space-xs bg-surface-container rounded">
                    <span className="font-body-sm text-body-sm text-on-surface-variant">Model Confidence:</span>
                    <span className="font-code-md text-code-md text-on-tertiary-container font-semibold">
                      {segmentDetail.confidence?.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Feature Contributions */}
              <div className="flex flex-col gap-space-sm bg-surface-container-lowest p-space-md rounded shadow-sm">
                <div className="flex items-center gap-space-xs pb-1">
                  <span className="material-symbols-outlined text-[16px] text-on-tertiary-container">analytics</span>
                  <span className="font-label-caps text-label-caps text-on-tertiary-container uppercase font-bold">
                    TOP FEATURE CONTRIBUTIONS
                  </span>
                </div>
                <div className="flex flex-col gap-space-xs">
                  {(segmentDetail.feature_contributions || []).slice(0, 5).map((fc, i) => (
                    <div key={i} className="flex items-center justify-between p-space-xs bg-surface-container rounded">
                      <span className="font-body-sm text-body-sm text-on-surface-variant truncate">{fc.name}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-surface-container-high rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${fc.contribution > 0 ? 'bg-error' : 'bg-on-tertiary-container'}`}
                            style={{ width: `${Math.min(Math.abs(fc.contribution) * 100, 100)}%` }}
                          ></div>
                        </div>
                        <span className={`font-code-sm text-code-sm font-bold ${fc.contribution > 0 ? 'text-error' : 'text-on-tertiary-container'}`}>
                          {fc.contribution > 0 ? '+' : ''}{(fc.contribution * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
                  {(!segmentDetail.feature_contributions || segmentDetail.feature_contributions.length === 0) && (
                    <span className="font-code-sm text-code-sm text-on-surface-variant p-space-xs">
                      Feature contributions not available for this segment.
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Survival Curve Preview */}
            {segmentDetail.survival_curve?.length > 0 && (
              <div className="px-space-md py-space-sm bg-surface-container-lowest">
                <div className="flex items-center gap-space-xs mb-space-xs">
                  <span className="font-label-caps text-label-caps text-secondary uppercase">SURVIVAL CURVE (30-DAY)</span>
                </div>
                <div className="flex items-end gap-0.5 h-12">
                  {segmentDetail.survival_curve.map((pt, i) => (
                    <div
                      key={i}
                      className={`flex-1 rounded-t ${pt.survival_probability > 0.8 ? 'bg-tertiary-fixed-dim' : pt.survival_probability > 0.5 ? 'bg-secondary-fixed-dim' : 'bg-error'}`}
                      style={{ height: `${pt.survival_probability * 100}%` }}
                      title={`Day ${pt.day}: ${(pt.survival_probability * 100).toFixed(1)}%`}
                    ></div>
                  ))}
                </div>
                <div className="flex justify-between font-code-sm text-code-sm text-on-surface-variant mt-0.5">
                  <span>Day 0</span>
                  <span>Day {segmentDetail.survival_curve[segmentDetail.survival_curve.length - 1]?.day}</span>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-space-md p-space-md bg-surface-container-lowest">
              <div className="flex items-center gap-space-sm w-full sm:w-auto">
                <div className="flex flex-col">
                  <span className="font-label-caps text-label-caps text-secondary uppercase">PLANNED BLOCKS</span>
                  <span className="font-code-sm text-code-sm font-bold text-on-surface">
                    {segAssignments.length} assignment{segAssignments.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-space-sm w-full sm:w-auto justify-end">
                <Link
                  to="/segment-why"
                  className="flex items-center gap-1.5 px-space-md py-1.5 bg-surface-container-high text-primary rounded font-code-sm text-code-sm font-semibold hover:bg-secondary-container transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">psychology</span>
                  <span>Open Segment 'Why?'</span>
                </Link>
                <button
                  onClick={triggerBlockAssign}
                  className="flex items-center gap-1.5 px-space-md py-1.5 bg-primary text-on-primary rounded font-code-sm text-code-sm font-semibold shadow-sm hover:opacity-90"
                >
                  <span className="material-symbols-outlined text-[16px]">assignment_add</span>
                  <span>Assign Block Window</span>
                </button>
                <button
                  onClick={exportTelemetry}
                  className="flex items-center gap-1 px-space-sm py-1.5 bg-surface-container text-on-surface-variant rounded font-code-sm text-code-sm hover:bg-surface-container-high"
                >
                  <span className="material-symbols-outlined text-[16px]">file_download</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {detailLoading && (
          <div className="flex items-center justify-center py-space-md">
            <span className="material-symbols-outlined text-[24px] text-primary animate-spin">autorenew</span>
            <span className="ml-2 font-code-sm text-code-sm text-on-surface-variant">Loading segment detail...</span>
          </div>
        )}
      </div>
    </main>
  );
}
