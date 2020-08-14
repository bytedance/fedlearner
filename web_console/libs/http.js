import ky from 'ky-universal';

export const client = ky.create({
  prefixUrl: '/api/v1',
  throwHttpErrors: false,
});

export const fetcher = (url, options = {}) => client.get(url, options).json();
