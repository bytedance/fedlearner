import { isNil, isUndefined, omitBy, snakeCase } from 'lodash-es';

/* istanbul ignore next */
export function removeUndefined(values: object) {
  return omitBy(values, isUndefined);
}

/** Remove keys of which value is null, undefined or '' */
export function removeFalsy(values: object) {
  return omitBy(values, (v) => {
    return isNil(v) || v === '';
  });
}

/** Remove keys starts with _underscore */
export function removePrivate<T = object>(values: T): T {
  return (omitBy((values as unknown) as object, (_, key) => key.startsWith('_')) as unknown) as T;
}

/**
 * Transform all keys of the object to snake_case
 * in line with backend definitions
 */
export function transformKeysToSnakeCase(values: object) {
  return Object.entries(values).reduce((ret, [key, val]) => {
    ret[snakeCase(key)] = val;
    return ret;
  }, {} as Record<string, any>);
}

export function binarizeBoolean(values: object) {
  return Object.entries(values).reduce((ret, [key, val]) => {
    if (typeof val === 'boolean') {
      ret[key] = Number(val);
    } else {
      ret[key] = val;
    }

    return ret;
  }, {} as Record<string, any>);
}

export function record<O = Object, V = any>(obj: O, targetValue: V): Record<keyof O, V> {
  return Object.entries(obj).reduce((ret, [key, val]) => {
    ret[key] = targetValue;
    return ret;
  }, {} as any);
}
