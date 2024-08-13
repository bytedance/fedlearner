import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import UTC from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(relativeTime);
dayjs.extend(UTC);
dayjs.extend(timezone);

export function formatTimestamp(input: number, format = 'YYYY-MM-DD HH:mm:ss') {
  try {
    if (input.toString().length === 10) {
      return dayjs.unix(input).tz('Asia/Shanghai').format(format);
    }

    return dayjs(input).tz('Asia/Shanghai').format(format);
  } catch (error) {
    return '[formatTimestamp]: Input error';
  }
}

/**
 * Give a second value and return a formatted time count till now
 * @param input a number accurate to seconds
 * @returns  HH:mm:ss
 */
export function formatTimeCount(input: number): string {
  const hours = Math.floor(input / 3600).toString();
  const minutes = Math.floor((input % 3600) / 60).toString();
  const seconds = ((input % 3600) % 60).toString();

  return `${_fillZero(hours)}:${_fillZero(minutes)}:${_fillZero(seconds)}`;
}

function _fillZero(input: string) {
  if (input.length > 1) return input;

  return '0' + input;
}

export function disableFuture(date: any) {
  return dayjs(date).valueOf() > Date.now();
}
