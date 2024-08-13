# DoubleSelect

双下拉框

> 注意 ⚠️: 因为 `<DoubleSelect.ModelSelect/>` 内部引入了 `react-query` 相关的函数，所以 Demo 代码中用 `<QueryClientProvider/>` 作为根组件，防止报错。

<API src="components/DoubleSelect/index.tsx" exports='["default"]'></API>

### OptionItem

每个 item 格式定义

```ts | pure
type OptionItem = {
  /** Display label */
  label: string | number;
  /** Form value */
  value: any;
  disabled?: boolean;
};
```

<API src="components/DoubleSelect/index.tsx" exports='["ModelSelect"]'></API>

## 常规用法

```tsx
import React, { useState } from 'react';
import DoubleSelect from 'components/DoubleSelect';

const leftOptionList = [
  {
    label: 'left label1',
    value: 'left value1',
  },
  {
    label: 'left label2',
    value: 'left value2',
  },
  {
    label: 'left label3',
    value: 'left value3',
  },
];

const rightOptionList = [
  {
    label: 'right label1',
    value: 'right value1',
  },
  {
    label: 'right label2',
    value: 'right value2',
  },
  {
    label: 'right label3',
    value: 'right value3',
  },
];

export default () => {
  const [value, setValue] = useState();
  return (
    <>
      <DoubleSelect
        value={value}
        leftOptionList={leftOptionList}
        rightOptionList={rightOptionList}
        onChange={(val) => {
          console.log(val);
          setValue(val);
        }}
      />
    </>
  );
};
```

## IsClearRightValueAfterLeftSelectChange

isClearRightValueAfterLeftSelectChange = true

左边的下拉框选中后，会清空右边的下拉框的 value

```tsx
import React, { useState } from 'react';
import DoubleSelect from 'components/DoubleSelect';

const leftOptionList = [
  {
    label: 'left label1',
    value: 'left value1',
  },
  {
    label: 'left label2',
    value: 'left value2',
  },
  {
    label: 'left label3',
    value: 'left value3',
  },
];

const rightOptionList = [
  {
    label: 'right label1',
    value: 'right value1',
  },
  {
    label: 'right label2',
    value: 'right value2',
  },
  {
    label: 'right label3',
    value: 'right value3',
  },
];

export default () => {
  const [value, setValue] = useState();
  return (
    <>
      <DoubleSelect
        value={value}
        leftOptionList={leftOptionList}
        rightOptionList={rightOptionList}
        onChange={(val) => {
          console.log(val);
          setValue(val);
        }}
        isClearRightValueAfterLeftSelectChange={true}
      />
    </>
  );
};
```

## LeftLabel/RightLabel

```tsx
import React, { useState } from 'react';
import DoubleSelect from 'components/DoubleSelect';

const leftOptionList = [
  {
    label: 'left label1',
    value: 'left value1',
  },
  {
    label: 'left label2',
    value: 'left value2',
  },
  {
    label: 'left label3',
    value: 'left value3',
  },
];

const rightOptionList = [
  {
    label: 'right label1',
    value: 'right value1',
  },
  {
    label: 'right label2',
    value: 'right value2',
  },
  {
    label: 'right label3',
    value: 'right value3',
  },
];

export default () => {
  const [value, setValue] = useState();
  return (
    <>
      <DoubleSelect
        value={value}
        leftOptionList={leftOptionList}
        rightOptionList={rightOptionList}
        onChange={(val) => {
          console.log(val);
          setValue(val);
        }}
        leftLabel="leftLabel"
        rightLabel="rightLabel"
      />
    </>
  );
};
```

## 子组件

### ModelSelect

`ModelSelect` 内部封装了获取模型集列表（下拉框）/模型列表（右下拉框）的网络请求

isDisabledLinkage = false，联动，会根据选中的模型集来过滤出模型列表，最终呈现在右下拉框上

```tsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';
import DoubleSelect from 'components/DoubleSelect';

export default () => {
  const [value, setValue] = useState();
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DoubleSelect.ModelSelect
          value={value}
          onChange={(val) => {
            console.log(val);
            setValue(val);
          }}
          leftField="model_set_id"
          rightField="model_id"
          leftLabel="模型集"
          rightLabel="模型"
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

isDisabledLinkage = true, 禁用联动，右下拉框直接显示所有模型

```tsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';
import DoubleSelect from 'components/DoubleSelect';

export default () => {
  const [value, setValue] = useState();
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DoubleSelect.ModelSelect
          value={value}
          onChange={(val) => {
            console.log(val);
            setValue(val);
          }}
          leftField="model_set_id"
          rightField="model_id"
          leftLabel="模型集"
          rightLabel="模型"
          isDisabledLinkage={true}
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

### AlgorithmSelect

`AlgorithmSelect` 内部封装了获取算法项目（下拉框）/算法版本（右下拉框）的网络请求,支持传递 `algorithmProjectTypeList` 数组来过滤算法类型，类型为 `EnumAlgorithmProjectType`

value 的格式为 `AlgorithmSelectValue`

选中算法版本后，如果该算法含有超参数的话，会展示超参数列表，并支持修改该超参数的 value

```ts
type AlgorithmSelectValue = {
  algorithmProjectId: ID;
  algorithmId: ID;
  config?: AlgorithmParameter[];
  path?: string;
};

type AlgorithmParameter = {
  name: string;
  value: string;
  required: boolean;
  display_name: string;
  comment: string;
  value_type: ValueType;
};

enum EnumAlgorithmProjectType {
  UNSPECIFIED = 'UNSPECIFIED',
  TREE_VERTICAL = 'TREE_VERTICAL',
  TREE_HORIZONTAL = 'TREE_HORIZONTAL',
  NN_VERTICAL = 'NN_VERTICAL',
  NN_HORIZONTAL = 'NN_HORIZONTAL',
  NN_LOCAL = 'NN_LOCAL',
}
```

```tsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';
import DoubleSelect from 'components/DoubleSelect';

export default () => {
  const [value, setValue] = useState();
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DoubleSelect.AlgorithmSelect
          value={value}
          onChange={(val) => {
            console.log(val);
            setValue(val);
          }}
          leftLabel="算法项目"
          rightLabel="算法版本"
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

### ModelJobGroupSelect

`ModelJobGroupSelect` 内部封装了获取模型评估和预测的 Job 的网络请求，支持传入 `type` 来根据算法类型过滤 Job Group 列表。

`type` 的类型为 `'NN_VERTICAL' | 'NN_HORIZONTAL'`。

一个简单的例子：

```tsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';
import DoubleSelect from 'components/DoubleSelect';

export default () => {
  const [value, setValue] = useState();
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DoubleSelect.ModelJobGroupSelect
          type="NN_VERTICAL"
          value={value}
          onChange={(val) => {
            console.log(val);
            setValue(val);
          }}
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
