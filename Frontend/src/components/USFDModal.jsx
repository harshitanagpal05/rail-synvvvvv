import React from 'react';

export default function USFDModal({ defectData, onClose }) {
  if (!defectData) return null;

  const division = defectData.division || 'Vadodara';
  const assetType = defectData.asset_type || 'TRACK (UIC 60kg Rail)';
  const crackDepth = defectData.crack_depth || '8.4 mm';
  const flawType = defectData.flaw_type || 'Transverse Fissure (Gauge Corner)';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl bg-[#090d16] border border-amber-500/40 rounded-3xl p-6 shadow-[0_0_50px_rgba(245,158,11,0.2)] text-slate-100 flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-amber-500/20 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <span className="material-symbols-outlined text-xl">vital_signs</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">
                  ULTRASONIC FLAW DETECTION (USFD) B-SCAN
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
                  DEFECT CONFIRMED
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                RDSO / IRS Specification T-12 · Probe Frequency 4 MHz (70° Angle Beam)
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-all"
          >
            ✕
          </button>
        </div>

        {/* Oscilloscope Screen */}
        <div className="bg-[#050811] border-2 border-slate-800 rounded-2xl p-5 relative overflow-hidden flex flex-col items-center">
          {/* Green CRT Grid */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#064e3b_1px,transparent_1px),linear-gradient(to_bottom,#064e3b_1px,transparent_1px)] bg-[size:30px_30px] opacity-25 pointer-events-none"></div>

          <div className="w-full flex justify-between text-[10px] font-mono text-emerald-400 mb-2 z-10">
            <span>CH-1: 70° GAUGE CORNER PROBE</span>
            <span>GAIN: 54.0 dB · RANGE: 0 - 150 mm</span>
            <span className="animate-pulse">USFD RECORDER: ONLINE</span>
          </div>

          {/* SVG Oscilloscope Waveform */}
          <svg viewBox="0 0 600 200" className="w-full h-48 z-10">
            {/* Base noise line */}
            <path
              d="M 0 160 L 60 160 L 70 155 L 75 160 L 140 160 
                 L 145 152 L 150 160 L 220 160 
                 L 230 40 L 240 160 
                 L 300 160 L 305 156 L 310 160 
                 L 410 160 L 420 85 L 430 160 
                 L 600 160"
              fill="none"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ filter: 'drop-shadow(0 0 6px #10b981)' }}
            />

            {/* Echo 1: Initial Transducer Pulse */}
            <circle cx="20" cy="160" r="3" fill="#10b981" />
            <text x="20" y="180" fill="#94a3b8" fontSize="9" fontFamily="monospace" textAnchor="middle">
              TX PULSE
            </text>

            {/* Echo 2: High Amplitude Defect Peak */}
            <g transform="translate(230, 35)">
              <circle r="4" fill="#f43f5e" className="animate-ping" />
              <circle r="3" fill="#f43f5e" />
              <rect x="-45" y="-24" width="90" height="18" rx="3" fill="#881337" stroke="#f43f5e" strokeWidth="1" />
              <text x="0" y="-11" fill="#ffffff" fontSize="9" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
                FLAW ECHO ({crackDepth})
              </text>
            </g>

            {/* Echo 3: Rail Bottom Reflection Peak */}
            <g transform="translate(420, 80)">
              <rect x="-40" y="-20" width="80" height="16" rx="3" fill="#0f172a" stroke="#64748b" strokeWidth="1" />
              <text x="0" y="-8" fill="#cbd5e1" fontSize="8" fontFamily="monospace" textAnchor="middle">
                BOTTOM ECHO (166mm)
              </text>
            </g>
          </svg>

          {/* Calibrated Depth scale */}
          <div className="w-full flex justify-between border-t border-emerald-500/20 pt-1 text-[9px] font-mono text-slate-400 z-10">
            <span>0 mm</span>
            <span>25 mm</span>
            <span>50 mm</span>
            <span className="text-rose-400 font-bold">75 mm (FLAW)</span>
            <span>100 mm</span>
            <span>125 mm</span>
            <span>150 mm</span>
          </div>
        </div>

        {/* Defect Metadata Grid */}
        <div className="grid grid-cols-3 gap-3 font-mono text-xs">
          <div className="p-3 bg-[#0d1322] border border-slate-800 rounded-xl">
            <span className="text-slate-400 block text-[10px]">FLAW CLASSIFICATION</span>
            <span className="font-bold text-rose-400 mt-1 block">{flawType}</span>
            <span className="text-[10px] text-slate-500 mt-0.5 block">Action: Immediate Emergency Block</span>
          </div>

          <div className="p-3 bg-[#0d1322] border border-slate-800 rounded-xl">
            <span className="text-slate-400 block text-[10px]">LOCATION MARKER</span>
            <span className="font-bold text-white mt-1 block">{division} Division</span>
            <span className="text-[10px] text-slate-500 mt-0.5 block">KM 394/14 UP Rajdhani Track</span>
          </div>

          <div className="p-3 bg-[#0d1322] border border-slate-800 rounded-xl">
            <span className="text-slate-400 block text-[10px]">REPAIR METHOD (RDSO)</span>
            <span className="font-bold text-emerald-400 mt-1 block">Thermit Weld Replacement</span>
            <span className="text-[10px] text-slate-500 mt-0.5 block">Requires 3h 30m Track Possession</span>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center border-t border-amber-500/20 pt-3 text-xs font-mono text-slate-400">
          <span>RDSO CERTIFIED DIGITAL TWIN USFD INSPECTOR</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-900 font-bold transition-all"
          >
            Close USFD Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
