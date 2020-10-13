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
          source: '/training',
          destination: '/training/job',
        },
      ];
    },
  },
};
