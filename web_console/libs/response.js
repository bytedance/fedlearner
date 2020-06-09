// TODO: adapt to Fedlearner convention
function ok(data, message = 'ok') {
  if (typeof message !== 'string') {
    throw new Error(`Illegal message: ${message}`);
  }

  return {
    status: 0,
    message,
    data,
  };
}

function error(message) {
  if (typeof message !== 'string') {
    throw new Error(`Illegal message: ${message}`);
  }

  return {
    status: -1,
    message,
  };
}

module.exports = {
  ok,
  error,
};
