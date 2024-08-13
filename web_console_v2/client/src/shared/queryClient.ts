/* istanbul ignore file */

import { QueryClient } from 'react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
    },
  },
});

/**
 * Force to trigger one or multiple query's refetch
 * by invalid there's result
 */
export function forceToRefreshQuery(queryKey: string | any[]) {
  return queryClient.invalidateQueries(queryKey);
}

export default queryClient;
