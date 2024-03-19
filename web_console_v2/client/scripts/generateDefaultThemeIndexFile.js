// Ensure environment variables are read.
require('../config/env');

const fs = require('fs');
const { promisify } = require('util');
const path = require('path');
const writeFileAsync = promisify(fs.writeFile);

const theme = process.env.THEME || 'normal';

const INDEX_PATH = path.resolve(__dirname, `../src/styles/index.ts`);
const THEME_PATH = path.resolve(__dirname, `../src/styles/theme.ts`);

try {
  const indexTpl = `/* eslint-disable */
/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, src/.env.development or src/.env.production is the file you should go
 */
import defaultTheme from './themes/${theme}';

export { defaultTheme };
`;
  writeFileAsync(INDEX_PATH, indexTpl, 'utf8');
  console.log(`[Theme: ${theme}] src/styles/index.js file done ✅`);
} catch (error) {
  console.error(`[Theme: ${theme}] src/styles/index.js file done ❌`, error);
}

try {
  const indexTpl = `/* eslint-disable */
/**
 * WARNING: This file is auto-generated
 * DO NOT modify it directly, src/.env.development or src/.env.production is the file you should go
 */
import defaultTheme from './themes/${theme}/${theme}';

export default defaultTheme;
`;
  writeFileAsync(THEME_PATH, indexTpl, 'utf8');
  console.log(`[Theme: ${theme}] src/styles/theme.js file done ✅`);
} catch (error) {
  console.error(`[Theme: ${theme}] src/styles/theme.js file done ❌`, error);
}
