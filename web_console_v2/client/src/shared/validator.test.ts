import {
  validatePassword,
  validNamePattern,
  validEmailPattern,
  isValidJobName,
  isValidCpu,
  isValidMemory,
  isWorkflowNameUniq,
  isValidName,
  isValidEmail,
  isStringCanBeParsed,
} from './validator';
import * as api from 'services/workflow';
import { newlyCreated } from 'services/mocks/v2/workflows/examples';

jest.mock('services/workflow');

const mockApi = api as jest.Mocked<typeof api>;

const validNameCases = [
  {
    // Empty
    i: '',
    o: false,
  },
  {
    // Single lowercase char
    i: 'a',
    o: true,
  },
  {
    // Single uppercase char
    i: 'A',
    o: true,
  },
  {
    // Single number char
    i: '0',
    o: true,
  },
  {
    // Single chinese char
    i: '中',
    o: true,
  },
  {
    // Single _ char
    i: '_',
    o: false,
  },
  {
    i: 'a_',
    o: false,
  },
  {
    i: 'A_',
    o: false,
  },
  {
    i: '0_',
    o: false,
  },
  {
    i: '中_',
    o: false,
  },
  {
    i: '__',
    o: false,
  },
  {
    i: 'a_A',
    o: true,
  },
  {
    i: 'A_a',
    o: true,
  },
  {
    i: '0_a',
    o: true,
  },
  {
    i: '中_a',
    o: true,
  },
  {
    i: '__a',
    o: false,
  },
];

describe('Password validation', () => {
  it('validatePassword', async () => {
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

    await expect(validatePassword('')).rejects.toThrow('users.placeholder_password_message');
  });
});

describe('Name validation', () => {
  it('validNamePattern', () => {
    validNameCases.forEach(({ i, o }) => {
      expect(validNamePattern.test(i)).toBe(o);
    });
  });

  it('isValidName', () => {
    validNameCases.forEach(({ i, o }) => {
      expect(isValidName(i)).toBe(o);
    });
  });

  it('isValidJobName', () => {
    expect(isValidJobName('')).toBe(false);
    expect(isValidJobName('嗷嗷嗷')).toBe(false);
    expect(isValidJobName('jobjobjobjobjobjobjobjob')).toBe(true); // 24 limit
    expect(
      isValidJobName(
        'jobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjobjob',
      ),
    ).toBe(false);
    expect(isValidJobName('-_aaa112399AAd')).toBe(false);
    expect(isValidJobName('-aaa112399AAd')).toBe(false);
    expect(isValidJobName('uuid-jobname')).toBe(true);
    expect(isValidJobName('-jobname')).toBe(false);
    expect(isValidJobName('_aaa112399AAd')).toBe(false);
    expect(isValidJobName('A')).toBe(false);
    expect(isValidJobName('aaaA')).toBe(false);
    expect(isValidJobName('aaa.test')).toBe(true);
  });

  it('isWorkflowNameUniq', async () => {
    try {
      const callback = (error?: string) => {
        return error;
      };
      // Empty input string will return undefiend
      await expect(isWorkflowNameUniq('', callback)).resolves.toBeUndefined();
      // Because api no mock resolve value, so it will throw error
      await expect(isWorkflowNameUniq('1', callback)).rejects.toMatch('TypeError');

      mockApi.fetchWorkflowList.mockResolvedValueOnce({ data: [] });
      const resolvedValue = await isWorkflowNameUniq('workflowName1', callback);
      expect(resolvedValue).toBeUndefined();

      mockApi.fetchWorkflowList.mockResolvedValueOnce({ data: [newlyCreated] });
      await isWorkflowNameUniq('workflowName1', callback).catch((error) => {
        expect(error).toMatch('workflow.msg_workflow_name_existed');
      });
    } catch (error) {
      return Promise.reject(error);
    }
  });
});

