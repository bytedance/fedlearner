# VariblePermission

显示权限 icon 的组件，常用于工作流详情页中

目前有 3 种权限

- VariableAccessMode.PEER_WRITABLE `对侧可编辑`
- VariableAccessMode.PEER_READABLE `对侧可见`
- VariableAccessMode.PRIVATE `对侧不可见`

```js | pure
import { VariableAccessMode } from 'typings/variable';

export enum VariableAccessMode {
  UNSPECIFIED = 'UNSPECIFIED',
  PRIVATE = 'PRIVATE',
  PEER_READABLE = 'PEER_READABLE',
  PEER_WRITABLE = 'PEER_WRITABLE',
}
```

<API src="components/VariblePermission/index.tsx"></API>

## 子组件

### Writable

VariableAccessMode.PEER_WRITABLE 对侧可编辑

```tsx
import React from 'react';
import VariblePermission from 'components/VariblePermission';

export default () => (
  <>
    <div>desc = false</div>
    <VariblePermission.Writable desc={false} />
    <div>desc = true</div>
    <VariblePermission.Writable desc={true} />
  </>
);
```

### Readable

VariableAccessMode.PEER_READABLE `对侧可见`

```tsx
import React from 'react';
import VariblePermission from 'components/VariblePermission';

export default () => (
  <>
    <div>desc = false</div>
    <VariblePermission.Readable desc={false} />
    <div>desc = true</div>
    <VariblePermission.Readable desc={true} />
  </>
);
```

### Private

VariableAccessMode.PRIVATE `对侧不可见`

```tsx
import React from 'react';
import VariblePermission from 'components/VariblePermission';

export default () => (
  <>
    <div>desc = false</div>
    <VariblePermission.Private desc={false} />
    <div>desc = true</div>
    <VariblePermission.Private desc={true} />
  </>
);
```

### VariablePermissionLegend

```tsx
import React from 'react';
import { VariablePermissionLegend } from 'components/VariblePermission';

export default () => (
  <>
    <div>desc = false</div>
    <VariablePermissionLegend desc={false} />
    <div>desc = true</div>
    <VariablePermissionLegend desc={true} />
    <div>desc = true + prefix = "对侧"</div>
    <VariablePermissionLegend desc={true} prefix="对侧" />
  </>
);
```
