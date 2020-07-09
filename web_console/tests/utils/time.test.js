const assert = require('assert');
const { humanizeTime, humanizeTimestamp } = require('../../utils/time');

describe('humanizeTime', () => {
  it('should return - for null datetime', () => {
    assert.deepStrictEqual(humanizeTime(null), '-');
  });

  it('should return custom placeholder for null datetime', () => {
    assert.deepStrictEqual(humanizeTime(null, 'YYYY-MM-DD', '*'), '*');
  });

  it('should return - for invalid datetime', () => {
    assert.deepStrictEqual(humanizeTime({}), '-');
  });

  it('should return humanized string with YYYY-MM-DD HH:mm:ss format', () => {
    assert.deepStrictEqual(humanizeTime('2020-06-16T06:29:05'), '2020-06-16 06:29:05');
  });

  it('should return humanized string with custom format', () => {
    assert.deepStrictEqual(humanizeTime('2020-06-16T06:29:05', 'YYYY-MM-DD'), '2020-06-16');
  });
});

describe('humanizeTimestamp', () => {
  it('should return - for 1970-01-01 00:00:00', () => {
    assert.deepStrictEqual(humanizeTimestamp(null), '-');
  });

  it('should return custom placeholder for empty timestamp', () => {
    assert.deepStrictEqual(humanizeTime('', 'YYYY-MM-DD', '*'), '*');
  });

  it('should return - for invalid timestamp', () => {
    assert.deepStrictEqual(humanizeTimestamp({}), '-');
  });

  it('should return humanized string with default YYYY-MM-DD HH:mm:ss format', () => {
    assert.deepStrictEqual(humanizeTimestamp(1592260145), '2020-06-16 06:29:05');
  });

  it('should return humanized string with custom format', () => {
    assert.deepStrictEqual(humanizeTimestamp(1592260145, 'YYYY-MM-DD'), '2020-06-16');
  });
});
