const assert = require('assert');
const path = require('path');
const { readFileSync } = require('../../utils');
const { loadYaml, dumpYaml } = require('../../utils/yaml');
const testJson = require('../fixtures/test.json');

const testYaml = readFileSync(
  path.resolve(__dirname, '..', 'fixtures', 'test.yaml'),
  { encoding: 'utf-8' },
);

describe('loadYaml', () => {
  it('should load yaml as a JSON object', () => {
    assert.deepStrictEqual(loadYaml(testYaml), testJson);
  });
});

describe('dumpYaml', () => {
  it('should dump object as a YAML string and keep consistency', () => {
    // Note: array could be described in two style (`[]` or `-`)
    // so just don't compare yaml
    assert.deepStrictEqual(loadYaml(dumpYaml(testJson)), testJson);
  });
});
