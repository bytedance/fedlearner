export function readAsJSONFromFile<T = object>(file: File): Promise<T> {
  return new Promise((resolve, reject) => {
    /* istanbul ignore if */
    if (!window.FileReader) {
      return reject(
        new Error(
          "Detect that Environment doesn't support FileReader yet, please using lastest Chrome",
        ),
      );
    }
    const reader = new FileReader();
    reader.onload = function () {
      try {
        const result = JSON.parse(this.result?.toString() || '');
        resolve(result);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.onabort = reject;

    reader.readAsText(file);
  });
}

export function readAsBinaryStringFromFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    /* istanbul ignore if */
    if (!window.FileReader) {
      return reject(
        new Error(
          "Detect that Environment doesn't support FileReader yet, please using lastest Chrome",
        ),
      );
    }
    const reader = new FileReader();
    reader.onload = function () {
      /* istanbul ignore else */
      if (typeof reader.result === 'string') {
        resolve(btoa(reader.result));
      }
    };
    reader.onerror = reject;
    reader.onabort = reject;
    reader.readAsBinaryString(file);
  });
}

export function readAsTextFromFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    /* istanbul ignore if */
    if (!window.FileReader) {
      return reject(
        new Error(
          "Detect that Environment doesn't support FileReader yet, please using lastest Chrome",
        ),
      );
    }
    const reader = new FileReader();
    reader.onload = function () {
      /* istanbul ignore else */
      if (typeof reader.result === 'string') {
        resolve(reader.result);
      }
    };
    reader.onerror = reject;
    reader.onabort = reject;
    reader.readAsText(file);
  });
}

/**
 * Format bytes as human-readable text
 *
 * @param bytes Number of bytes.
 * @param si True to use metric (SI) units, aka powers of 1000. False to use
 *           binary (IEC), aka powers of 1024.
 * @param dp Number of decimal places to display.
 *
 * @return Formatted string.
 */
export function humanFileSize(bytes: number, si = true, dp = 1) {
  const thresh = si ? 1000 : 1024;

  if (Math.abs(bytes) < thresh) {
    return bytes + ' B';
  }

  const units = si
    ? ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
  let u = -1;
  const r = 10 ** dp;

  do {
    bytes /= thresh;
    ++u;
  } while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);

  return bytes.toFixed(dp) + ' ' + units[u];
}

/**
 * Get file info by relative file path
 * @param path file path
 * @returns file info { fileName, fileExt, parentPath }
 * @example getFileInfoByFilePath(leader/folder/main.js) => { parentPath: 'leader/folder', fileName: 'main.js', fileExt: 'js' }
 */
export function getFileInfoByFilePath(path: string) {
  const pathList = path.split('/');
  const parentPath = pathList.slice(0, pathList.length - 1).join('/');
  const fileName = pathList[pathList.length - 1];

  const extList = fileName.indexOf('.') > -1 ? fileName.split('.') : [];
  const fileExt = extList && extList.length > 0 ? extList[extList.length - 1] : '';

  return {
    parentPath,
    fileName,
    fileExt,
  };
}
/**
 * Build relative file path by file info
 * @param fileInfo \{ path: string; filename: string}
 * @returns relativePath string
 * @example buildRelativePath({ path:'folder', filename: 'a.js'}) => 'folder/a.js'
 */
export function buildRelativePath(fileInfo: { path: string; filename: string }) {
  const path = fileInfo?.path.replace(/\/+$/, '');

  return path && path !== '.' ? `${path}/${fileInfo.filename}` : fileInfo.filename;
}
