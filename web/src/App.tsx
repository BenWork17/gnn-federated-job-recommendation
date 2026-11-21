import React from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Layout } from './components/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { JobGraphPage } from './pages/JobGraphPage';
import { FlSimPage } from './pages/FlSimPage';
import { NodeMonitorPage } from './pages/NodeMonitorPage';
import { ConclusionsPage } from './pages/ConclusionsPage';

const PageWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, y: 6 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
  >
    {children}
  </motion.div>
);

const AnimatedRoutes: React.FC = () => {
  const location = useLocation();
  return (
    <AnimatePresence>
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageWrapper><OverviewPage /></PageWrapper>} />
        <Route path="/do-thi" element={<PageWrapper><JobGraphPage /></PageWrapper>} />
        <Route path="/lien-bang" element={<PageWrapper><FlSimPage /></PageWrapper>} />
        <Route path="/giam-sat-node" element={<PageWrapper><NodeMonitorPage /></PageWrapper>} />
        <Route path="/ket-luan" element={<PageWrapper><ConclusionsPage /></PageWrapper>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
};

export const App: React.FC = () => (
  <BrowserRouter>
    <Layout>
      <AnimatedRoutes />
    </Layout>
  </BrowserRouter>
);

export default App;
