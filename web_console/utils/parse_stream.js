const { Readable } = require('stream');

module.exports = function parseStream(stream, isText = false) {
  return new Promise((resolve, reject) => {
    if (!(stream instanceof Readable)) {
      return resolve(stream);
    }

    stream.setEncoding('utf8');

    let body = '';
    stream.on('data', (chunk) => {
      body += chunk;
    });
    stream.on('end', () => {
      try {
        if (isText) {
          return resolve(body);
        }
        const data = JSON.parse(body);
        resolve(data);
      } catch (err) {
        reject(err);
      }
    });
    stream.on('error', (err) => {
      reject(err);
    });
  });
};
