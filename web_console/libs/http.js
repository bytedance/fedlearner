import ky from 'ky-universal';

export const client = ky.create({
  prefixUrl: '/api/v1',
  throwHttpErrors: false,
});

export const fetcher = (url, options = {}) => {
  const federationID = localStorage.getItem('federationID')
  if (federationID) {
    options.headers = {
      ...options.headers,
      'X-Federation-Id':  federationID
    }
  }
  return client.get(url, options).json();
}
