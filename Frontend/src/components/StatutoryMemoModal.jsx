import React from 'react';

export default function StatutoryMemoModal({ memoData, onClose }) {
  if (!memoData) return null;

  const now = new Date();
  const memoDate = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  const memoTime = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

  const division = memoData.division || 'Vadodara';
  const corridor = memoData.corridor || 'Delhi-Mumbai Rajdhani Corridor';
  const taskType = memoData.task_type || 'Emergency Rail Fracture Rectification';
  const duration = memoData.duration_hrs || '03h 30m';
  const memoNumber = `IR/COCC/BLK-${now.getFullYear()}/${now.getMonth() + 1}/${Math.floor(1000 + Math.random() * 9000)}`;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-white text-slate-900 rounded-2xl shadow-2xl overflow-y-auto flex flex-col font-serif p-8 border-4 border-slate-900 print:p-0 print:border-none">
        {/* Close & Print Buttons (hidden in print) */}
        <div className="flex items-center justify-between border-b-2 border-slate-300 pb-4 mb-6 font-sans print:hidden">
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-700">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse"></span>
            STATUTORY SANCTION BULLETIN · FORM T/1518 (ELECTRONIC)
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="px-4 py-1.5 rounded-lg bg-slate-900 text-white hover:bg-slate-800 text-xs font-mono font-bold flex items-center gap-1.5 transition-all shadow-md"
            >
              <span className="material-symbols-outlined text-sm">print</span>
              Print Memo (Form T/1518)
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-700 transition-all text-sm font-bold"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Official Indian Railways Header */}
        <div className="text-center border-b-2 border-slate-900 pb-4">
          <div className="text-sm font-bold tracking-widest uppercase">
            GOVERNMENT OF INDIA · MINISTRY OF RAILWAYS
          </div>
          <div className="text-2xl font-black tracking-tight text-slate-900 mt-1 uppercase">
            INDIAN RAILWAYS · CENTRAL OPERATIONS CONTROL CENTRE
          </div>
          <div className="text-xs font-sans font-bold text-slate-700 uppercase tracking-wider mt-0.5">
            DIVISIONAL HEADQUARTERS · {division.toUpperCase()} DIVISION
          </div>
          <div className="text-[11px] font-sans text-slate-600 mt-1">
            G&SR Chapter XV (Rules 15.06 & 15.08 - Working of Trains on Block Sections)
          </div>
        </div>

        {/* Memo Metadata Strip */}
        <div className="flex justify-between items-center py-3 border-b border-slate-300 text-xs font-mono">
          <div>
            <strong>MEMO NO:</strong> {memoNumber}
          </div>
          <div>
            <strong>DISPATCH TIME:</strong> {memoDate} {memoTime} IST
          </div>
          <div className="text-emerald-700 font-bold">
            STATUS: SANCTIONED (AUTOMATED)
          </div>
        </div>

        {/* Addressed To */}
        <div className="mt-4 text-xs font-sans space-y-1">
          <div><strong>TO:</strong> STATION MASTER(S) CONCERNED & SECTION CONTROLLER</div>
          <div><strong>COPY TO:</strong> SENIOR DIVISIONAL OPERATIONS MANAGER (SR. DOM)</div>
          <div><strong>COPY TO:</strong> SENIOR DIVISIONAL ENGINEER (SR. DEN / P-WAY)</div>
          <div><strong>COPY TO:</strong> TRACTION POWER CONTROLLER (TPC / ELECTRICAL)</div>
        </div>

        {/* Memo Subject */}
        <div className="mt-4 p-3 bg-slate-100 border border-slate-300 rounded-md text-xs font-sans">
          <strong>SUBJECT:</strong> OFFICIAL SANCTION OF LINE BLOCK & POWER BLOCK (OHE) WITH CAUTION ORDER (FORM T/409) ON {corridor.toUpperCase()}.
        </div>

        {/* Body Clauses */}
        <div className="mt-4 text-xs font-sans space-y-3 leading-relaxed text-slate-800">
          <p>
            <strong>1. AUTHORIZATION:</strong> Under authority delegated by the Chief Operations Manager (COM), permission is hereby granted to isolate and occupy the railway track segment specified below for urgent preventive engineering works.
          </p>

          <table className="w-full text-xs font-mono border-collapse border border-slate-400 my-2">
            <tbody>
              <tr className="bg-slate-50 border-b border-slate-300">
                <td className="p-2 font-bold border-r border-slate-300 w-1/3">DIVISION & CORRIDOR</td>
                <td className="p-2">{division} Division · {corridor}</td>
              </tr>
              <tr className="border-b border-slate-300">
                <td className="p-2 font-bold border-r border-slate-300">NATURE OF WORK</td>
                <td className="p-2 text-rose-700 font-bold">{taskType}</td>
              </tr>
              <tr className="bg-slate-50 border-b border-slate-300">
                <td className="p-2 font-bold border-r border-slate-300">SANCTIONED WINDOW</td>
                <td className="p-2">{duration} (Calculated via Google OR-Tools CP-SAT)</td>
              </tr>
              <tr className="border-b border-slate-300">
                <td className="p-2 font-bold border-r border-slate-300">SPEED RESTRICTION (TSR)</td>
                <td className="p-2 font-bold text-amber-700">30 KM/H (CAUTION ORDER FORM T/409 ISSUED)</td>
              </tr>
              <tr className="bg-slate-50">
                <td className="p-2 font-bold border-r border-slate-300">TRAFFIC DIVERSION</td>
                <td className="p-2 text-emerald-700 font-bold">DOWN LINE BI-DIRECTIONAL SIGNALLING ENGAGED (0 DETENTIONS)</td>
              </tr>
            </tbody>
          </table>

          <p>
            <strong>2. SAFETY PROTOCOL:</strong> Red Banner Flags and 3 Detonators placed at 600m and 1200m distances respectively. OHE Traction Power isolated with earth discharge rods affixed on both sides before commencement of work.
          </p>
          <p>
            <strong>3. SYSTEM VALIDATION:</strong> This sanction order was generated by <strong>RailSync 2.0 AI Decision Engine</strong> based on Weibull AFT Failure Forecasts and synchronized with CRIS Control Office Application (COA).
          </p>
        </div>

        {/* Signatures & Electronic Stamp */}
        <div className="mt-8 pt-4 border-t-2 border-slate-900 flex justify-between items-end text-xs font-sans">
          <div>
            <div className="w-24 h-24 border-2 border-slate-700 flex flex-col items-center justify-center text-center p-1 font-mono text-[9px] text-slate-500">
              <span className="font-bold text-slate-900">QR VERIFY</span>
              <span className="text-[8px] mt-1 break-all">IR-COCC-{memoNumber.slice(-4)}</span>
              <span className="text-[8px] text-emerald-600 font-bold mt-1">VALID SECURE</span>
            </div>
          </div>

          <div className="text-right space-y-1 font-mono text-xs">
            <div className="inline-block px-3 py-1 border-2 border-emerald-700 rounded text-emerald-800 font-bold text-[10px] uppercase mb-1">
              DIGITALLY SIGNED & DISPATCHED
            </div>
            <div className="font-bold text-slate-900">CHIEF CONTROLLER (CENTRAL DESK)</div>
            <div className="text-slate-600">Operations Control Centre (COCC)</div>
            <div className="text-slate-500 text-[10px]">Indian Railways Electronic Sanction Registry</div>
          </div>
        </div>
      </div>
    </div>
  );
}
