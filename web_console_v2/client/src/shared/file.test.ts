import {
  readAsJSONFromFile,
  readAsBinaryStringFromFile,
  readAsTextFromFile,
  humanFileSize,
  getFileInfoByFilePath,
  buildRelativePath,
} from './file';

const testImageFile = new File(['xyz'], 'test.png', { type: 'image/png' });
const testJSONFile = new File([JSON.stringify({ a: 1, b: 2 })], 'test.json', {
  type: 'application/json',
});

describe('readAsJSONFromFile', () => {
  it('image file', async () => {
    return expect(readAsJSONFromFile(testImageFile)).rejects.toThrow('Unexpected token x in JSON');
  });
  it('json file', async () => {
    const value = await readAsJSONFromFile(testJSONFile);
    expect(value).toEqual({
      a: 1,
      b: 2,
    });
  });
});

describe('readAsBinaryStringFromFile', () => {
  it('image file', async () => {
    const value = await readAsBinaryStringFromFile(testImageFile);
    expect(value).toBe(btoa('xyz'));
  });
  it('json file', async () => {
    const value = await readAsBinaryStringFromFile(testJSONFile);
    expect(value).toBe(btoa(JSON.stringify({ a: 1, b: 2 })));
  });
});

describe('readAsTextFromFile', () => {
  it('image file', async () => {
    const value = await readAsTextFromFile(testImageFile);
    expect(value).toBe('xyz');
  });
  it('json file', async () => {
    const value = await readAsTextFromFile(testJSONFile);
    expect(value).toBe(JSON.stringify({ a: 1, b: 2 }));
  });
});

it('humanFileSize', async () => {
  expect(humanFileSize(100)).toBe('100 B');
  expect(humanFileSize(1024)).toBe('1.0 KB');
  expect(humanFileSize(1024 * 1000)).toBe('1.0 MB');
  expect(humanFileSize(1024 * 1000 * 1000)).toBe('1.0 GB');
  expect(humanFileSize(1024 * 1000 * 1000 * 1000)).toBe('1.0 TB');
  expect(humanFileSize(1024 * 1000 * 1000 * 1000 * 1000)).toBe('1.0 PB');

  expect(humanFileSize(100, false)).toBe('100 B');
  expect(humanFileSize(1024, false)).toBe('1.0 KiB');
  expect(humanFileSize(1024 * 1000, false)).toBe('1000.0 KiB');
  expect(humanFileSize(1024 * 1000 * 1000, false)).toBe('976.6 MiB');
  expect(humanFileSize(1024 * 1000 * 1000 * 1000, false)).toBe('953.7 GiB');
  expect(humanFileSize(1024 * 1000 * 1000 * 1000 * 1000, false)).toBe('931.3 TiB');
});

it('getFileInfoByFilePath', () => {
  expect(getFileInfoByFilePath('main.js')).toEqual({
    parentPath: '',
    fileName: 'main.js',
    fileExt: 'js',
  });
  expect(getFileInfoByFilePath('leader/main.js')).toEqual({
    parentPath: 'leader',
    fileName: 'main.js',
    fileExt: 'js',
  });
  expect(getFileInfoByFilePath('leader/folder/main.js')).toEqual({
    parentPath: 'leader/folder',
    fileName: 'main.js',
    fileExt: 'js',
  });
  expect(getFileInfoByFilePath('main')).toEqual({
    parentPath: '',
    fileName: 'main',
    fileExt: '',
  });
  expect(getFileInfoByFilePath('')).toEqual({
    parentPath: '',
    fileName: '',
    fileExt: '',
  });
});
it('buildRelativePath', () => {
  expect(
    buildRelativePath({
      path: 'folder',
      filename: 'a.js',
    }),
  ).toBe('folder/a.js');
  expect(
    buildRelativePath({
      path: '',
      filename: 'a.js',
    }),
  ).toBe('a.js');
  expect(
    buildRelativePath({
      path: '.',
      filename: 'a.js',
    }),
  ).toBe('a.js');
  expect(
    buildRelativePath({
      path: 'a/b/c/d',
      filename: 'e.js',
    }),
  ).toBe('a/b/c/d/e.js');

  expect(
    buildRelativePath({
      path: 'a/b/c/d/',
      filename: 'e.js',
    }),
  ).toBe('a/b/c/d/e.js');
  expect(
    buildRelativePath({
      path: 'a/b/c/d//////',
      filename: 'e.js',
    }),
  ).toBe('a/b/c/d/e.js');
  expect(
    buildRelativePath({
      path: '//////',
      filename: 'e.js',
    }),
  ).toBe('e.js');
  expect(
    buildRelativePath({
      path: './/////',
      filename: 'e.js',
    }),
  ).toBe('e.js');
  expect(
    buildRelativePath({
      path: 'a//////',
      filename: 'e.js',
    }),
  ).toBe('a/e.js');
});