describe('Resource config validation', () => {
  it('isValidCpu', () => {
    expect(isValidCpu('')).toBe(false);
    expect(isValidCpu(' ')).toBe(false);
    expect(isValidCpu('100m')).toBe(true);
    expect(isValidCpu('100M')).toBe(false);
    expect(isValidCpu('100mm')).toBe(false);
    expect(isValidCpu('a100m')).toBe(false);
    expect(isValidCpu('1a00m')).toBe(false);
    expect(isValidCpu('100ma')).toBe(false);
    expect(isValidCpu('m')).toBe(false);
    expect(isValidCpu('M')).toBe(false);
    expect(isValidCpu('100')).toBe(false);
  });
  it('isValidMemory', () => {
    expect(isValidMemory('')).toBe(false);
    expect(isValidMemory(' ')).toBe(false);

    // Gi
    expect(isValidMemory('Gi')).toBe(false);
    expect(isValidMemory('gi')).toBe(false);
    expect(isValidMemory('100')).toBe(false);
    expect(isValidMemory('100Gi')).toBe(true);
    expect(isValidMemory('100gi')).toBe(false);
    expect(isValidMemory('100Gii')).toBe(false);
    expect(isValidMemory('100gii')).toBe(false);
    expect(isValidMemory('a100Gi')).toBe(false);
    expect(isValidMemory('1a00Gi')).toBe(false);
    expect(isValidMemory('100aGi')).toBe(false);
    expect(isValidMemory('100Gai')).toBe(false);

    // Mi
    expect(isValidMemory('Mi')).toBe(false);
    expect(isValidMemory('mi')).toBe(false);
    expect(isValidMemory('100')).toBe(false);
    expect(isValidMemory('100Mi')).toBe(true);
    expect(isValidMemory('100mi')).toBe(false);
    expect(isValidMemory('100Mii')).toBe(false);
    expect(isValidMemory('100mii')).toBe(false);
    expect(isValidMemory('a100Mi')).toBe(false);
    expect(isValidMemory('1a00Mi')).toBe(false);
    expect(isValidMemory('100aMi')).toBe(false);
    expect(isValidMemory('100Mai')).toBe(false);
  });
});

describe('Email validation', () => {
  it('validEmailPattern', () => {
    expect(validEmailPattern.test('')).toBe(false);
    expect(validEmailPattern.test('a')).toBe(false);
    expect(validEmailPattern.test('a@qq.com')).toBe(true);
    expect(validEmailPattern.test('a_?s@qq.com')).toBe(true);
    expect(validEmailPattern.test('a@@qq.com')).toBe(false);
    expect(validEmailPattern.test('a@qqcom')).toBe(false);
    expect(validEmailPattern.test('a@qq.')).toBe(false);
    expect(validEmailPattern.test('aqq.com')).toBe(false);
  });

  it('isValidEmail', () => {
    expect(isValidEmail('')).toBe(false);
    expect(isValidEmail('a')).toBe(false);
    expect(isValidEmail('a@qq.com')).toBe(true);
    expect(isValidEmail('a_?s@qq.com')).toBe(true);
    expect(isValidEmail('a@@qq.com')).toBe(false);
    expect(isValidEmail('a@qqcom')).toBe(false);
    expect(isValidEmail('a@qq.')).toBe(false);
    expect(isValidEmail('aqq.com')).toBe(false);
  });
});

it('isStringCanBeParsed', async () => {
  await expect(isStringCanBeParsed('', 'OBJECT')).rejects.toMatch('msg_wrong_format');
  await expect(isStringCanBeParsed('', 'LIST')).rejects.toMatch('msg_wrong_format');

  await expect(isStringCanBeParsed('cc', 'OBJECT')).rejects.toMatch('msg_wrong_format');
  await expect(isStringCanBeParsed('cc', 'LIST')).rejects.toMatch('msg_wrong_format');

  await expect(isStringCanBeParsed('{}', 'OBJECT')).resolves.toBeUndefined();
  await expect(isStringCanBeParsed('{}', 'LIST')).resolves.toBeUndefined();

  await expect(isStringCanBeParsed('[]', 'OBJECT')).resolves.toBeUndefined();
  await expect(isStringCanBeParsed('[]', 'LIST')).resolves.toBeUndefined();

  const testObjectString = JSON.stringify({ a: 1, b: 2 });
  await expect(isStringCanBeParsed(testObjectString, 'OBJECT')).resolves.toBeUndefined();
  await expect(isStringCanBeParsed(testObjectString, 'LIST')).resolves.toBeUndefined();

  const testArrayString = JSON.stringify([{ a: 1, b: 2 }]);
  await expect(isStringCanBeParsed(testArrayString, 'OBJECT')).resolves.toBeUndefined();
  await expect(isStringCanBeParsed(testArrayString, 'LIST')).resolves.toBeUndefined();

  const testFakeObjectString = '{a:1}';
  await expect(isStringCanBeParsed(testFakeObjectString, 'OBJECT')).rejects.toMatch(
    'msg_wrong_format',
  );
  await expect(isStringCanBeParsed(testFakeObjectString, 'LIST')).rejects.toMatch(
    'msg_wrong_format',
  );

  const testFakeArrayString = '[1],';
  await expect(isStringCanBeParsed(testFakeArrayString, 'OBJECT')).rejects.toMatch(
    'msg_wrong_format',
  );
  await expect(isStringCanBeParsed(testFakeArrayString, 'LIST')).rejects.toMatch(
    'msg_wrong_format',
  );
});
