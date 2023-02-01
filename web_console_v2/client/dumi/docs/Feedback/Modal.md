# Modal

基于 [Arco Modal](https://arco.design/react/components/modal#api) 封装，并在`styles/global.less`中覆盖了 Modal 相关静态方法`Modal.confirm` 的样式(带有`custom-modal`)，尽量保持和 UX 图一致

把 config 冗余的配置抽离出来，导出`withConfirmProps`/`withDeleteProps` 2 个函数

## API

支持传入 [Arco Modal](https://arco.design/react/components/modal#api) 原有的 props,并且增加一个自定义的静态方法`Modal.delete(props: ModalFuncProps)`

### withConfirmProps

```jsx | pure
export function withConfirmProps(props: ConfirmProps) {
  return {
    className: CUSTOM_CLASS_NAME,
    zIndex: Z_INDEX_GREATER_THAN_HEADER,
    okText: i18n.t('confirm'),
    cancelText: i18n.t('cancel'),
    ...props,
  };
}
```

### withDeleteProps

```jsx | pure
export function withDeleteProps(props: ConfirmProps) {
  return withConfirmProps({
    okText: i18n.t('delete'),
    okButtonProps: {
      status: 'danger',
    },
    ...props,
  });
}
```

```jsx | pure
// Custom method
MyModal.delete = (props: ModalFuncProps) => {
  return Modal.confirm(withDeleteProps(props));
};
```

## Modal.delete

```jsx
import React from 'react';
import Modal from 'components/Modal';

export default () => {
  return (
    <>
      <button
        onClick={() => {
          Modal.delete({
            title: 'You sure you want to delete it?',
            content:
              'Due to security audit reasons, the platform only supports cleaning up the event records 6 months ago',
            onOk() {
              //
            },
            onCancel() {
              //
            },
          });
        }}
      >
        Click me show Modal.delete()
      </button>
    </>
  );
};
```

## Modal.confirm

```jsx
import React from 'react';
import Modal from 'components/Modal';

export default () => {
  return (
    <>
      <button
        onClick={() => {
          Modal.confirm({
            title: 'You sure you want to delete it?',
            content:
              'Due to security audit reasons, the platform only supports cleaning up the event records 6 months ago',
            onOk() {
              //
            },
            onCancel() {
              //
            },
          });
        }}
      >
        Click me show Modal.confirm()
      </button>
    </>
  );
};
```
