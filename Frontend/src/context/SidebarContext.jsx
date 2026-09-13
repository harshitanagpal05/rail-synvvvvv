import React, { createContext, useContext, useState, useEffect } from 'react';

const SidebarContext = createContext();

export function SidebarProvider({ children }) {
  // Default to open (true) as in Image 1
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Optional: persist state to localStorage if available
  useEffect(() => {
    const saved = localStorage.getItem('railsync_sidebar_open');
    if (saved !== null) {
      setSidebarOpen(saved === 'true');
    }
  }, []);

  const toggleSidebar = () => {
    setSidebarOpen((prev) => {
      const next = !prev;
      localStorage.setItem('railsync_sidebar_open', String(next));
      return next;
    });
  };

  return (
    <SidebarContext.Provider value={{ sidebarOpen, setSidebarOpen, toggleSidebar }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}
