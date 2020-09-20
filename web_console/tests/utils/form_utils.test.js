import { fillJSON } from '../../utils/form_utils'
const assert = require('assert');

describe('form_utils', () => {
  it('should create object with path', () => {
    let path = 'foo.bar.baz'
    let value = 1
    let obj = {}
    fillJSON(obj, path, value)
    assert.deepStrictEqual(obj, {
      foo: {
        bar: {
          baz: value
        }
      }
    })
  })

  it('should fill in array[0]', () => {
    let path = 'foo.bar[].baz.qux'
    let value = 1
    let obj = {}
    fillJSON(obj, path, value)
    assert.deepStrictEqual(obj, {
      foo: {
        bar: [
          {baz: { qux: value }}
        ]
      }
    })
  })

  it('should fill all in array[0]', () => {
    let paths = [
      'foo.bar[].baz.qux',
      'foo.bar[].baz.quux',
    ]
    let value = 1
    let obj = {}
    paths.forEach(path => fillJSON(obj, path, value))
    assert.deepStrictEqual(obj, {
      foo: {
        bar: [
          {baz: { qux: value, quux: value }}
        ]
      }
    })
  })

  it('test push new object and insert to the first item', () => {
    let paths = [
      'foo.bar[].baz.qux',
      'foo.bar[-1].baz.quux',
    ]
    let value = 1
    let obj = {}
    paths.forEach(path => fillJSON(obj, path, value))
    assert.deepStrictEqual(obj, {
      foo: {
        bar: [
          { baz: { qux: value} },
          { baz: { quux: value} },
        ]
      }
    })
  })

  it('test multi push', () => {
    let paths = [
      'foo.bar[].baz[].qux',
      'foo.bar[].baz[-1].quux',
    ]
    let value = 1
    let obj = {}
    paths.forEach(path => fillJSON(obj, path, value))
    assert.deepStrictEqual(obj, { 
      foo: {
        bar: [
          { baz: [{ qux: value }, { quux: value } ] },
        ]
      }
    })
  })
})

describe('filter value', () => {
  it('should filter undefined', () => {
    let arr = [1, 2, undefined, 3, undefined]
    filterArrayValue(arr)

    assert.deepStrictEqual(arr, [1, 2, 3])
  })

  it('should filter value', () => {
    let arr = [1, 2, undefined, 3, undefined]
    filterArrayValue(arr, 3)

    assert.deepStrictEqual(arr, [1, 2, undefined, undefined])
  })
})