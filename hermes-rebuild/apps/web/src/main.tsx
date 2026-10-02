import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { App } from './app/App';
import { createQueryClient } from './app/query-client';
import './shared/ui/tokens.css';
import './shared/ui/shell.css';
import './shared/ui/styles.css';

const container = document.getElementById('root');
if (!container) throw new Error('Missing application mount element');
createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={createQueryClient()}><App /></QueryClientProvider>
  </StrictMode>,
);
