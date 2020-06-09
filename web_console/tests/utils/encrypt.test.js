const assert = require('assert');
const encrypt = require('../../utils/encrypt');

describe('encrypt', () => {
  it('should throw for illegal input', () => {
    assert.throws(() => encrypt(0));
  });

  it('should throw for empty string input', () => {
    assert.throws(() => encrypt(''));
  });

  it('should throw for illegal size', () => {
    assert.throws(() => encrypt('foo', 'bar'));
  });

  it('should throw for size smaller than 1', () => {
    assert.throws(() => encrypt('foo', 0));
  });

  it('should throw for size greater than 64', () => {
    assert.throws(() => encrypt('foo', 65));
  });

  it('should generate default 16-bit string', () => {
    assert.equal(encrypt('foo').length, 16);
  });

  it('should generate same output for same input', () => {
    const p1 = encrypt('foo');
    const p2 = encrypt('foo');
    assert.equal(p1, p2);
  });

  it('should generate different output for different input', () => {
    const t1 = encrypt('foo');
    const t2 = encrypt('bar');
    assert.notEqual(t1, t2);
  });
});
