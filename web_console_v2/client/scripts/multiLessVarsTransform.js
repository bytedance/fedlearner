const less = require('less');
const fs = require('fs');
const { promisify } = require('util');
const path = require('path');
const lessToJs = require('./lessVarsToJs');
const { camelCase } = require('./utils');
const readFileAsync = promisify(fs.readFile);
const writeFileAsync = promisify(fs.writeFile);
const readDirAsync = promisify(fs.readdir);
const mkDirAsync = promisify(fs.mkdir);

const VARIABLES_DIR_PATH = path.resolve(__dirname, '../src/styles/variables');
const THEME_DIR_PATH = path.resolve(__dirname, '../src/styles/themes');

async function generateLessIndexFile(themeName, filePath) {
  try {
    const fileString = `/* eslint-disable */
/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, src/styles/variables/${themeName}.less is the file you should go
 */
@import 'assets/fonts/ClarityMono/index.less';
@import './${themeName}.css';

@import 'styles/variables/${themeName}.less';
@import 'styles/arco-overrides.less';
@import 'styles/global.less';
`;

    await writeFileAsync(filePath, fileString, 'utf8');
    console.log(`[Theme: ${themeName}] Less index file done ✅`);
  } catch (error) {
    console.log(`[Theme: ${themeName}] Less index file error ❌`, error);
  }
}
async function generateTsIndexFile(themeName, filePath) {
  try {
    const fileString = `/* eslint-disable */
/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, src/styles/variables/${themeName}.less is the file you should go
 */
import './${themeName}.less';
import defaultTheme from './${themeName}';

export default defaultTheme;
`;

    await writeFileAsync(filePath, fileString, 'utf8');
    console.log(`[Theme: ${themeName}] TS index file done ✅`);
  } catch (error) {
    console.log(`[Theme: ${themeName}] TS index file error ❌`, error);
  }
}

function watch(filename, callback, { immediate = true, callbackParams = [] } = {}) {
  if (immediate && callback) {
    callback(...(callbackParams || []));
  }

  if (process.env.NODE_ENV === 'development') {
    fs.watchFile(filename, () => {
      callback(...(callbackParams || []));
    });
  }
}

function compile(themeName, lessPath, cssPath, tsPath, indexLessPath, indexTsPath) {
  readFileAsync(lessPath)
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
 * DO NOT modify it directly, src/styles/variables/${themeName}.less is the file you should go
 */
          ${lessVarsString}

          :root {
            ${cssTemplate}
          }`;

          const { css: cssNativeVarsString } = await less.render(stringToRender, {});

          writeFileAsync(cssPath, cssNativeVarsString, 'utf8');

          console.log(`[Theme: ${themeName}] CSS Variables done ✅`);
        } catch (error) {
          console.log(`[Theme: ${themeName}] CSS Variables error ❌`, error);
        }

        try {
          const output = lessToJs(lessVarsString);

          const themeString = `/* istanbul ignore file */

/* eslint-disable */
/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, src/styles/variables/${themeName}.less is the file you should go
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

          writeFileAsync(tsPath, themeString, 'utf8');
          console.log(`[Theme: ${themeName}] TS Variables file done ✅`);
        } catch (error) {
          console.log(`[Theme: ${themeName}] TS Variables file error ❌`, error);
        }
      });

      generateLessIndexFile(themeName, indexLessPath);
      generateTsIndexFile(themeName, indexTsPath);
    })
    .catch((error) => {
      console.error(`[Theme: ${themeName}] failed ❌`, error);
      // Exit
      process.exit(1);
    });
}

// Get all file in variables folder
readDirAsync(VARIABLES_DIR_PATH).then((files) => {
  // Get all .less file
  const lessFiles = files.filter((fileName) => {
    return /\.less$/.test(fileName);
  });

  lessFiles.forEach((fileName) => {
    // Get filename as theme name
    // e.g. default.less => default, bio.less => bio
    const themeName = fileName.slice(0, fileName.lastIndexOf('.'));

    // Input Path
    const lessPath = path.resolve(VARIABLES_DIR_PATH, `${themeName}.less`);
    // Output path
    const cssPath = path.resolve(THEME_DIR_PATH, themeName, `${themeName}.css`);
    const tsPath = path.resolve(THEME_DIR_PATH, themeName, `${themeName}.ts`);
    const indexTsPath = path.resolve(THEME_DIR_PATH, themeName, `index.ts`);
    const indexLessPath = path.resolve(THEME_DIR_PATH, themeName, `${themeName}.less`);

    // Create folder If not existed
    mkDirAsync(path.resolve(THEME_DIR_PATH, themeName), { recursive: true }).then(() => {
      // Watch and compile less file to css variable file and ts file
      watch(lessPath, compile, {
        immediate: true,
        callbackParams: [themeName, lessPath, cssPath, tsPath, indexLessPath, indexTsPath],
      });
    });
  });
});
