import { MixinCommonTransition } from './mixins'
import defaultTheme from './_theme'

describe('Common transition mixin', () => {
  it('Should works fine', () => {
    const t = defaultTheme.commonTiming
    const cases = [
      { i: undefined, o: `transition: 0.4s ${t}` },
      { i: 'color', o: `transition: color 0.4s ${t}` },
      {
        i: ['color', 'opacity'],
        o: `transition: color 0.4s ${t},opacity 0.4s ${t}`,
      },
    ]

    cases.forEach(({ i, o }) => {
      expect(MixinCommonTransition(i).trim().replace(/\n/g, '')).toBe(o)
    })
  })
})
