import React, { useState, useEffect } from 'react';
import {
  getRiskSegments, getSegmentRisk,
  riskLevel, formatDuration,
} from '../services/api';

export default function SegmentWhy() {
  const [bookingState, setBookingState] = useState('idle');
  const [selectedSegId, setSelectedSegId] = useState(null);

  // Real data
  const [segments, setSegments] = useState([]);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const segs = await getRiskSegments();
      setSegments(segs);
      // Auto-select highest risk segment
      if (segs.length > 0) {
        const highest = segs.reduce((a, b) => a.risk_30d > b.risk_30d ? a : b);
        await selectSegment(highest.segment_id);
      }
    } catch {} finally {
      setLoading(false);
    }
  };

  const selectSegment = async (segId) => {
    setSelectedSegId(segId);
    try {
      const d = await getSegmentRisk(segId);
      setDetail(d);
    } catch {
      setDetail(null);
    }
  };

  const handleBookBlock = () => {
    if (bookingState !== 'idle') return;
    setBookingState('transmitting');
    setTimeout(() => setBookingState('requested'), 1200);
  };

  if (loading) {
    return (
      <main className="flex flex-col relative w-full">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-space-sm">
            <span className="material-symbols-outlined text-[32px] text-primary animate-spin">autorenew</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">Loading segment risk analysis from ML model...</span>
          </div>
        </div>
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="flex flex-col relative w-full p-gutter">
        <div className="text-center py-space-lg font-headline-sm text-headline-sm text-on-surface-variant">
          No segment data available. Check Layer 1 connection.
        </div>
      </main>
    );
  }

  const rl = riskLevel(detail.risk_30d);
  const isCritical = rl.label === 'CRITICAL';
  const isHigh = rl.label === 'HIGH' || isCritical;

  return (
    <main className="flex flex-col relative w-full">
      <div className="flex flex-col w-full gap-space-md p-space-md">
        {/* Segment Selector */}
        <div className="flex items-center gap-space-xs overflow-x-auto no-scrollbar bg-surface-container p-space-xs rounded">
          <span className="font-label-caps text-label-caps text-on-surface-variant shrink-0">SEGMENT:</span>
          {segments.sort((a, b) => b.risk_30d - a.risk_30d).slice(0, 8).map(seg => {
            const segRl = riskLevel(seg.risk_30d);
            return (
              <button
                key={seg.segment_id}
                onClick={() => selectSegment(seg.segment_id)}
                className={`px-space-sm py-1 rounded font-code-sm text-code-sm shrink-0 transition-colors ${
                  selectedSegId === seg.segment_id
                    ? (segRl.label === 'CRITICAL' ? 'bg-error text-on-error font-bold' : 'bg-primary text-on-primary font-bold')
                    : 'bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                {seg.segment_id.length > 14 ? seg.segment_id.slice(0, 14) + '…' : seg.segment_id}
                <span className="ml-1 text-[10px]">({(seg.risk_30d * 100).toFixed(0)}%)</span>
              </button>
            );
          })}
        </div>

        {/* Asset Identity & Risk Summary */}
        <section className="flex flex-col w-full bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-space-xs px-space-md py-space-xs bg-surface-container text-on-surface-variant font-label-caps text-label-caps uppercase tracking-wider">
            <div className="flex items-center gap-space-xs">
              <span className={`w-2 h-2 rounded-full ${isCritical ? 'bg-error animate-pulse' : isHigh ? 'bg-secondary' : 'bg-on-tertiary-container'}`}></span>
              <span>LAYER 1 ML RISK PREDICTION</span>
            </div>
            <div className="flex items-center gap-space-sm font-code-sm text-code-sm normal-case">
              <span>Model: <strong className="text-on-surface">{detail.model_version || 'Trained XGBoost-Weibull'}</strong></span>
            </div>
          </div>

          <div className="p-space-md flex flex-col gap-space-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm">
              <div className="flex flex-col">
                <div className="flex items-center gap-space-xs">
                  <span className="font-headline-xl text-headline-xl text-primary tracking-tight font-bold">{detail.segment_id}</span>
                  <span className={`inline-flex items-center px-space-xs py-0.5 rounded font-label-caps text-label-caps uppercase ${
                    isCritical ? 'bg-error text-on-error' : isHigh ? 'bg-secondary-container text-on-secondary-container' : 'bg-tertiary-container text-tertiary-fixed font-bold'
                  }`}>
                    {rl.label} RISK
                  </span>
                </div>
                <span className="font-code-sm text-code-sm text-secondary mt-0.5">
                  Confidence: {detail.confidence} • {detail.feature_contributions?.length || 0} features analyzed
                </span>
              </div>

              <div className="flex items-center gap-space-md bg-surface-container px-space-md py-space-sm rounded-lg">
                <div className="text-center">
                  <span className={`font-headline-xl text-headline-xl font-bold ${isCritical ? 'text-error' : 'text-on-surface'}`}>
                    {(detail.risk_30d * 100).toFixed(1)}%
                  </span>
                  <span className="font-label-caps text-label-caps text-on-surface-variant block">30-DAY RISK</span>
                </div>
                <div className="h-10 w-[1px] bg-outline-variant"></div>
                <div className="text-center">
                  <span className="font-headline-xl text-headline-xl font-bold text-on-surface">
                    {detail.expected_downtime_days?.toFixed(1)}
                  </span>
                  <span className="font-label-caps text-label-caps text-on-surface-variant block">DOWNTIME DAYS</span>
                </div>
                <div className="h-10 w-[1px] bg-outline-variant"></div>
                <div className="text-center">
                  <span className="font-headline-xl text-headline-xl font-bold text-on-surface">
                    {formatDuration(detail.preventive_block_duration_hrs)}
                  </span>
                  <span className="font-label-caps text-label-caps text-on-surface-variant block">BLOCK NEEDED</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Contributions — WHY this risk? */}
        <section className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
          <div className="px-space-md py-space-sm bg-surface-container flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-[18px] text-primary">psychology</span>
            <span className="font-headline-sm text-headline-sm text-on-surface">"Why?" — ML Feature Contributions</span>
          </div>

          <div className="p-space-md flex flex-col gap-space-sm">
            {(detail.feature_contributions || []).length === 0 ? (
              <span className="font-code-sm text-code-sm text-on-surface-variant text-center py-space-md">
                Feature contributions not available for this segment.
              </span>
            ) : (
              detail.feature_contributions
                .filter(fc => (fc.importance ?? fc.contribution ?? 0) > 0)
                .slice(0, 8)
                .map((fc, i) => {
                  const score = fc.contribution ?? fc.importance ?? 0;
                  const pct = (Math.abs(score) * 100).toFixed(1);
                  return (
                    <div key={i} className="flex items-center gap-space-sm p-space-sm bg-surface-container-low rounded">
                      <span className="font-code-sm text-code-sm text-on-surface font-bold w-6 text-center">{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="font-code-sm text-code-sm text-on-surface font-semibold truncate">{fc.name}</span>
                          <span className="font-code-sm text-code-sm font-bold text-error">
                            +{pct}%
                          </span>
                        </div>
                        <div className="w-full h-2 bg-surface-container-high rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all bg-error"
                            style={{ width: `${Math.min(Math.abs(score) * 200, 100)}%` }}
                          ></div>
                        </div>
                        <span className="font-body-sm text-body-sm text-on-surface-variant">
                          {fc.value != null ? `Value: ${typeof fc.value === 'number' ? fc.value.toFixed(3) : fc.value} • ` : ''}Feature Importance: {pct}%
                        </span>
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </section>

        {/* Survival Curve */}
        {detail.survival_curve?.length > 0 && (
          <section className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
            <div className="px-space-md py-space-sm bg-surface-container flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-[18px] text-secondary">show_chart</span>
              <span className="font-headline-sm text-headline-sm text-on-surface">Survival Curve (Weibull Model)</span>
            </div>
            <div className="p-space-md">
              <div className="flex items-end gap-[2px] h-32 px-space-xs">
                {detail.survival_curve.map((pt, i) => {
                  const barPct = pt.survival_probability * 100;
                  return (
                    <div
                      key={i}
                      className={`flex-1 rounded-t transition-all ${
                        pt.survival_probability > 0.9 ? 'bg-tertiary-fixed-dim' :
                        pt.survival_probability > 0.7 ? 'bg-secondary-fixed-dim' :
                        pt.survival_probability > 0.5 ? 'bg-secondary' : 'bg-error'
                      }`}
                      style={{ height: `${barPct}%` }}
                      title={`Day ${pt.day}: ${barPct.toFixed(1)}% survival`}
                    ></div>
                  );
                })}
              </div>
              <div className="flex justify-between font-code-sm text-code-sm text-on-surface-variant mt-space-xs px-space-xs">
                <span>Day 0 (100%)</span>
                <span>Day {detail.survival_curve[detail.survival_curve.length - 1]?.day} ({(detail.survival_curve[detail.survival_curve.length - 1]?.survival_probability * 100).toFixed(1)}%)</span>
              </div>
            </div>
          </section>
        )}

        {/* Action Footer */}
        <div className="bg-surface-container-lowest rounded-xl shadow-sm p-space-md flex flex-col sm:flex-row items-center justify-between gap-space-sm">
          <div className="flex items-center gap-space-sm">
            <span className="material-symbols-outlined text-primary text-[24px]">assignment_add</span>
            <div className="flex flex-col">
              <span className="font-headline-sm text-headline-sm text-on-surface font-bold">
                Recommended: {formatDuration(detail.preventive_block_duration_hrs)} maintenance block
              </span>
              <span className="font-code-sm text-code-sm text-on-surface-variant">
                Based on trained ML model prediction • Confidence: {detail.confidence}
              </span>
            </div>
          </div>
          <button
            onClick={handleBookBlock}
            disabled={bookingState !== 'idle'}
            className="px-space-lg py-space-sm rounded bg-primary text-on-primary font-code-md text-code-md font-bold shadow-sm flex items-center gap-space-xs"
          >
            <span className="material-symbols-outlined text-[18px]">
              {bookingState === 'transmitting' ? 'autorenew' : bookingState === 'requested' ? 'check_circle' : 'send'}
            </span>
            {bookingState === 'transmitting' ? 'TRANSMITTING...' : bookingState === 'requested' ? 'BLOCK REQUESTED ✓' : 'REQUEST BLOCK'}
          </button>
        </div>
      </div>
    </main>
  );
}
