import { formatTimestamp, fomatTimeCount } from './date';

// Beijing time
const DATE_20201_01_21_12_58_23 = 1611205103;

describe('Date formatters', () => {
  it('formatTimestamp', () => {
    expect(formatTimestamp(DATE_20201_01_21_12_58_23)).toBe('2021-01-21 12:58:23');
    expect(formatTimestamp(DATE_20201_01_21_12_58_23, 'MM/DD/YYYY')).toBe('01/21/2021');
    expect(formatTimestamp(DATE_20201_01_21_12_58_23 * 1000)).toBe('2021-01-21 12:58:23');
    expect(formatTimestamp(DATE_20201_01_21_12_58_23, 'MM/DD/YYYY')).toBe('01/21/2021');
  });

  it('fomatTimeCount', () => {
    expect(fomatTimeCount(3600)).toBe('01:00:00');
    expect(fomatTimeCount(60)).toBe('00:01:00');
    expect(fomatTimeCount(10000)).toBe('02:46:40');
    expect(fomatTimeCount(1)).toBe('00:00:01');
  });
});
