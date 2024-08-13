# Label

展示纯文本的组件 

> 注意 ⚠️: 此组件是在项目后期创建的，所以代码中可能存在很多硬编码的文本组件，以后为了统一管理，可能会逐一替换。

<API src="../../../src/styles/elements.ts" exports='["Label"]' ></API>

## Label

普通文本

```jsx
import React from 'react';
import { Label } from 'styles/elements';

export default () => (
  <>
    <Label marginRight={16}>Label</Label>
    <Label>Label</Label>
    <Label isBlock={true}>BlockLabel</Label>
    <Label>Label</Label>
  </>
);
```

### LabelStrong

强调文本

与 Label 的 props 相同，只是默认值不一样

```
fontSize: props.fontSize || 12,
fontColor: props.fontColor || 'var(--textColorStrong)',
fontWeight: props.fontWeight || 500,
```

```jsx
import React from 'react';
import { LabelStrong } from 'styles/elements';

export default () => (
  <>
    <LabelStrong>LabelStrong</LabelStrong>
  </>
);
```

### LabelTint

次要的小文本

与 Label 的 props 相同，只是默认值不一样

```
fontSize: props.fontSize || 12,
fontColor: props.fontColor || 'var(--textColorSecondary)',
fontWeight: props.fontWeight || 400,
```

```jsx
import React from 'react';
import { LabelTint } from 'styles/elements';

export default () => (
  <>
    <LabelTint>LabelTint</LabelTint>
  </>
);
```

### LabelForm

表单文本

与 Label 的 props 相同，只是默认值不一样

```
fontSize: props.fontSize || 13,
fontColor: props.fontColor || 'rgba(0, 0, 0, 0.85)',
fontWeight: props.fontWeight || 400,
```

```jsx
import React from 'react';
import { LabelForm } from 'styles/elements';

export default () => (
  <>
    <LabelForm>LabelForm</LabelForm>
  </>
);
```
