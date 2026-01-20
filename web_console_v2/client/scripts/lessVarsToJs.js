// Code modified from https://github.com/michaeltaranto/less-vars-to-js/blob/master/src/index.js

const stripComments = require('strip-json-comments');
const { camelCase } = require('./utils');

const varRgx = /@[a-zA-Z0-9-_]*/g;
const followVar = (value, lessVars, dictionary) => {
  if (varRgx.test(value)) {
    // value is a variable
    return value.replace(varRgx, (cur) => {
      return followVar(lessVars[cur] || dictionary[cur.replace(varRgx, '')]);
    });
  }
  return value;
};

module.exports = (sheet, options = { dictionary: {} }) => {
  const { dictionary } = options;

  let lessVars = {};
  const matches = stripComments(sheet).match(/[@$](.*:[^;]*)/g) || [];

  matches.forEach((variable) => {
    const definition = variable.split(/:\s*/);
    let value = definition.splice(1).join(':');
    value = value.trim().replace(/^["'](.*)["']$/, '$1');
    lessVars[definition[0].replace(/['"]+/g, '').trim()] = value;
  });

  Object.keys(lessVars).forEach((key) => {
    const value = lessVars[key];
    lessVars[key] = followVar(value, lessVars, dictionary);
  });

  const transformKey = (key) => camelCase(key.slice(1));

  lessVars = Object.keys(lessVars).reduce((prev, key) => {
    prev[transformKey(key)] = lessVars[key];
    return prev;
  }, {});

  return lessVars;
};
