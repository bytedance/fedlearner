import debounce from 'debounce-promise';
import i18n from 'i18n';

import { fetchWorkflowList } from 'services/workflow';

export const validPasswordPattern = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()_=+|{};:'",<.>/?~])[A-Za-z\d!@#$%^&*()_=+|{};:'",<.>/?~]{8,20}$/i;

export async function validatePassword(
  value: string,
  options: { message: string } = { message: i18n.t('users.placeholder_password_message') },
) {
  if (validPasswordPattern.test(value)) {
    return true;
  }

  throw new Error(options.message);
}

function generateInputPattern(maxSize: number) {
  return new RegExp(
    `^[a-zA-Z0-9\u4e00-\u9fa5][a-zA-Z0-9\u4e00-\u9fa5-_@.]{0,${
      maxSize - 2
    }}[a-zA-Z0-9\u4e00-\u9fa5]$|^[a-zA-Z0-9\u4e00-\u9fa5]{1}$`,
  );
}

function generateParticipantValidName(maxSize: number) {
  return new RegExp(
    `^[a-zA-Z0-9\u4e00-\u9fa5][a-zA-Z0-9\u4e00-\u9fa5-_]{0,${
      maxSize - 2
    }}[a-zA-Z0-9\u4e00-\u9fa5]$|^[a-zA-Z0-9\u4e00-\u9fa5]{1}$`,
  );
}

/**
 * Support uppercase and lowercase letters, numbers, Chinese, "_" and "-" characters,
 * can only start/end with uppercase and lowercase letters, numbers or Chinese,
 * and no more than 63 characters
 */
export const validNamePattern = generateInputPattern(63);

export const validParticipantNamePattern = generateParticipantValidName(63);

export function isValidName(str: string) {
  return validNamePattern.test(str);
}

export const validCommentPattern = generateInputPattern(100);

export const MAX_COMMENT_LENGTH = 200;

/**
 * limit from k8s
 */
export const jobNamePattern = /^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$/;
export function isValidJobName(str: string) {
  return str.length <= 24 && jobNamePattern.test(str);
}

/**
 * valid format: xxxm, x is number
 *
 * @example
 * 100m
 */
export const validCpuPattern = /^\d+m$/;

/**
 * valid format: xxxMi or xxxGi, x is number
 *
 * @example
 * 100Mi,100Gi
 */
export const validMemoryPattern = /^\d+(Mi|Gi)$/;

/**
 * valid format: xxxm, x is number
 *
 * @param cpu string
 * @returns boolean
 * @example
 * 100m
 */
export function isValidCpu(cpu: string) {
  return validCpuPattern.test(cpu);
}
/**
 * valid format: xxxMi or xxxGi
 *
 * @param memory string
 * @returns boolean
 * @example
 * 100Mi,100Gi
 */
export function isValidMemory(memory: string) {
  return validMemoryPattern.test(memory);
}

/**
 * valid is workflow name unique
 * @param workflowName string
 * @returns Promise<string | null>
 */
export async function isWorkflowNameUniq(workflowName: string, callback: (error?: string) => void) {
  if (!workflowName) {
    return;
  }

  try {
    // filter by workflowName
    const resp = await fetchWorkflowList({
      name: workflowName,
    });
    const { data } = resp;
    if (data && data.length > 0) {
      callback('系统中存在同名的工作流，请更换名称');
    }
    return;
  } catch (error) {
    return Promise.reject(String(error));
  }
}

/* istanbul ignore next */
export const isWorkflowNameUniqWithDebounce = debounce(
  async (value: any, callback: (error?: string) => void) => {
    return isWorkflowNameUniq(value, callback);
  },
  500,
);

// https://github.com/any86/any-rule#email%E9%82%AE%E7%AE%B1
export const validEmailPattern = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
export function isValidEmail(email: string) {
  return validEmailPattern.test(email);
}

/**
 * valid string is can be parse
 * @param value string
 * @returns Promise<string | null>
 */
export function isStringCanBeParsed(value: string, valueType: 'LIST' | 'OBJECT') {
  try {
    JSON.parse(value);
    return Promise.resolve();
  } catch (error) {
    return Promise.reject(
      i18n.t('settings.msg_wrong_format', {
        type: valueType,
      }),
    );
  }
}
