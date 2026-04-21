import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import EnrollmentPage from './pages/EnrollmentPage';
import DashboardPage from './pages/DashboardPage';
import FarmDetailPage from './pages/FarmDetailPage';

const App: React.FC = () => (
  <BrowserRouter>
    <ToastProvider>
      <Routes>
        <Route path="/" element={<EnrollmentPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/farm/:farmId" element={<FarmDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  </BrowserRouter>
);

export default App;