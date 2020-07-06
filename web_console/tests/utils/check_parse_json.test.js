const assert = require('assert');
const checkParseJson = require('../../utils/check_parse_json');

describe('checkParseJson', () => {
  it('should return true for plain object or array', () => {
    assert.deepEqual(checkParseJson({ a: 1 }), [true, { a: 1 }]);
    assert.deepEqual(checkParseJson([{ a: 1 }]), [true, [{ a: 1 }]]);
  });

  it('should return true for null/undefined/empty string', () => {
    assert.deepEqual(checkParseJson(null), [true, {}]);
    assert.deepEqual(checkParseJson(), [true, {}]);
    assert.deepEqual(checkParseJson(''), [true, {}]);
  });

  it('should return true for json string', () => {
    assert.deepEqual(checkParseJson('{ "a": 1 }'), [true, { a: 1 }]);
    assert.deepEqual(checkParseJson('[{ "a": 1 }]'), [true, [{ a: 1 }]]);
  });

  it('should return false for not-json string', () => {
    assert.deepEqual(checkParseJson('123'), [false, '123']);
    assert.deepEqual(checkParseJson('false'), [false, 'false']);
    assert.deepEqual(checkParseJson('string'), [false, 'string']);
    assert.deepEqual(checkParseJson('{ a: 1 }'), [false, '{ a: 1 }']);
  });

  it('should return false for other types', () => {
    assert.deepEqual(checkParseJson(123), [false, 123]);
    assert.deepEqual(checkParseJson(false), [false, false]);
    const func = () => {};
    assert.deepEqual(checkParseJson(func), [false, func]);
  });
});
