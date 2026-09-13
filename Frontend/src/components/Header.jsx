import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSidebar } from '../context/SidebarContext.jsx';
import railSyncLogo from '../assets/railsync-logo.png';

export default function Header() {
  const navigate = useNavigate();
  const { sidebarOpen, toggleSidebar } = useSidebar();
  const [time, setTime] = useState('14:28:12 IST');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      setTime(`${hours}:${minutes}:${seconds} IST`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="fixed top-0 right-0 z-40 w-full transition-all duration-300 ease-in-out">
      {sidebarOpen ? (
        /* ============================================================ */
        /* STATE 1: Sidebar is OPEN (Image 1 Layout)                    */
        /* Compact, clean, light-themed top operational strip           */
        /* ============================================================ */
        <div className="h-14 bg-surface-container-lowest border-b border-surface-container-high px-4 flex items-center justify-between shadow-xs transition-all duration-300">
          {/* Left section: Route dropdown & Shift details */}
          <div className="flex items-center gap-3 min-w-0">
            {/* Predict & Optimize Action Button */}
            <button
              onClick={() => navigate('/predict-optimize')}
              className="flex items-center gap-1.5 font-code-sm text-[11px] font-bold text-on-primary bg-primary hover:bg-primary/90 px-2.5 py-1 rounded shadow-2xs transition-colors cursor-pointer shrink-0"
              title="Report Live Defect & Run CP-SAT Optimization"
            >
              <span className="material-symbols-outlined text-[15px]">bolt</span>
              <span className="hidden xs:inline">PREDICT & OPTIMIZE</span>
            </button>

            {/* Route selector dropdown */}
            <button className="flex items-center gap-1.5 font-code-sm text-[12px] text-on-surface bg-surface-container px-2.5 py-1 rounded hover:bg-surface-container-high transition-colors max-w-[260px] truncate text-left font-medium">
              <span className="material-symbols-outlined text-[15px] text-primary shrink-0">train</span>
              <span className="truncate">NCR / PRYJ Div (NDLS-DDU Km 1024-1148)</span>
              <span className="material-symbols-outlined text-[15px] text-secondary shrink-0">arrow_drop_down</span>
            </button>

            {/* Shift & Desk details */}
            <div className="hidden md:flex items-center gap-2 text-[12px] font-code-sm text-secondary">
              <span className="w-2 h-2 rounded-full bg-on-tertiary-container animate-pulse"></span>
              <span className="font-semibold text-on-surface">DAY SHIFT (06:00 - 18:00 IST)</span>
              <span>•</span>
              <span>SR. DOM / COA DESK</span>
            </div>
          </div>

          {/* Right section: Conflicts, Time, Duty Controller */}
          <div className="flex items-center gap-2.5 shrink-0">
            {/* Active Conflicts badge */}
            <div className="flex items-center gap-1.5 bg-error-container text-on-error-container px-2.5 py-1 rounded font-code-sm text-[11px] font-bold shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-error animate-ping"></span>
              <span>2 ACTIVE CONFLICTS</span>
            </div>

            {/* Live Clock */}
            <div className="flex items-center gap-1.5 bg-surface-container-low px-2.5 py-1 rounded font-code-sm text-[12px] text-on-surface font-semibold shadow-xs">
              <span className="material-symbols-outlined text-[14px] text-secondary">schedule</span>
              <span>{time}</span>
            </div>

            {/* Duty Controller Pill */}
            <div className="hidden sm:flex items-center gap-2 bg-surface-container px-2.5 py-1 rounded text-on-surface font-code-sm text-[11px]">
              <div className="flex flex-col text-right leading-tight">
                <span className="font-bold text-[10px] text-primary">PRYJ-DY-OPT-04</span>
                <span className="text-[9px] text-secondary uppercase font-semibold">Duty Controller</span>
              </div>
              <div className="w-6 h-6 rounded-full bg-primary text-on-primary flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[14px]">person</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ============================================================ */
        /* STATE 2: Sidebar is HIDDEN / COLLAPSED (Image 2 Layout)      */
        /* Full dark header + operational subheader bar                 */
        /* ============================================================ */
        <div className="flex flex-col w-full shadow-md transition-all duration-300">
          {/* Main Dark Header Bar */}
          <div className="bg-primary-container text-on-primary pt-safe shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <div className="h-20 px-gutter flex flex-col justify-center gap-space-xs">
              {/* Row 1: Logo & Actions */}
              <div className="flex items-center justify-between gap-space-sm">
                <div className="flex items-center gap-space-sm min-w-0">
                  {/* Hamburger menu to expand sidebar */}
                  <button
                    onClick={toggleSidebar}
                    title="Open Sidebar"
                    className="w-8 h-8 rounded flex items-center justify-center text-on-primary hover:bg-primary/50 transition-colors shrink-0 mr-0.5 cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[22px]">menu</span>
                  </button>

                  {/* Predict & Optimize Button next to Hamburger */}
                  <button
                    onClick={() => navigate('/predict-optimize')}
                    className="hidden sm:flex items-center gap-1 bg-primary hover:bg-primary/80 text-on-primary px-2.5 py-1 rounded text-[11px] font-bold font-code-sm shadow-2xs transition-colors cursor-pointer shrink-0"
                    title="Report Live Defect & Run CP-SAT Optimization"
                  >
                    <span className="material-symbols-outlined text-[15px]">bolt</span>
                    <span>PREDICT & OPTIMIZE</span>
                  </button>

                  <img
                    alt="RailSync Operations Emblem"
                    className="h-8 w-auto object-contain"
                    src={railSyncLogo}
                    onError={(e) => {
                      e.currentTarget.src = '/railsync-logo.png';
                    }}
                  />
                  <div className="flex items-center gap-space-xs min-w-0">
                    <span className="font-headline-sm text-headline-sm text-on-primary tracking-tight truncate">
                      RailSync
                    </span>
                    <span className="font-label-caps text-label-caps uppercase bg-primary px-space-xs py-0.5 rounded text-on-primary-container tracking-wider shrink-0">
                      NCR / PRYJ DIV
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-space-sm shrink-0">
                  <div className="hidden sm:flex items-center gap-space-xs bg-tertiary-container px-space-xs py-0.5 rounded">
                    <span className="w-1.5 h-1.5 rounded-full bg-tertiary-fixed animate-pulse"></span>
                    <span className="font-label-caps text-label-caps text-tertiary-fixed">CRIS LIVE</span>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0 cursor-pointer">
                    <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
                  </div>
                </div>
              </div>

              {/* Row 2: Route, Status & Time */}
              <div className="flex items-center justify-between gap-gutter overflow-x-auto no-scrollbar">
                <div className="flex items-center gap-space-xs min-w-0">
                  <span className="material-symbols-outlined text-[16px] text-on-primary-container shrink-0">route</span>
                  <button className="flex items-center gap-space-xs font-code-sm text-code-sm text-on-primary bg-primary/40 px-space-xs py-0.5 rounded max-w-[200px] truncate text-left">
                    <span className="truncate">NDLS-DDU (Km 1024-1148)</span>
                    <span className="material-symbols-outlined text-[14px]">arrow_drop_down</span>
                  </button>
                </div>
                <div className="flex items-center gap-space-sm shrink-0">
                  <span className="font-label-caps text-label-caps bg-secondary/30 text-on-primary px-space-xs py-0.5 rounded hidden xs:inline">
                    #4102 COMPLETED
                  </span>
                  <div className="flex items-center gap-space-xs bg-primary/50 px-space-xs py-0.5 rounded">
                    <span className="material-symbols-outlined text-[12px] text-tertiary-fixed-dim">schedule</span>
                    <span className="font-code-sm text-code-sm text-on-primary">{time}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Operational Subheader Strip (Image 2 style) */}
          <div className="bg-surface-container-low px-gutter py-space-sm flex flex-col gap-space-xs shadow-xs border-b border-surface-container-high">
            <div className="flex items-center justify-between gap-space-sm flex-wrap">
              <div className="flex items-center gap-space-xs min-w-0">
                <span className="material-symbols-outlined text-[15px] text-primary">lan</span>
                <span className="font-code-sm text-code-sm font-semibold text-on-surface uppercase tracking-wide">
                  SEC: NDLS-DDU QUAD (ALJN-CNB)
                </span>
                <span className="font-label-caps text-label-caps bg-surface-container-highest text-on-surface-variant px-1 rounded">
                  MTR-408
                </span>
              </div>
              <div className="flex items-center gap-space-sm">
                <span className="font-label-caps text-label-caps bg-tertiary-fixed text-on-tertiary-fixed px-1.5 py-0.5 rounded font-bold uppercase">
                  DAY SHIFT 06:00-18:00
                </span>
                <span className="font-code-sm text-code-sm text-on-surface-variant">Sr. DOM / COA</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
