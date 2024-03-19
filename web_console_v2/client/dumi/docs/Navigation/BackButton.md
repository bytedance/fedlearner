# BackButton

后退组件，带有二次确定对话框(默认关闭)，需要自己实现 onClick 方法,常用于 `<SharedPageLayout/>`的`title`上

> 注意 ⚠️: isShowConfirmModal 为 true 时，onClick 方法只会在点击二次确定对话框的`确定`按钮时才会触发

<API src="components/BackButton/index.tsx"></API>

## 常规使用

```tsx
import React from 'react';
import BackButton from 'components/BackButton';

export default () => (
  <>
    <BackButton
      onClick={() => {
        alert('back');
      }}
    >
      back
    </BackButton>
  </>
);
```

## IsShowConfirmModal

当 isShowConfirmModal = true 时，点击组件时，会出现一个用 [Modal.confirm](/feedback/modal#modalconfirm) 封装的二次确定对话框，点击确定时，会触发原来的 onClick 方法

```tsx
import React from 'react';
import BackButton from 'components/BackButton';

export default () => (
  <>
    <div>default modal title/content</div>
    <BackButton
      isShowConfirmModal={true}
      onClick={() => {
        alert('back');
      }}
    >
      back
    </BackButton>
    <div>custom modal title/content</div>
    <BackButton
      isShowConfirmModal={true}
      title="custom title"
      content="custom content"
      onClick={() => {
        alert('back');
      }}
    >
      back
    </BackButton>
  </>
);
```

## 与 SharedPageLayout 配合

```tsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

export default () => (
  <RecoilRoot>
    <SharedPageLayout
      title={
        <BackButton
          onClick={() => {
            alert('back');
          }}
        >
          back
        </BackButton>
      }
    >
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```
