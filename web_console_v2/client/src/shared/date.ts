import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

export function formatTimestamp(input: number, format = 'YYYY-MM-DD HH:mm:ss') {
  if (input.toString().length === 10) {
    return dayjs.unix(input).format(format);
  }

  return dayjs(input).format(format);
}

export function fromNow(input: number, ...args: any[]) {
  return dayjs.unix(input).fromNow(...args);
}
