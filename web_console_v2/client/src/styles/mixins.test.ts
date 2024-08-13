import { MixinCommonTransition, MixinSquare, MixinCircle } from './mixins';
import defaultTheme from './theme';

describe('Square and Circle', () => {
  it('Should works fine', () => {
    const square = MixinSquare(30);
    expect(square.includes('width: 30px;')).toBeTruthy();
    expect(square.includes('height: 30px;')).toBeTruthy();

    const circle = MixinCircle(20);
    expect(circle.includes('width: 20px;')).toBeTruthy();
    expect(circle.includes('height: 20px;')).toBeTruthy();
  });
});

describe('Common transition mixin', () => {
  it('Should works fine', () => {
    const t = defaultTheme.commonTiming;
    const cases = [
      { i: undefined, o: `transition: 0.4s ${t};` },
      { i: 'color', o: `transition: color 0.4s ${t};` },
      {
        i: ['color', 'opacity'],
        o: `transition: color 0.4s ${t},opacity 0.4s ${t};`,
      },
    ];

    cases.forEach(({ i, o }) => {
      expect(MixinCommonTransition(i).trim().replace(/\n/g, '')).toBe(o);
    });

    expect(MixinCommonTransition('padding', 0.2).trim()).toBe(`transition: padding 0.2s ${t};`);
  });
});
