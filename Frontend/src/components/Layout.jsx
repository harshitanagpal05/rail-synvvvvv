import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header.jsx';
import Sidebar from './Sidebar.jsx';
import { useSidebar } from '../context/SidebarContext.jsx';

export default function Layout() {
  const { sidebarOpen } = useSidebar();

  return (
    <div className="bg-surface font-body-md text-body-md text-on-surface min-h-screen antialiased flex">
      {/* Collapsible Left Sidebar */}
      <Sidebar />

      {/* Main App Content Area */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}
      >
        {/* Dynamic Header */}
        <Header />

        {/* Routed Page Container */}
        <div
          className={`flex-1 flex flex-col w-full transition-all duration-300 ${
            sidebarOpen ? 'pt-14' : 'pt-[116px]'
          } pb-8`}
        >
          <Outlet />
        </div>
      </div>
    </div>
  );
}
