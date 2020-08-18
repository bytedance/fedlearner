import ky from 'ky-universal';

export const client = ky.create({
  prefixUrl: '/api/v1',
  throwHttpErrors: false,
});

export const fetcher = (url, options = {}) => {
  options.headers = {
    ...options.headers,
    'X-Federation-Id': localStorage.getItem('federationID')
  }
  return client.get(url, options).json();
}
