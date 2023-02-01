# FeatureImportance

显示 FeatureImportance 的组件

<API src="components/FeatureImportance/index.tsx" exports='["default"]'></API>

```tsx | pure
type Item = {
  label: string;
  value: any;
};
```

## 常规使用

```tsx
import React from 'react';
import FeatureImportance from 'components/FeatureImportance';

const data = [
  { label: 'test_13', value: 0.7 },
  { label: 'test_14', value: 0.6 },
  { label: 'test_15', value: 0.5 },
  { label: 'test_16', value: 0.4 },
  { label: 'peer-1', value: 0.3 },
  { label: 'peer-2', value: 0.3 },
  { label: 'age', value: 0.3 },
  { label: 'overall_score', value: 0.3 },
  { label: 'test_17', value: 0.3 },
  { label: 'salary', value: 0.2 },
  { label: 'test_19', value: 0.2 },
  { label: 'peer-3', value: 0.1 },
  { label: 'education', value: 0.1 },
  { label: 'height', value: 0.1 },
  { label: 'peer-0', value: 0.08 },
];

export default () => (
  <div>
    <FeatureImportance valueList={data} />
  </div>
);
```

## xTickFormatter

可以指定 x 轴的格式化函数，例如可以把 x 轴显示为百分比

默认 `xTickFormatter` 的函数

```tsx | pure
function defaultXTickFormatter(val: any) {
  return val;
}
```

```tsx
import React from 'react';
import FeatureImportance from 'components/FeatureImportance';

const data = [
  { label: 'test_13', value: 0.7 },
  { label: 'test_14', value: 0.6 },
  { label: 'test_15', value: 0.5 },
  { label: 'test_16', value: 0.4 },
  { label: 'peer-1', value: 0.3 },
  { label: 'peer-2', value: 0.3 },
  { label: 'age', value: 0.3 },
  { label: 'overall_score', value: 0.3 },
  { label: 'test_17', value: 0.3 },
  { label: 'salary', value: 0.2 },
  { label: 'test_19', value: 0.2 },
  { label: 'peer-3', value: 0.1 },
  { label: 'education', value: 0.1 },
  { label: 'height', value: 0.1 },
  { label: 'peer-0', value: 0.08 },
];

export default () => (
  <div>
    <FeatureImportance valueList={data} xTipFormatter={(value: any) => `${value * 100}%`} />
  </div>
);
```
