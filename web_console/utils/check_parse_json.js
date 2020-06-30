const isPlainObject = require('lodash/isPlainObject');

const typeIsOk = (p) => isPlainObject(p) || Array.isArray(p);

/**
 * @param jsonStr json string or something
 *
 * @return [pass: boolean, result: json]
 */
module.exports = function checkParseJson(jsonStr) {
  let pass = false;
  let result = jsonStr;
  if (jsonStr == null || jsonStr === '') {
    result = {};
    pass = true;
  } else if (typeIsOk(jsonStr)) {
    pass = true;
  } else if (typeof jsonStr === 'string') {
    try {
      const parsed = JSON.parse(jsonStr);
      if (typeIsOk(parsed)) {
        result = parsed;
        pass = true;
      }
    } catch (e) { /* */ }
  }
  return [pass, result];
};
