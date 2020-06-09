const assert = require('assert');
const { ok, error } = require('../../libs/response');

describe('ok', () => {
  it('should throw for illegal message', () => {
    assert.throws(() => ok(0, 1));
  });

  it('should return default undefined data with ok message and 0 status', () => {
    assert.deepEqual(ok(), { status: 0, data: undefined, message: 'ok' });
  });

  it('should return expected custom successful reponse', () => {
    assert.deepEqual(
      ok({ foo: 'bar' }, 'Process successfully'),
      { status: 0, data: { foo: 'bar' }, message: 'Process successfully' },
    );
  });
});

describe('error', () => {
  it('should throw for illegal message', () => {
    assert.throws(() => error(0));
  });

  it('should return expected custom failed reponse', () => {
    assert.deepEqual(error('Illegal params'), { status: -1, message: 'Illegal params' });
  });
});
