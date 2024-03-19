// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
import 'jest-styled-components';

/**
 * Since i18next doesn't support jest environment
 * we did a mock here for unit tests
 */
jest.mock('i18next', () => ({
  use: () => {
    return {
      init() {
        return { t: (k: any) => k, on: () => {} };
      },
    };
  },
  t: (k: any) => k,
  useTranslation: () => ({
    t: (k: any) => k,
  }),
}));

Object.defineProperty(window, 'matchMedia', {
  value: () => {
    return {
      matches: false,
      addListener: () => {},
      removeListener: () => {},
    };
  },
});
