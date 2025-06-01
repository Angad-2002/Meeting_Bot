import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

// Import theme
import theme from './theme';

// Import layouts
import Layout from './components/Layout';

// Import pages - these will be lazy loaded
import { lazy, Suspense } from 'react';
import LoadingScreen from './components/LoadingScreen';

// Lazy load pages
const PersonaList = lazy(() => import('./pages/PersonaList'));
const PersonaEditor = lazy(() => import('./pages/PersonaEditor'));
const BotManager = lazy(() => import('./pages/BotManager'));
const ActiveBots = lazy(() => import('./pages/ActiveBots'));
const NotFound = lazy(() => import('./pages/NotFound'));

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Suspense fallback={<LoadingScreen />}>
          <Routes>
            <Route path="/" element={<Layout />}>
              {/* Dashboard/home */}
              <Route index element={<PersonaList />} />
              
              {/* Personas */}
              <Route path="personas">
                <Route index element={<Navigate to="/" replace />} />
                <Route path="new" element={<PersonaEditor />} />
                <Route path=":id" element={<PersonaEditor />} />
              </Route>
              
              {/* Bots */}
              <Route path="bots" element={<BotManager />} />
              <Route path="active-bots" element={<ActiveBots />} />
              
              {/* 404 */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
