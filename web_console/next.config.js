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
      ];
    },
  },
};
