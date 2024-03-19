/* istanbul ignore file */

import History from 'history';

export function parseSearch(location: History.Location | Location) {
  return new URLSearchParams(location.search);
}
