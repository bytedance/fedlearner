import dayjs from 'dayjs';
import { formatTimestamp, formatTimeCount, disableFuture } from './date';

// Beijing time
const DATE_20201_01_21_12_58_23 = 1611205103;

describe('Date formatters', () => {
  it('formatTimestamp', () => {
    expect(formatTimestamp(DATE_20201_01_21_12_58_23)).toBe('2021-01-21 12:58:23');
    expect(formatTimestamp(DATE_20201_01_21_12_58_23, 'MM/DD/YYYY')).toBe('01/21/2021');
    expect(formatTimestamp(DATE_20201_01_21_12_58_23 * 1000)).toBe('2021-01-21 12:58:23');
    expect(formatTimestamp(DATE_20201_01_21_12_58_23, 'MM/DD/YYYY')).toBe('01/21/2021');
    expect(formatTimestamp(10012341231241241412)).toBe('Invalid Date');

    // Mock fake error
    const unixSpy = jest.spyOn(dayjs, 'unix').mockImplementation(() => {
      throw new Error('fake error');
    });
    expect(formatTimestamp(DATE_20201_01_21_12_58_23)).toBe('[formatTimestamp]: Input error');
    unixSpy.mockRestore();
  });

  it('formatTimeCount', () => {
    expect(formatTimeCount(3600)).toBe('01:00:00');
    expect(formatTimeCount(60)).toBe('00:01:00');
    expect(formatTimeCount(10000)).toBe('02:46:40');
    expect(formatTimeCount(1)).toBe('00:00:01');
  });
  it('disableFuture', () => {
    const dateNowSpy = jest.spyOn(Date, 'now').mockImplementation(() => 1631527486469);
    expect(disableFuture(1631527486469 - 1000)).toBe(false);
    expect(disableFuture(1631527486469)).toBe(false);
    expect(disableFuture(1631527486469 + 1000)).toBe(true);
    dateNowSpy.mockRestore();
  });
});
