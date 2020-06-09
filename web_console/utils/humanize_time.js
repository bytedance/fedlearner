/**
 * transform ISO date to humanized string
 *
 * @param {Date} date - date object
 * @return {String}
 */
module.exports = (date) => {
  if (date) return date.toISOString().replace('T', ' ').substring(0, 19);

  return 'None';
};
