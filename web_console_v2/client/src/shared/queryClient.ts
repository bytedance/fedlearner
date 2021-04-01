/* istanbul ignore file */

import { QueryClient } from 'react-query';

const queryClient = new QueryClient();

/**
 * Force to trigger one or multiple query's refetch
 * by invalid there's result
 */
export function forceToRefreshQuery(queryKey: string | string[]) {
  return queryClient.invalidateQueries(queryKey);
}

export default queryClient;
