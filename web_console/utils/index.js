const { readFile, readFileSync, writeFile, writeFileSync, readdir, readdirSync } = require('fs');
const { exec, execSync, spawn } = require('child_process');
const { promisify } = require('util');

module.exports = {
  exec: promisify(exec),
  execSync: (cmd, options) => execSync(cmd, { encoding: 'utf-8', ...options }),
  spawn: (cmd, args = [], options) => spawn(cmd, args, { stdio: ['pipe', process.stdout, process.stderr], ...options }),
  readdir: promisify(readdir),
  readdirSync,
  readFile: promisify(readFile),
  readFileSync,
  writeFile: promisify(writeFile),
  writeFileSync,
};
