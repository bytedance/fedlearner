# GridRow

Row component with ability to specify gap between items

<API src="components/_base/GridRow/index.tsx"></API>

# 默认行为

默认垂直居中，水平居左，gap 为 0

```jsx
import React from 'react';
import GridRow from 'components/_base/GridRow';

export default () => (
  <>
    <GridRow>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </GridRow>
  </>
);
```

## 水平居中

```jsx
import React from 'react';
import GridRow from 'components/_base/GridRow';

export default () => (
  <>
    <GridRow justify="center">
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </GridRow>
  </>
);
```

## Gap

gap = 14

```jsx
import React from 'react';
import GridRow from 'components/_base/GridRow';

export default () => (
  <>
    <GridRow gap={14}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </GridRow>
  </>
);
```

gap = 28

```jsx
import React from 'react';
import GridRow from 'components/_base/GridRow';

export default () => (
  <>
    <GridRow gap={28}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </GridRow>
  </>
);
```
