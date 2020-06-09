const crypto = require('crypto');

module.exports = function encrypt(str, size = 16) {
  if (!str || typeof str !== 'string') {
    throw new Error(`Illegal input: ${str}`);
  }

  if (typeof size !== 'number' || size <= 0 || size > 64) {
    throw new Error(`Illegal size: ${size}`);
  }

  return crypto.createHash('sha256').update(str).digest('hex').substring(0, size);
};
