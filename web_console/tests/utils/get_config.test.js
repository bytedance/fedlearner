const assert = require('assert');
const getConfig = require('../../utils/get_confg');

let serverConfig = null;
try {
  serverConfig = require('../../server.config');
} catch (err) { /* */ }
const defaultConfig = require('../../constants').DEFAULT_SERVER_CONFIG;

const testConfig = { ...defaultConfig, ...serverConfig };

describe('get_confg', () => {
  it('should get defaultConfig if customConfig is not provided', () => {
    assert.deepEqual(getConfig(), testConfig);
  });

  it('should get defaultConfig if customConfig is unqualified', () => {
    assert.deepEqual(getConfig(null), testConfig);
    assert.deepEqual(getConfig([]), testConfig);
    assert.deepEqual(getConfig(() => {}), testConfig);
    assert.deepEqual(getConfig('something'), testConfig);
  });

  it('should get defaultConfig if customConfig\'s properties have no actual value', () => {
    assert.equal(getConfig({ SERVER_CIPHER: undefined }).SERVER_CIPHER, testConfig.SERVER_CIPHER);
    assert.equal(getConfig({ SERVER_CIPHER: '' }).SERVER_CIPHER, testConfig.SERVER_CIPHER);
    assert.equal(getConfig({ SERVER_CIPHER: null }).SERVER_CIPHER, testConfig.SERVER_CIPHER);
  });

  it('should get customConfig if customConfig is provided', () => {
    const config = getConfig({ SERVER_CIPHER: 'undefined' });
    assert.equal(config.SERVER_CIPHER, 'undefined');
    assert.equal(config.K8S_HOST, testConfig.K8S_HOST);
  });
});
