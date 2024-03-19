import {
  removeUndefined,
  removeFalsy,
  removePrivate,
  transformKeysToSnakeCase,
  binarizeBoolean,
  record,
} from './object';

describe('Object helpers', () => {
  it('Remove undefined', () => {
    const cases = [
      {
        i: { a: 1, b: 2, c: null, d: false },
        o: { a: 1, b: 2, c: null, d: false },
      },
      {
        i: { a: 'string', b: undefined, c: null, d: false },
        o: { a: 'string', c: null, d: false },
      },
    ];

    cases.forEach(({ i, o }) => {
      expect(removeUndefined(i)).toEqual(o);
    });
  });

  it('Remove falsy values', () => {
    const cases = [
      {
        i: { a: 0, b: '', c: null, d: false, e: undefined },
        o: { a: 0, d: false },
      },
      {
        i: { a: 'string', b: undefined, c: null, d: false },
        o: { a: 'string', d: false },
      },
    ];

    cases.forEach(({ i, o }) => {
      expect(removeFalsy(i)).toEqual(o);
    });
  });

  it('Remove private values (key starts with _ )', () => {
    const cases = [
      {
        i: { a: 0, _b: '', c: null, d: false, _e: undefined },
        o: { a: 0, c: null, d: false },
      },
    ];

    cases.forEach(({ i, o }) => {
      expect(removePrivate(i)).toEqual(o);
    });
  });

  it('Transform keys to snake_case', () => {
    const cases = [
      {
        i: { projectId: 1, workflowName: 'test' },
        o: { project_id: 1, workflow_name: 'test' },
      },
      {
        i: {},
        o: {},
      },
    ];

    cases.forEach(({ i, o }) => {
      expect(transformKeysToSnakeCase(i)).toEqual(o);
    });
  });

  it('Binarize boolean values', () => {
    const cases = [
      {
        i: { a: 0, b: '', c: true, d: false, e: undefined },
        o: { a: 0, b: '', c: 1, d: 0, e: undefined },
      },
      {
        i: { c: 'true', d: 'false' },
        o: { c: 'true', d: 'false' },
      },
    ];

    cases.forEach(({ i, o }) => {
      expect(binarizeBoolean(i)).toEqual(o);
    });
  });
  it('Record', () => {
    expect(
      record(
        {
          a: 1,
          b: 2,
          c: 3,
        },
        1,
      ),
    ).toEqual({
      a: 1,
      b: 1,
      c: 1,
    });

    expect(
      record(
        {
          a: 1,
          b: 2,
          c: 3,
        },
        false,
      ),
    ).toEqual({
      a: false,
      b: false,
      c: false,
    });

    expect(
      record(
        {
          a: 1,
          b: 2,
          c: 3,
        },
        undefined,
      ),
    ).toEqual({
      a: undefined,
      b: undefined,
      c: undefined,
    });
  });
});
