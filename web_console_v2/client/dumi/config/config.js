/* eslint-disable import/no-anonymous-default-export */
import { resolve } from 'path';

export default {
  title: 'fedlearner',
  locales: [
    ['zh-CN', '中文'],
    ['en-US', 'English'],
  ],
  chainWebpack(memo) {
    memo.plugins.delete('copy');
    memo.resolve.modules.add(resolve(__dirname, '../../src'));
  },
  alias: {
    src: resolve(__dirname, '../../src'),
    components: resolve(__dirname, '../../src/components'),
    assets: resolve(__dirname, '../../src/assets'),
    styles: resolve(__dirname, '../../src/styles'),
    typings: resolve(__dirname, '../../src/typings'),
    shared: resolve(__dirname, '../../src/shared'),
    i18n: resolve(__dirname, '../../src/i18n'),
    services: resolve(__dirname, '../../src/services'),
    stores: resolve(__dirname, '../../src/stores'),
  },
  apiParser: {
    propFilter: {
      skipNodeModules: true,
    },
    shouldExtractLiteralValuesFromEnum: true,
    shouldExtractValuesFromUnion: true,
  },
  define: {
    // Force enable mock data
    'process.env.REACT_APP_ENABLE_FULLY_MOCK': 'true',
    'process.env.IS_DUMI_ENV': 'true',
  },
};
