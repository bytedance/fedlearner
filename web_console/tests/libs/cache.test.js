const assert = require('assert');
const { users } = require('../../libs/cache');
const encrypt = require('../../utils/encrypt');

const session = '0e918801-0dc2-406c-abeb-48534e5f0111';

const user = {
  username: 'fedlearner',
  avatar_url: 'https://foo.com/xxxx/aaaa/bbbb',
  display_name: 'Fedlearner',
  email: 'fedlearner@bytedance.com',
  groups: [],
};

function getSession(str) {
  const arr = encrypt(str, 32).split('');
  arr.splice(8, 0, '-');
  arr.splice(13, 0, '-');
  arr.splice(18, 0, '-');
  arr.splice(23, 0, '-');
  return arr.join('');
}

describe('users cache', () => {
  describe('Instantiation', () => {
    it('should be initialized with fixed max-size 1500 and no cache', () => {
      assert.strictEqual(users.max, 1500);
      assert.strictEqual(users.size, 0);
    });
  });

  describe('Getter & Setter', () => {
    it('should throw for illegal key', () => {
      assert.throws(() => users.set(0));
    });

    it('should throw for non-session key', () => {
      assert.throws(() => users.set('foo'));
    });

    it('should throw for illegal options', () => {
      assert.throws(() => users.set(session, {}, 'foo'));
    });

    it('should throw for illegal maxAge', () => {
      assert.throws(() => users.set(session, {}, { maxAge: 'foo' }));
    });

    it('should cache user as expected', () => {
      users.set(session, user);
      assert.deepEqual(users.get(session), user);
    });

    it('should cache users up to only 3000', () => {
      for (let i = 0; i < 3000; i += 1) {
        users.set(getSession(`${i}`), user);
      }
      assert(!users.get(session));
    });
  });
});
