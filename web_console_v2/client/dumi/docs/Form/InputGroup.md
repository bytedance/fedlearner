# InputGroup

栅格布局的表单组

<API src="components/InputGroup/index.tsx"></API>

### TColumn

```typescript
interface TColumn {
  /** INPUT for input[type="text"], INPUT_NUMBER for input[type="number"], TEXT for plain value display */
  type: 'INPUT' | 'INPUT_NUMBER' | 'TEXT';
  /** column title */
  title: string;
  /** column tooltip */
  tooltip?: string;
  /** column data field name */
  dataIndex: string;
  /** column width proportion (the total is 24) */
  span: number;
  /** the placeholder of current column's input item */
  placeholder?: string;
  /** the unit text of current column's input item */
  unitLabel?: string;
  /** validation rules of current column's input item */
  rules?: RulesProps[];
  /** precision of number(when type is 'INPUT_NUMBER') */
  precision?: number;
  /** minimum value of number(when type is 'INPUT_NUMBER') */
  min?: number;
  /** maximum value of number(when type is 'INPUT_NUMBER') */
  max?: number;
  /** it is the same with InputNumber of ArcoDesign(when type is 'INPUT_NUMBER') */
  mode?: 'button' | 'embed';
  /** provide a way to process output value, the type of output would be limited to the same type of value. */
  formatValue?: () => string | number;
  /** disabled component */
  disabled?: boolean;
}
```

> 各个列的 span 总和应该等于 24，否则会抛出一个 error。这也是 ArcoDesign 栅格系统的每行 span 总和。

## 常规用法

用 `columns` 定义列，用 `onChange` 监听值变化。

```jsx
import React from 'react';
import InputGroup from 'components/InputGroup';

const columns = [
  {
    title: 'first name',
    dataIndex: 'firstName',
    span: 10,
    type: 'INPUT',
  },
  {
    title: 'last name',
    dataIndex: 'lastName',
    span: 10,
    type: 'INPUT',
    tooltip: "I'm tooltip",
  },
  {
    title: 'age',
    dataIndex: 'age',
    span: 4,
    type: 'INPUT_NUMBER',
    mode: 'button',
    min: 1,
    max: 100,
  },
];

export default () => {
  return (
    <InputGroup
      columns={columns}
      onChange={(values) => {
        console.log(values);
      }}
    />
  );
};
```

## 受控模式

在使用了 `value` 属性后，组件就处于受控模式，必须通过修改 `value` 属性来控制组件的值。

在此模式下，添加行和删除行都会调用 `onChange`，如果外部接受在 `onChange` 中传入的值后，**不用**它来重新设置 `value`，那组件的值就**不会**发生变化。

```jsx
import React, { useState } from 'react';
import InputGroup from 'components/InputGroup';

const columns = [
  {
    title: 'first name',
    dataIndex: 'firstName',
    span: 9,
    type: 'INPUT',
  },
  {
    title: 'last name',
    dataIndex: 'lastName',
    span: 9,
    type: 'INPUT',
  },
  {
    title: 'age',
    dataIndex: 'age',
    span: 6,
    type: 'INPUT_NUMBER',
    mode: 'button',
    min: 1,
    max: 100,
  },
];

const initialValue = [
  {
    firstName: 'Steve',
    lastName: 'Curry',
    age: 34,
  },
  {
    firstName: 'LerBron',
    lastName: 'James',
    age: 37,
  },
  {
    firstName: 'Bryant',
    lastName: 'Kobe',
    age: 45,
  },
];

export default () => {
  const [value, setValue] = useState(initialValue);
  return (
    <InputGroup
      columns={columns}
      value={value}
      onChange={(newValue) => {
        setValue(newValue);
      }}
    />
  );
};
```

## 子组件

### CpuInput

CPU 输入器，虽然显示的单位是`Core`,但是组件内部已经转换了一层，组件期望输入输出的单位都是`m`，转为公式为`1Core = 1000m`

```tsx
import React, { useState } from 'react';
import { CpuInput } from 'components/InputGroup/NumberTextInput';

export default () => {
  const [value, setValue] = useState('2000m');
  return (
    <CpuInput
      value={value}
      onChange={(newValue) => {
        console.log(newValue);
        setValue(newValue);
      }}
    />
  );
};
```

### MemInput

内存输入器,组件期望输入输出的单位都是`Gi`

```tsx
import React, { useState } from 'react';
import { MemInput } from 'components/InputGroup/NumberTextInput';

export default () => {
  const [value, setValue] = useState('1Gi');
  return (
    <MemInput
      value={value}
      onChange={(newValue) => {
        console.log(newValue);
        setValue(newValue);
      }}
    />
  );
};
```
