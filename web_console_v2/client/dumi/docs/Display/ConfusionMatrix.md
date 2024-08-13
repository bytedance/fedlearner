# ConfusionMatrix

混淆矩阵

从上到下，从左到右，分别为 `tp`,`fn`,`fp`,`tn`

<API src="components/ConfusionMatrix/index.tsx" exports='["default"]'></API>

## 常规使用

```tsx
import React from 'react';
import ConfusionMatrix from 'components/ConfusionMatrix';

export default () => (
  <ConfusionMatrix title="Confusion matrix" tip="Confusion matrix" valueList={[10, 40, 35, 15]} />
);
```

## 归一化相关配置

默认会根据`valueList`和`formatPercentValueList`得到 `percentValueList`，用来显示归一化之后的数据，可以参考[常规使用](#常规使用)

默认 `formatPercentValueList` 的函数

```tsx | pure
export const defaultFormatPercentValueList = (valueList: number[]) => {
  const total = valueList.reduce((acc: number, cur: number) => acc + cur, 0);
  return valueList.map((num) => ((num / total) * 100).toFixed(2) + '%');
};
```

强行传入的 `percentValueList` 的话，就只会显示 `percentValueList`

```tsx
import React from 'react';
import ConfusionMatrix from 'components/ConfusionMatrix';

export default () => (
  <ConfusionMatrix
    valueList={[10, 40, 35, 15]}
    percentValueList={['10.00%', '40.00%', '35.00%', '15.00%']}
  />
);
```

## isEmpty

强行显示暂无数据布局

```tsx
import React from 'react';
import ConfusionMatrix from 'components/ConfusionMatrix';

export default () => <ConfusionMatrix isEmpty={true} />;
```
