import { decodeBase64 } from './base64';

describe('decode base64', () => {
  it('decodeBase64', () => {
    const cases = [
      {
        i: 'hello world!',
        o: 'hello world!',
      },
      {
        i: 'aGVsbG8gd29ybGQh',
        o: 'hello world!',
      },
      {
        i: 'YUdWc2JHOGdkMjl5YkdRaA==',
        o: 'aGVsbG8gd29ybGQh',
      },
      {
        i: 'JUU0JUJEJUEwJUU1JUE1JUJEJTIwd29ybGQh',
        o: '你好 world!',
      },
      {
        i: '',
        o: '',
      },
    ];
    cases.forEach(({ i, o }) => {
      expect(decodeBase64(i)).toBe(o);
    });

    // Mock fake error
    const decodeURIComponentSpy = jest
      .spyOn(window, 'decodeURIComponent')
      .mockImplementation(() => {
        throw new Error('fake error');
      });
    expect(decodeBase64('aGVsbG8gd29ybGQh')).toBe('');
    decodeURIComponentSpy.mockRestore();
  });
});
