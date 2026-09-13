import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import OverviewDashboard from './pages/OverviewDashboard.jsx';
import DigitalTwin from './pages/DigitalTwin.jsx';
import BlockPlanner from './pages/BlockPlanner.jsx';
import SegmentWhy from './pages/SegmentWhy.jsx';
import WhatIfSandbox from './pages/WhatIfSandbox.jsx';
import TaskPool from './pages/TaskPool.jsx';
import Optimization from './pages/Optimization.jsx';
import Feedback from './pages/Feedback.jsx';
import PredictOptimize from './pages/PredictOptimize.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<OverviewDashboard />} />
        <Route path="overview" element={<OverviewDashboard />} />
        <Route path="digital-twin" element={<DigitalTwin />} />
        <Route path="planner" element={<BlockPlanner />} />
        <Route path="segment-why" element={<SegmentWhy />} />
        <Route path="disruption" element={<WhatIfSandbox />} />
        <Route path="what-if" element={<Navigate to="/disruption" replace />} />
        <Route path="predict-optimize" element={<PredictOptimize />} />
        <Route path="task-pool" element={<TaskPool />} />
        <Route path="optimization" element={<Optimization />} />
        <Route path="feedback" element={<Feedback />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
