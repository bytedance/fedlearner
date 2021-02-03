import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import UTC from 'dayjs/plugin/utc';

dayjs.extend(relativeTime);
dayjs.extend(UTC);

export function formatTimestamp(input: number, format = 'YYYY-MM-DD HH:mm:ss') {
  if (input.toString().length === 10) {
    return dayjs.unix(input).format(format);
  }

  return dayjs(input).format(format);
}

/** Inpput is accurate to seconds */
export function fomatTimeCount(input: number) {
  const hours = Math.floor(input / 3600).toString();
  const minutes = Math.floor((input % 3600) / 60).toString();
  const seconds = ((input % 3600) % 60).toString();

  return `${_fillZero(hours)}:${_fillZero(minutes)}:${_fillZero(seconds)}`;
}

function _fillZero(input: string) {
  if (input.length > 1) return input;

  return '0' + input;
}
