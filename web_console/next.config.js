module.exports = {
  pageExtensions: ['jsx'],
  poweredByHeader: false,
  experimental: {
    rewrites() {
      return [
        {
          source: '/admin',
          destination: '/admin/federation',
        },
        {
          source: '/datasource',
          destination: '/datasource/job',
        },
        {
          source: '/trainning',
          destination: '/trainning/job',
        },
      ];
    },
  },
};
