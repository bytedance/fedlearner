# MoreActions

显示更多操作的组件，click 上去会显示具体的操作，同时带有禁用和禁用提示 disabled/disabledTip 的功能

<API src="components/MoreActions/index.tsx" exports='["default"]'></API>

### ActionItem

```jsx | pure
interface ActionItem {
  /** Display Label */
  label: string;
  onClick?: () => void;
  /** Sometimes you need to disable the button */
  disabled?: boolean;
  /** Sometimes you want a hint when the button is disabled */
  disabledTip?: string;
  /** Danger button style, red color */
  danger?: boolean;
}
```

## 常规使用

如果不传入 children 的话，默认显示`...`

```tsx
import React from 'react';
import MoreActions, { ActionItem } from 'components/MoreActions';

const actionList: ActionItem[] = [
  {
    label: 'Delete',
    onClick: () => {
      alert('Delete');
    },
  },
  {
    label: 'Log',
    onClick: () => {
      alert('Log');
    },
  },
  {
    label: 'Refetch',
    onClick: () => {
      alert('Refetch');
    },
  },
  {
    label: 'Disabled',
    disabled: true,
    onClick: () => {
      alert('Disabled');
    },
  },
  {
    label: 'Disabled with tip',
    disabled: true,
    disabledTip: 'tip',
    onClick: () => {
      alert('Disabled with tip');
    },
  },
  {
    label: 'Danger',
    onClick: () => {
      alert('Danger');
    },
    danger: true,
  },
  {
    label: 'Danger with disabled',
    onClick: () => {
      alert('Danger with disabled');
    },
    danger: true,
    disabled: true,
  },
];

export default () => (
  <>
    <MoreActions actionList={actionList} />
  </>
);
```

## RenderContent

```tsx
import React from 'react';
import MoreActions from 'components/MoreActions';

const actionList: ActionItem[] = [
  {
    label: 'Delete',
    onClick: () => {
      alert('Delete');
    },
  },
  {
    label: 'Log',
    onClick: () => {
      alert('Log');
    },
  },
  {
    label: 'Refetch',
    onClick: () => {
      alert('Refetch');
    },
  },
  {
    label: 'Disabled',
    disabled: true,
    onClick: () => {
      alert('Disabled');
    },
  },
  {
    label: 'Disabled with tip',
    disabled: true,
    disabledTip: 'tip',
    onClick: () => {
      alert('Disabled with tip');
    },
  },
  {
    label: 'Danger',
    onClick: () => {
      alert('Danger');
    },
    danger: true,
  },
  {
    label: 'Danger with disabled',
    onClick: () => {
      alert('Danger with disabled');
    },
    danger: true,
    disabled: true,
  },
];

export default () => (
  <>
    <MoreActions
      actionList={actionList}
      renderContent={(actionList) => {
        return actionList.map((item, index) => {
          return (
            <div>
              <span>{index + 1} </span>
              <span>{item.label}</span>
            </div>
          );
        });
      }}
    />
  </>
);
```

## Children

```tsx
import React from 'react';
import MoreActions, { ActionItem } from 'components/MoreActions';

const actionList: ActionItem[] = [
  {
    label: 'Delete',
    onClick: () => {
      alert('Delete');
    },
  },
  {
    label: 'Log',
    onClick: () => {
      alert('Log');
    },
  },
  {
    label: 'Refetch',
    onClick: () => {
      alert('Refetch');
    },
  },
  {
    label: 'Disabled',
    disabled: true,
    onClick: () => {
      alert('Disabled');
    },
  },
  {
    label: 'Disabled with tip',
    disabled: true,
    disabledTip: 'tip',
    onClick: () => {
      alert('Disabled with tip');
    },
  },
  {
    label: 'Danger',
    onClick: () => {
      alert('Danger');
    },
    danger: true,
  },
  {
    label: 'Danger with disabled',
    onClick: () => {
      alert('Danger with disabled');
    },
    danger: true,
    disabled: true,
  },
];

export default () => (
  <>
    <MoreActions actionList={actionList}>Click me</MoreActions>
  </>
);
```

## ZIndex

支持修改容器的 z-index，默认为 z-index 为 var(--zIndexLessThanModal)，目前该值为 999

```tsx
import React from 'react';
import MoreActions, { ActionItem } from 'components/MoreActions';

const actionList: ActionItem[] = [
  {
    label: 'Delete',
    onClick: () => {
      alert('Delete');
    },
  },
  {
    label: 'Log',
    onClick: () => {
      alert('Log');
    },
  },
  {
    label: 'Refetch',
    onClick: () => {
      alert('Refetch');
    },
  },
  {
    label: 'Disabled',
    disabled: true,
    onClick: () => {
      alert('Disabled');
    },
  },
  {
    label: 'Disabled with tip',
    disabled: true,
    disabledTip: 'tip',
    onClick: () => {
      alert('Disabled with tip');
    },
  },
  {
    label: 'Danger',
    onClick: () => {
      alert('Danger');
    },
    danger: true,
  },
  {
    label: 'Danger with disabled',
    onClick: () => {
      alert('Danger with disabled');
    },
    danger: true,
    disabled: true,
  },
];

export default () => (
  <>
    <MoreActions actionList={actionList} zIndex={9999} />
  </>
);
```
