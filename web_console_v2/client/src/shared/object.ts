import { isNil, isUndefined, omitBy } from 'lodash'

/* istanbul ignore next */
export function removeUndefined(values: object) {
  return omitBy(values, isUndefined)
}

/** Remove keys of which value is null, undefined or '' */
export function removeFalsy(values: object) {
  return omitBy(values, (v) => {
    return isNil(v) || v === ''
  })
}

/** Remove keys starts with _underscore */
export function removePrivate(values: object) {
  return omitBy(values, (_, key) => key.startsWith('_'))
}
