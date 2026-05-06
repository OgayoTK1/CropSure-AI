import { Navigate, Route, Routes } from 'react-router-dom';

import Layout from '@/components/Layout';
import DashboardPage from '@/pages/DashboardPage';
import EnrollPage from '@/pages/EnrollPage';
import FarmDetailPage from '@/pages/FarmDetailPage';
import NotFoundPage from '@/pages/NotFoundPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/enroll" replace />} />
        <Route path="/enroll" element={<EnrollPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/farms/:farmId" element={<FarmDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  );
}
