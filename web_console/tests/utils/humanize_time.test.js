const assert = require('assert');
const time = require('../../utils/humanize_time');

describe('humanize_time utility', () => {
  it('should return humanized time string for any date object', () => {
    const date = new Date(Date.now());
    assert.match(time(date), /^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$/);
  });

  it('should return None for null object', () => {
    assert.equal(time(null), 'None');
  });
});
