import { I18nMessageModule, separateLng } from './helpers';

const mockModule: I18nMessageModule = {
  a: { zh: '1', en: '2' },
  b: { zh: '3' },
};

describe('Separate ZH and EN messages from module', () => {
  it('Should works fine', () => {
    expect(separateLng(mockModule)).toEqual({
      zh: {
        a: '1',
        b: '3',
      },
      en: {
        a: '2',
        b: null,
      },
    });
  });
});
