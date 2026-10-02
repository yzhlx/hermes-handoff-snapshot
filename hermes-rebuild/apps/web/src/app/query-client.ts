import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '../shared/api/client';

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5_000,
        retry: (attempt, error) => !(error instanceof ApiError && error.status < 500) && attempt < 1,
        refetchOnWindowFocus: true,
      },
      mutations: { retry: false },
    },
  });
}
