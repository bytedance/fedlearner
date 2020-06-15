const yaml = require('js-yaml');

/**
 * https://github.com/nodeca/js-yaml#safeload-string---options-
 *
 * @param {string} str - original yaml
 * @param {Object} options - `js-yaml` options
 * @return {Object} - a JSON object
 */
function loadYaml(str, options = { json: true }) {
  return yaml.safeLoad(str, options);
}

/**
 * https://github.com/nodeca/js-yaml#safedump-object---options-
 *
 * @param {Object} obj - a JSON object
 * @param {Object} options - `js-yaml` options
 * @return {string} - a yaml
 */
function dumpYaml(obj, options = { sortKeys: false, noCompatMode: true }) {
  return yaml.safeDump(obj, options);
}

module.exports = {
  loadYaml,
  dumpYaml,
};
