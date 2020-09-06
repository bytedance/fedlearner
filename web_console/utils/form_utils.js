/**
 * fill a json object with given path
 * path rules:
 * - `path.of.some.key` will make obj.path.of.some.key === value
 * - `array[].key` will always make obj.array[0].key === value
 * - `array[-1].key` will push a new object to array
 * TODO: `array[],[]key`
 */
export function fillJSON(container, path, value) {
  let paths = path.split('.')
  let currLayer = container

  let cursor = 0
  while (cursor < paths.length) {
    let arrayMarks = new RegExp(/\[([\s\S]*?)\]$/).exec(paths[cursor])
    let isArray = !!arrayMarks
    let currKey = isArray ? paths[cursor].replace(arrayMarks[0], '') : paths[cursor]

    // insert value
    if (cursor === paths.length - 1) {
      currLayer[paths[cursor]] = value
      break
    }

    // handle layer
    if (isArray) {
      let posToInsert = parseInt(arrayMarks[1] || '0')

      if (!currLayer[currKey]) { currLayer[currKey] = [] }

      switch (posToInsert) {
        case 0:
          currLayer[currKey][0] = currLayer[currKey][0] || {}
          currLayer = currLayer[currKey][0]
          break
        case -1:
          let newObj = {}
          currLayer[currKey] = currLayer[currKey].concat(newObj)
          currLayer = newObj
      }
    } else {
      if (!currLayer[currKey]) { currLayer[currKey] = {} }

      currLayer = currLayer[currKey]
    }
    cursor++
  }
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
  let value = (data && data[field.key]) || ''
  if (['json', 'name-value'].some(el => el === field.type)) {
    value = value ? JSON.parse(value) : field.emptyDefault || {}
  }
  return value
}