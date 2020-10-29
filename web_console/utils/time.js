const dayjs = require('dayjs');
dayjs.extend(require('dayjs/plugin/duration'));

/**
 * Humanize datetime in humanized format
 *
 * @param  {string} date - a standard date string
 * @param  {string} format - a standard date format, defaults to 'YYYY-MM-DD HH:mm:ss'
 * @return {string}
 */
function humanizeTime(date, format = 'YYYY-MM-DD HH:mm:ss', placeholder = '-') {
  const datetime = dayjs(date);
  if (datetime.isValid()) {
    return datetime.format(format);
  }
  return placeholder;
}

/**
 * Humanize unix timestamp
 *
 * @param {number} timestamp - a standard unix timestamp
 * @param {string} format - a standard date format, defaults to 'YYYY-MM-DD HH:mm:ss'
 * @param {string} placeholder - a placeholder for blank string
 * @return {string}
 */
function humanizeTimestamp(timestamp, format = 'YYYY-MM-DD HH:mm:ss', placeholder = '-') {
  const datetime = dayjs.unix(timestamp);
  if (timestamp && datetime.isValid()) {
    return datetime.format(format);
  }
  return placeholder;
}

function humanizeDuration(date, placeholder = '-') {
  const datetime = dayjs(date);
  if (datetime.isValid()) {
    const duration = dayjs.duration(datetime.diff(dayjs()));
    const minutes = -Math.floor(duration.asMinutes());
    if (minutes < 60) return `${minutes}m ago`;
    const hours = -Math.floor(duration.asHours());
    if (hours < 24) return `${hours}h ago`;
    const days = -Math.floor(duration.asDays());
    return `${days}d ago`;
  }
  return placeholder;
}

module.exports = {
  humanizeTime,
  humanizeTimestamp,
  humanizeDuration,
};
