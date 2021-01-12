import { isHead, isLast } from './array';

describe('isHead, isLast', () => {
  it('isHead', () => {
    const obj = { z: 2 };
    const isHeadCases = [
      {
        i: [1, [1, 2, 3]],
        o: true,
      },
      {
        i: [2, [1, 2, 3]],
        o: false,
      },
      {
        i: [obj, [1, obj, 3]],
        o: false,
      },
      {
        i: [obj, [obj, 1, 3]],
        o: true,
      },
    ];

    isHeadCases.forEach(({ i, o }) => {
      expect(isHead(i[0], i[1] as any)).toBe(o);
    });
  });

  it('isLast', () => {
    const obj = { z: 2 };
    const isLastCases = [
      {
        i: [1, [1, 2, 3]],
        o: false,
      },
      {
        i: [3, [1, 2, 3]],
        o: true,
      },
      {
        i: [obj, [1, obj, 3]],
        o: false,
      },
      {
        i: [obj, [1, 3, obj]],
        o: true,
      },
    ];

    isLastCases.forEach(({ i, o }) => {
      expect(isLast(i[0], i[1] as any)).toBe(o);
    });
  });
});
