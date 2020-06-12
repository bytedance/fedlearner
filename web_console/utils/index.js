const { readFile, readFileSync, writeFile, writeFileSync, readdir, readdirSync, unlink, unlinkSync } = require('fs');
const { exec, execSync } = require('child_process');
const { promisify } = require('util');

module.exports = {
  exec: promisify(exec),
  execSync: (cmd, options) => execSync(cmd, { encoding: 'utf-8', ...options }),
  readdir: promisify(readdir),
  readdirSync,
  readFile: promisify(readFile),
  readFileSync,
  writeFile: promisify(writeFile),
  writeFileSync,
  unlink: promisify(unlink),
  unlinkSync,
};
