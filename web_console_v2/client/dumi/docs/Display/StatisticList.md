# StatisticList

显示统计数字列表的组件，基于 [Arco Card](https://arco.design/react/components/card#api) 和 [TitleWithIcon](/display/title-with-icon) 封装

<API src="components/StatisticList/index.tsx" exports='["default"]'></API>

```tsx | pure
type OptionItem = {
  /** Display title */
  text: string;
  /** Display value */
  value: string | number;
  /** Tip */
  tip?: string;
};
```

## 常规使用

```tsx
import React from 'react';
import StatisticList from 'components/StatisticList';

const data = [
  {
    text: 'AUC ROC',
    value: 0.75316,
    tip: 'AUC ROC',
  },
  {
    text: 'Accuracy',
    value: 0.75316,
    tip: 'Accuracy',
  },
  {
    text: 'Precision',
    value: 0.5,
    tip: 'Precision',
  },
  {
    text: 'Recall',
    value: 0.8,
    tip: 'Recall',
  },
  {
    text: 'F1 score',
    value: 0.8,
  },
  {
    text: 'Log loss',
    value: 0.7,
  },
  {
    text: 'Metrics1',
    value: 0.12345,
  },
  {
    text: 'Metrics2',
    value: 0.54321,
  },
  {
    text: 'Metrics3',
    value: 0.888888,
  },
];

export default () => (
  <div>
    <div>cols = 6</div>
    <StatisticList data={data} cols={6} />
    <div>cols = 3</div>
    <StatisticList data={data} cols={3} />
  </div>
);
```

## 子组件

### NumberItem

```tsx | pure
type NumberItemProps = {
  value?: any;
  className?: string;
} & TitleWithIconProps;
```

```jsx
import React from 'react';
import { NumberItem } from 'components/StatisticList';

export default () => [
  <NumberItem value={0.6} title="with tip" tip="tip" />,
  <br />,
  <NumberItem value={0.5} title="no tip" />,
];
```
