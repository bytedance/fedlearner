# ButtonWithModalConfirm

带有二次确认功能(对话框)的 Button 组件，基于[Arco Button](xxx) 和 [Modal.confirm](/feedback/modal#modalconfirm) 封装

props 可以传任意 Button 的 props

<API src="components/ButtonWithModalConfirm/index.tsx"></API>

## 常规使用

```tsx
import React from 'react';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';

export default () => (
  <>
    <ButtonWithModalConfirm
      onClick={() => {
        alert('cancel');
      }}
    >
      Cancel
    </ButtonWithModalConfirm>
    <ButtonWithModalConfirm
      style={{ marginLeft: 8 }}
      type="primary"
      onClick={() => {
        alert('confirm');
      }}
    >
      confirm
    </ButtonWithModalConfirm>
  </>
);
```

## IsShowConfirmModal

```tsx
import React from 'react';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';

export default () => (
  <>
    <ButtonWithModalConfirm
      isShowConfirmModal={true}
      onClick={() => {
        alert('Default title/content');
      }}
    >
      Default title/content
    </ButtonWithModalConfirm>
    <ButtonWithModalConfirm
      style={{ marginLeft: 8 }}
      isShowConfirmModal={true}
      onClick={() => {
        alert('Custom title/content');
      }}
    >
      Custom title/content
    </ButtonWithModalConfirm>
  </>
);
```
