import { isUndefined, omitBy } from 'lodash'
/* istanbul ignore next */
export function removeUndefinedKeys(values: object) {
  return omitBy(values, isUndefined)
}

/** Remove keys starts with _underscore */
export function removePrivateKeys(values: object) {
  return omitBy(values, (_, key) => key.startsWith('_'))
}
