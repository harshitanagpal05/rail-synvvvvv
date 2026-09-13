import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useSidebar } from '../context/SidebarContext.jsx';
import railSyncLogo from '../assets/railsync-logo.png';

const navItems = [
  { path: '/overview', alias: '/', label: 'Overview', icon: 'dashboard' },
  { path: '/predict-optimize', label: 'Predict & Optimize (Live)', icon: 'bolt', highlight: true },
  { path: '/digital-twin', label: 'Corridor Digital Twin', icon: 'conversion_path' },
  { path: '/planner', label: 'Schedule & Block Planner', icon: 'calendar_month' },
  { path: '/segment-why', label: "Segment 'Why?' Risk", icon: 'psychology' },
  { path: '/disruption', alias: '/what-if', label: 'What-If Sandbox', icon: 'tune' },
  { path: '/task-pool', label: 'Department Task Pool', icon: 'swap_horiz' },
  { path: '/optimization', label: 'Pareto Optimization', icon: 'stacked_line_chart' },
  { path: '/feedback', label: 'Feedback & Audit', icon: 'history_edu' },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useSidebar();
  const location = useLocation();

  return (
    <aside
      className={`fixed top-0 left-0 h-screen z-50 bg-[#0c172b] text-white flex flex-col transition-all duration-300 ease-in-out border-r border-[#1a2942] select-none ${
        sidebarOpen ? 'w-64 translate-x-0 opacity-100 shadow-2xl' : 'w-0 -translate-x-full opacity-0 overflow-hidden pointer-events-none'
      }`}
    >
      {/* Sidebar Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-[#1a2942] shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded bg-primary-container border border-primary-fixed/20 flex items-center justify-center shrink-0 shadow-sm overflow-hidden">
            <img
              alt="RailSync Logo"
              className="h-6 w-6 object-contain"
              src={railSyncLogo}
              onError={(e) => {
                e.currentTarget.src = '/railsync-logo.png';
              }}
            />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-headline-sm text-[15px] font-bold tracking-tight text-white leading-tight">
              RAILSYNC
            </span>
            <span className="font-label-caps text-[9px] uppercase tracking-wider text-slate-400 font-semibold">
              NCR / PRYJ DIV
            </span>
          </div>
        </div>

        {/* Collapse Button */}
        <button
          onClick={toggleSidebar}
          title="Collapse Sidebar"
          className="w-8 h-8 rounded flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">menu_open</span>
        </button>
      </div>

      {/* Quick Action Button for Defect Reporting */}
      <div className="px-3 pt-3 pb-1">
        <NavLink
          to="/predict-optimize"
          className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-lg bg-primary hover:bg-primary/90 text-on-primary text-[12px] font-bold shadow-sm transition-all group"
        >
          <span className="material-symbols-outlined text-[17px] text-on-primary group-hover:rotate-12 transition-transform">
            bolt
          </span>
          <span>Report Defect & Optimize</span>
        </NavLink>
      </div>

      {/* Operations Console Section */}
      <div className="px-4 pt-3 pb-1">
        <span className="font-label-caps text-[10px] tracking-wider uppercase text-slate-400 font-bold">
          OPERATIONS CONSOLE
        </span>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto no-scrollbar py-1 space-y-1 px-2">
        {navItems.map((item) => {
          const isActive =
            location.pathname === item.path ||
            (item.alias && location.pathname === item.alias);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 group ${
                isActive
                  ? 'bg-[#182844] text-white font-semibold shadow-sm border-l-2 border-primary-fixed'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <span
                className={`material-symbols-outlined text-[19px] shrink-0 transition-colors ${
                  isActive ? 'text-tertiary-fixed' : 'text-slate-400 group-hover:text-slate-200'
                }`}
              >
                {item.icon}
              </span>
              <span className="truncate">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Ticker & System Telemetry Footer */}
      <div className="p-3 bg-[#080f1d] border-t border-[#1a2942] text-[11px] font-code-sm shrink-0 flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-slate-400">
          <span className="uppercase tracking-wider font-semibold">FOIS / COA</span>
          <span className="text-slate-300">SYNC: 42s ago</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span className="uppercase tracking-wider font-semibold">CRIS LINK</span>
          <span className="flex items-center gap-1.5 text-on-tertiary-container font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-on-tertiary-container animate-pulse"></span>
            NORMAL
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span className="uppercase tracking-wider font-semibold">ENGINE</span>
          <span className="text-primary-fixed font-semibold">SOLVER v4.2</span>
        </div>
      </div>
    </aside>
  );
}
