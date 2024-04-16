import { message } from 'antd';
import { validatePassword } from './validator';

describe('Password validation', () => {
  it('validatePassword', () => {
    const cases = [
      {
        // Empty
        i: '',
        o: false,
      },
      {
        // Too short
        i: 'A@34567',
        o: false,
      },
      {
        // Too loooong
        i: 'A!3451234512345123450',
        o: false,
      },
      {
        i: 'Fl@1234!',
        o: true,
      },
    ];

    cases.forEach(async ({ i, o }) => {
      expect(
        await validatePassword(i, { message: 'Wrong password' }).catch((err) => {
          expect(err.message).toBe('Wrong password');
          return false;
        }),
      ).toBe(o);
    });
  });
});
