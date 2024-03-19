# PropertyList

显示属性列表的组件

<API src="components/PropertyList/index.tsx"></API>

### VariableAccessMode

```ts | pure
enum VariableAccessMode {
  UNSPECIFIED = 'UNSPECIFIED',
  PRIVATE = 'PRIVATE',
  PEER_READABLE = 'PEER_READABLE',
  PEER_WRITABLE = 'PEER_WRITABLE',
}
```

### PropertyItem

```ts | pure
type PropertyItem = {
  /** Display label */
  label: string;
  /** Display value */
  value: any;
  /** Is hidden */
  hidden?: boolean;
  /** Access mode */
  accessMode?: VariableAccessMode;
};
```

## 常规使用

默认一行两个

```tsx
import React from 'react';
import PropertyList from 'components/PropertyList';

const properties = [
  {
    label: 'ID',
    value: '12345',
  },
  {
    label: 'State',
    value: 'READY',
  },
  {
    label: 'Type',
    value: 'NN Model',
  },
  {
    label: 'Replicas',
    value: '1/10',
  },
  {
    label: 'Created Time',
    value: '2021-04-21 18:00:23',
  },
  {
    label: 'Updated Time',
    value: '2021-04-21 22:00:23',
  },
  {
    label: 'Deleted Time',
    value: '2021-04-21 23:00:23',
  },
];

export default () => (
  <>
    <PropertyList properties={properties} />
  </>
);
```

## Cols

```tsx
import React from 'react';
import PropertyList from 'components/PropertyList';

const properties = [
  {
    label: 'ID',
    value: '12345',
  },
  {
    label: 'State',
    value: 'READY',
  },
  {
    label: 'Type',
    value: 'NN Model',
  },
  {
    label: 'Replicas',
    value: '1/10',
  },
  {
    label: 'Created Time',
    value: '2021-04-21 18:00:23',
  },
  {
    label: 'Updated Time',
    value: '2021-04-21 22:00:23',
  },
  {
    label: 'Deleted Time',
    value: '2021-04-21 23:00:23',
  },
];

export default () => (
  <>
    <div>cols = 3</div>
    <PropertyList properties={properties} cols={3} />
    <div>cols = 4</div>
    <PropertyList properties={properties} cols={4} />
    <div>cols = 5</div>
    <PropertyList properties={properties} cols={5} />
  </>
);
```

## InitialVisibleRows

```tsx
import React from 'react';
import PropertyList from 'components/PropertyList';

const properties = [
  {
    label: 'ID',
    value: '12345',
  },
  {
    label: 'State',
    value: 'READY',
  },
  {
    label: 'Type',
    value: 'NN Model',
  },
  {
    label: 'Replicas',
    value: '1/10',
  },
  {
    label: 'Created Time',
    value: '2021-04-21 18:00:23',
  },
  {
    label: 'Updated Time',
    value: '2021-04-21 22:00:23',
  },
  {
    label: 'Deleted Time',
    value: '2021-04-21 23:00:23',
  },
];

export default () => (
  <>
    <div>initialVisibleRows = 1</div>
    <PropertyList properties={properties} cols={3} initialVisibleRows={1} />
    <div>initialVisibleRows = 2</div>
    <PropertyList properties={properties} cols={3} initialVisibleRows={2} />
    <div>initialVisibleRows = 3</div>
    <PropertyList properties={properties} cols={3} initialVisibleRows={3} />
  </>
);
```

## Hidden

```tsx
import React from 'react';
import PropertyList from 'components/PropertyList';

const properties = [
  {
    label: 'ID',
    value: '12345',
  },
  {
    label: 'State',
    value: 'READY',
  },
  {
    label: 'Type',
    value: 'NN Model',
  },
  {
    label: 'Replicas',
    value: '1/10',
  },
  {
    label: 'Created Time',
    value: '2021-04-21 18:00:23',
    hidden: true,
  },
  {
    label: 'Updated Time',
    value: '2021-04-21 22:00:23',
    hidden: true,
  },
  {
    label: 'Deleted Time',
    value: '2021-04-21 23:00:23',
  },
];

export default () => (
  <>
    <PropertyList properties={properties} cols={3} initialVisibleRows={3} />
  </>
);
```

## AccessMode

- VariableAccessMode.PEER_WRITABLE 为对侧可编辑
- VariableAccessMode.PEER_READABLE 为对侧可见
- VariableAccessMode.PRIVATE 为对侧不可见

```tsx
import React from 'react';
import PropertyList from 'components/PropertyList';
import { VariablePermissionLegend } from 'components/VariblePermission';

enum VariableAccessMode {
  UNSPECIFIED = 'UNSPECIFIED',
  PRIVATE = 'PRIVATE',
  PEER_READABLE = 'PEER_READABLE',
  PEER_WRITABLE = 'PEER_WRITABLE',
}

const properties = [
  {
    label: 'ID',
    value: '12345',
    accessMode: VariableAccessMode.UNSPECIFIED,
  },
  {
    label: 'State',
    value: 'READY',
    accessMode: VariableAccessMode.PRIVATE,
  },
  {
    label: 'Type',
    value: 'NN Model',
    accessMode: VariableAccessMode.PEER_READABLE,
  },
  {
    label: 'Replicas',
    value: '1/10',
    accessMode: VariableAccessMode.PEER_WRITABLE,
  },
  {
    label: 'Created Time',
    value: '2021-04-21 18:00:23',
  },
  {
    label: 'Updated Time',
    value: '2021-04-21 22:00:23',
  },
  {
    label: 'Deleted Time',
    value: '2021-04-21 23:00:23',
  },
];

export default () => (
  <>
    <VariablePermissionLegend desc={true} prefix="对侧" />
    <PropertyList properties={properties} cols={3} initialVisibleRows={3} />
  </>
);
```

## Align

css align-items 属性的代理

垂直居中 align="center"

```tsx
import React from 'react';
import PropertyList from 'components/PropertyList';

const properties = [
  {
    label: 'ID',
    value: '12345',
  },
  {
    label: 'State',
    value: 'READY',
  },
  {
    label: 'Type',
    value: 'NN Model',
  },
  {
    label: 'Replicas',
    value: '1/10',
  },
  {
    label: 'Created Time',
    value: '2021-04-21 18:00:23',
  },
  {
    label: 'Updated Time',
    value: '2021-04-21 22:00:23',
  },
  {
    label: 'Deleted Time',
    value: '2021-04-21 23:00:23',
  },
];

export default () => (
  <>
    <PropertyList properties={properties} align="center" />
  </>
);
```
