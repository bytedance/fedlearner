# MultiSelect

基于 [Arco Select](xxx) 封装，面向 UX 设计图的多选下拉框，具有全选功能，并显示当前选中的个数

<API src="components/MultiSelect/index.tsx"></API>

也支持传入 [Arco Select](xxx) 原有的 props

### Option

每个 item 格式定义

```jsx | pure
type OptionItem = {
  /** Display label */
  label: string,
  /** Form value */
  value: any,
};
```

## 常规用法

```jsx
import React, { useState } from 'react';
import i18n from '../../../src/i18n/index.ts';
import MultiSelect from 'components/MultiSelect';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState([]);
  return (
    <>
      <MultiSelect
        style={{ width: 300 }}
        placeholder="placeholder"
        optionList={options || []}
        value={value}
        onChange={(val) => {
          setValue(val);
        }}
        allowClear
      />
    </>
  );
};
```

## IsHideHeader

```jsx
import React, { useState } from 'react';
import i18n from '../../../src/i18n/index.ts';
import MultiSelect from 'components/MultiSelect';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState([]);
  return (
    <>
      <MultiSelect
        style={{ width: 300 }}
        placeholder="placeholder"
        optionList={options || []}
        value={value}
        onChange={(val) => {
          setValue(val);
        }}
        allowClear
        isHideHeader={true}
      />
    </>
  );
};
```

## IsHideIndex

```jsx
import React, { useState } from 'react';
import i18n from '../../../src/i18n/index.ts';
import MultiSelect from 'components/MultiSelect';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState([]);
  return (
    <>
      <MultiSelect
        style={{ width: 300 }}
        placeholder="placeholder"
        optionList={options || []}
        value={value}
        onChange={(val) => {
          setValue(val);
        }}
        allowClear
        isHideIndex={true}
      />
    </>
  );
};
```
