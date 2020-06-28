const isPlainObject = require('lodash/isPlainObject');

let config = {};
try {
  config = require('../server.config');
} catch (err) { /* */ }

const defaultConfig = require('../constants').DEFAULT_SERVER_CONFIG;

module.exports = function getConfig(customConfig) {
  const override = isPlainObject(customConfig)
    ? Object.keys(customConfig).reduce((prev, key) => {
      if (customConfig[key]) {
        prev[key] = customConfig[key];
      }
      return prev;
    }, {})
    : null;
  return { ...defaultConfig, ...config, ...override };
};
