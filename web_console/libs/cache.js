const LRU = require('ylru');

/**
 * LRU cahce for logged user
 */
class UserLRU extends LRU {
  constructor() {
    // hash-lru uses double hash storage, so the size should be cut in half
    super(1500);
  }

  set(key, value, options = { maxAge: 2592000000 }) {
    if (typeof key !== 'string' || !/^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$/.test(key)) {
      throw new Error(`Illegal key: ${key}`);
    }

    if (typeof options !== 'object' || ('maxAge' in options && typeof options.maxAge !== 'number')) {
      throw new Error(`Illegal options: ${options}`);
    }

    super.set(key, value, options);
  }
}

const users = new UserLRU();

module.exports = {
  users,
};
