# BreadcrumbLink

面包屑组件

<API src="components/BreadcrumbLink/index.tsx"></API>

```ts
type path = {
  /** Display label or i18n key */
  label: string;
  /** Link */
  to?: string;
};
```

## 常规使用

```tsx
import React from 'react';
import BreadcrumbLink from 'components/BreadcrumbLink';

const paths = [
  {
    label: 'navigation',
    to: '/navigation',
  },
  {
    label: 'breadcrumb-link',
    to: '/navigation/breadcrumb-link',
  },
];

export default () => (
  <>
    <BreadcrumbLink paths={paths} />
  </>
);
```

## 与 SharedPageLayout 配合

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';
import BreadcrumbLink from 'components/BreadcrumbLink';

const paths = [
  {
    label: 'navigation',
    to: '/navigation',
  },
  {
    label: 'breadcrumb-link',
    to: '/navigation/breadcrumb-link',
  },
];
export default () => (
  <RecoilRoot>
    <SharedPageLayout title={<BreadcrumbLink paths={paths} />}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```
