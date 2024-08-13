if (process.env.REACT_APP_ENABLE_IMAGE_VERSION_PAGE !== 'false') {
  module.exports = require('./index');
} else {
  module.exports = function () {
    return null;
  };
}
