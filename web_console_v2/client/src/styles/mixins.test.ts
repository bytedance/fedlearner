import { commonTransition } from './mixins'
import defaultTheme from './_theme'

describe('Common transition mixin', () => {
  it('Should works fine', () => {
    const t = defaultTheme.commonTiming
    const cases = [
      { i: undefined, o: `transition: 0.2s ${t}` },
      { i: 'color', o: `transition: color 0.2s ${t}` },
      {
        i: ['color', 'opacity'],
        o: `transition: color 0.2s ${t},opacity 0.2s ${t}`,
      },
    ]

    cases.forEach(({ i, o }) => {
      expect(commonTransition(i).trim()).toBe(o)
    })
  })
})
