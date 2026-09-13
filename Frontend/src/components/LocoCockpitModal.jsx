import React, { useState, useEffect } from 'react';
import { playAlarmSound } from '../utils/audio';

export default function LocoCockpitModal({ train, onClose }) {
  const [speed, setSpeed] = useState(126);
  const [emergencyBrake, setEmergencyBrake] = useState(false);
  const [targetDistance, setTargetDistance] = useState(3850); // meters to next signal

  useEffect(() => {
    if (emergencyBrake) {
      const interval = setInterval(() => {
        setSpeed((prev) => {
          if (prev <= 0) {
            clearInterval(interval);
            return 0;
          }
          return Math.max(0, prev - 14); // rapid deceleration
        });
      }, 300);
      return () => clearInterval(interval);
    } else {
      // Natural speed flutter (125 - 131 km/h)
      const interval = setInterval(() => {
        setSpeed(125 + Math.floor(Math.random() * 6));
        setTargetDistance((prev) => (prev > 200 ? prev - 35 : 4200));
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [emergencyBrake]);

  if (!train) return null;

  const handleBrakeTest = () => {
    playAlarmSound('alert');
    setEmergencyBrake(true);
  };

  const handleResetBrake = () => {
    playAlarmSound('click');
    setEmergencyBrake(false);
    setSpeed(128);
  };

  // Speedometer needle rotation (-120deg at 0 to +120deg at 160)
  const needleRotation = -120 + (speed / 160) * 240;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl bg-[#090d16] border border-cyan-500/40 rounded-3xl p-6 shadow-[0_0_50px_rgba(6,182,212,0.15)] overflow-hidden text-slate-100 flex flex-col gap-6">
        {/* Glow ambient */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Cockpit Top Header */}
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4 relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <span className="material-symbols-outlined text-xl">speed</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">
                  LOCO PILOT CAB HUD · KAVACH 4.0 TCAS
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  DMI DISPLAY V4
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Train #{train.id} · {train.name} · WAP-7 6350 HP Electric Locomotive
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-all"
          >
            ✕
          </button>
        </div>

        {/* Cockpit Instrument Cluster */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 relative z-10">
          {/* Left: Analog Speedometer Dial */}
          <div className="md:col-span-5 bg-[#0d1322] border border-slate-800 rounded-2xl p-5 flex flex-col items-center justify-center relative shadow-inner">
            <span className="text-[10px] font-mono uppercase text-slate-400 font-bold tracking-widest absolute top-3 left-4">
              SPEED INDICATOR (DMI)
            </span>

            {/* Circular Speedometer Gauge */}
            <div className="relative w-56 h-56 flex items-center justify-center mt-2">
              <svg viewBox="0 0 200 200" className="w-full h-full">
                {/* Dial Arc Track */}
                <circle
                  cx="100"
                  cy="100"
                  r="75"
                  fill="none"
                  stroke="#1e293b"
                  strokeWidth="12"
                  strokeDasharray="314"
                  strokeDashoffset="105"
                  transform="rotate(135 100 100)"
                />
                {/* Permitted Speed Band (up to 130 km/h) */}
                <circle
                  cx="100"
                  cy="100"
                  r="75"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="12"
                  strokeDasharray="314"
                  strokeDashoffset="170"
                  transform="rotate(135 100 100)"
                  opacity="0.5"
                />
                {/* Danger Over-speed Band (130 - 160 km/h) */}
                <circle
                  cx="100"
                  cy="100"
                  r="75"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="12"
                  strokeDasharray="314"
                  strokeDashoffset="275"
                  transform="rotate(135 100 100)"
                  opacity="0.8"
                />

                {/* Ticks and Numbers */}
                {[0, 20, 40, 60, 80, 100, 120, 140, 160].map((v) => {
                  const angle = -120 + (v / 160) * 240;
                  const rad = (angle * Math.PI) / 180;
                  const x = 100 + 60 * Math.sin(rad);
                  const y = 100 - 60 * Math.cos(rad);
                  return (
                    <text
                      key={v}
                      x={x}
                      y={y + 3}
                      fill="#94a3b8"
                      fontSize="9"
                      fontWeight="bold"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {v}
                    </text>
                  );
                })}

                {/* Center Hub */}
                <circle cx="100" cy="100" r="14" fill="#0f172a" stroke="#06b6d4" strokeWidth="3" />

                {/* Speedometer Needle */}
                <g transform={`rotate(${needleRotation} 100 100)`}>
                  <line
                    x1="100"
                    y1="100"
                    x2="100"
                    y2="34"
                    stroke={emergencyBrake ? '#ef4444' : '#06b6d4'}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    filter="drop-shadow(0 0 6px #06b6d4)"
                  />
                  <polygon points="100,28 97,38 103,38" fill="#06b6d4" />
                </g>
              </svg>

              {/* Digital Readout inside Center */}
              <div className="absolute bottom-6 flex flex-col items-center">
                <span className="text-3xl font-black font-mono tracking-tight text-cyan-400">
                  {speed}
                </span>
                <span className="text-[10px] font-mono text-slate-400 uppercase">KM / H</span>
              </div>
            </div>

            {/* Permitted Speed Limit Notice */}
            <div className="w-full mt-1 pt-2 border-t border-slate-800 flex justify-between items-center text-xs font-mono">
              <span className="text-slate-400">MAX PERMITTED (MPS):</span>
              <span className="text-emerald-400 font-bold">130 KM/H</span>
            </div>
          </div>

          {/* Right: Kavach 4.0 In-Cab Signaling & Braking Profile */}
          <div className="md:col-span-7 flex flex-col gap-3">
            {/* Top Kavach Aspect Bar */}
            <div className="grid grid-cols-3 gap-3">
              {/* In-Cab Signal */}
              <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
                <span className="text-[10px] font-mono text-slate-400">CAB SIGNAL (ASPECT)</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="w-5 h-5 rounded-full bg-emerald-500 shadow-[0_0_12px_#10b981] animate-pulse"></span>
                  <span className="font-bold font-mono text-emerald-400 text-sm">PROCEED</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400 mt-1">
                  Next Sig: <strong>{(targetDistance / 1000).toFixed(2)} km</strong>
                </span>
              </div>

              {/* Kavach Mode */}
              <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
                <span className="text-[10px] font-mono text-slate-400">KAVACH 4.0 TCAS</span>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="material-symbols-outlined text-cyan-400 text-base">security</span>
                  <span className="font-bold font-mono text-cyan-400 text-sm">FULL SUPERV.</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 mt-1">
                  Radio Link: 457.5 MHz OK
                </span>
              </div>

              {/* Braking Authority */}
              <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
                <span className="text-[10px] font-mono text-slate-400">TARGET DISTANCE</span>
                <div className="font-mono text-sm font-bold text-white mt-1">
                  {targetDistance} METERS
                </div>
                <span className="text-[10px] font-mono text-slate-400 mt-1">
                  Braking Curve: NOMINAL
                </span>
              </div>
            </div>

            {/* Dynamic Braking Profile & Route Ahead Preview */}
            <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-3.5 flex flex-col gap-2">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-slate-400">TRACK PROFILE & MOVEMENT AUTHORITY</span>
                <span className="text-cyan-400 font-bold">ROUTE: UP RAJDHANI LINE</span>
              </div>

              {/* Simulated Rail Line Elevation/Gradient Profile */}
              <div className="h-16 w-full bg-[#080d16] rounded-lg border border-slate-800/80 p-2 relative overflow-hidden flex items-end">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px)] bg-[size:40px_100%] opacity-20"></div>

                {/* Simulated Target Distance Line */}
                <div className="w-full h-1 bg-slate-700 rounded-full relative mb-4">
                  <div
                    className="h-full bg-cyan-400 rounded-full"
                    style={{ width: `${Math.min(100, (targetDistance / 4000) * 100)}%` }}
                  ></div>
                  {/* Train Marker */}
                  <div className="absolute -top-2 left-4 w-4 h-4 rounded-full bg-cyan-400 border-2 border-white shadow-[0_0_10px_#06b6d4]"></div>
                  {/* Signal Post Marker */}
                  <div className="absolute -top-3 right-4 flex flex-col items-center">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#10b981]"></span>
                    <span className="text-[9px] font-mono font-bold text-emerald-400 mt-0.5">S-42</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>KM 394/12 (Current)</span>
                <span>Gradient: 1 in 200 (Rising)</span>
                <span>Signal Post S-42 (KM 398/02)</span>
              </div>
            </div>

            {/* Emergency Brake Controls */}
            <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-3 flex items-center justify-between gap-4">
              <div>
                <div className="text-xs font-bold text-white font-mono">
                  EMERGENCY BRAKE INTERVENTION (EBI / MRSB)
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  {emergencyBrake
                    ? '⚠️ EMERGENCY BRAKE ACTIVATED · AIR PRESSURE DUMPED'
                    : 'System standby. Automatic deceleration triggers if SPAD detected.'}
                </div>
              </div>

              {emergencyBrake ? (
                <button
                  onClick={handleResetBrake}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold shadow-lg transition-all"
                >
                  RESET BRAKES
                </button>
              ) : (
                <button
                  onClick={handleBrakeTest}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-bold shadow-lg shadow-rose-600/30 transition-all active:scale-95"
                >
                  APPLY EMERGENCY BRAKE
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Footer info strip */}
        <div className="border-t border-cyan-500/20 pt-3 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>STATIONARY KAVACH UNIT: NGP-TWR-04 · UHF RSSI: -68 dBm (EXCELLENT)</span>
          <button
            onClick={onClose}
            className="text-cyan-400 font-bold hover:underline"
          >
            Close Cockpit HUD [ESC]
          </button>
        </div>
      </div>
    </div>
  );
}
