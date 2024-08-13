const less = require('less');
const fs = require('fs');
const { promisify } = require('util');
const path = require('path');
const lessToJs = require('./lessVarsToJs');
const { camelCase } = require('./utils');
const readFileAsync = promisify(fs.readFile);
const writeFileAsync = promisify(fs.writeFile);

function resolveStyleDir(filename) {
  return path.resolve(__dirname, '../src/styles/'.concat(filename));
}

/** Configs */
const LESS_FILENAME = 'variables.less';
const CSS_FILENAME = '_variables.css';
const TS_FILENAME = '_theme.ts';

const PATH_TO_LESS_FILE = resolveStyleDir(LESS_FILENAME);
const PATH_TO_CSS_FILE = resolveStyleDir(CSS_FILENAME);
const PATH_TO_TS_FILE = resolveStyleDir(TS_FILENAME);

function watch(filename, callback, { immediate = true } = {}) {
  if (immediate && callback) {
    callback(filename);
  }

  fs.watchFile(filename, () => {
    callback(filename);
  });
}

function compile() {
  readFileAsync(PATH_TO_LESS_FILE)
    .then((buffer) => {
      const lessVarsString = buffer.toString();

      less.parse(lessVarsString, {}, async (err, root) => {
        if (err) {
          throw err;
        }

        root.variables();

        try {
          const cssTemplate = Object.keys(root._variables)
            .map((varName) => `--${camelCase(varName.slice(1))}: ${varName};`)
            .join('\n');

          const stringToRender = `/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, ./variables.less is the file you should go
 */
          ${lessVarsString}

          :root {
            ${cssTemplate}
          }`;

          const { css: cssNativeVarsString } = await less.render(stringToRender, {});

          writeFileAsync(PATH_TO_CSS_FILE, cssNativeVarsString, 'utf8');

          console.log('CSS Variables compile done ✅');
        } catch (error) {
          console.error('❌ [CSS Variables render error]:', error);
        }

        try {
          const output = lessToJs(lessVarsString);

          const themeString = `/* eslint-disable */
/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, ./variables.less is the file you should go
 */
const defaultTheme = {
${Object.entries(output)
  .map(([varName, varValue]) => {
    varValue = varValue.replace(/\n/g, '');
    return `  ${varName}: ${varValue.startsWith("'") ? `"${varValue}"` : `'${varValue}'`},`;
  })
  .join('\n')}
}

export default defaultTheme\n`;

          writeFileAsync(PATH_TO_TS_FILE, themeString, 'utf8');
          console.log('Theme compile done ✅');
        } catch (error) {
          console.error('❌ [Theme render error]:', error);
        }
      });
    })
    .catch((error) => {
      console.error('❌ [Less variables compile failed]:', error);
    });
}

watch(PATH_TO_LESS_FILE, compile);
