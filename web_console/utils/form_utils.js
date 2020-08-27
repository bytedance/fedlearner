/**
 * fill a json object with given path
 * path rules:
 * - `path.of.some.key` will make obj.path.of.some.key === value
 * - `array[].key` will make obj.array[0].key === value
 */
export const fillJSON = (container, path, value) => {
  let containerIsArray = Array.isArray(container)
  if (typeof path === 'string') {
    path = path.split('.')
  }
  if (path.length === 1) {
    if (containerIsArray) {
      container[0]
        ? container[0][path[0]]= value
        : container[0] = { [path[0]]: value }
    } else {
      container[path[0]] = value
    }
    return
  }
  let currPath
  if (container[path[0]] === undefined) {
    if (path[0].endsWith('[]')) {
      currPath = path[0].replace('[]', '')
      container[currPath] = []
    } else {
      container[path[0]] = {}
      currPath = path[0]
    }
  } else {
    currPath = path[0]
  }
  fillJSON(container[currPath], path.slice(1), value)
}

/**
 * return value of an json object with given path
 * path rules:
 * - `path.of.some.key` will return obj.path.some.key
 * - `array[].key` will return obj.array[0].key
 */
export const getValueFromJson = (data, path) => {
  if (typeof path === 'string') {
    path = path.split('.')
  }
  if (path.length === 1) {
    return data[path[0]]
  }
  const currPathIsArray = path[0].endsWith('[]')
  let currPath = path[0].replace('[]', '')
  let nextLayer = currPathIsArray ? data[currPath][0] : data[path[0]]
  if (nextLayer === undefined) return undefined
  return getValueFromJson(nextLayer, path.slice(1))
}

export function getParsedValueFromData (data, field) {
  let value = (data && data[field.key]) || (field.emptyDefault || '')
  if (['json', 'name-value'].some(el => el === field.type)) {
    value = JSON.parse(value)
  }
  return value
}