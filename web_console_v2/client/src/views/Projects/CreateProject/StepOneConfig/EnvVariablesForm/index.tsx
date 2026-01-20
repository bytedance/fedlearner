import React, {
  useCallback,
  useLayoutEffect,
  useRef,
  useImperativeHandle,
  ForwardRefRenderFunction,
  forwardRef,
} from 'react';
import { Form, Input, Button } from '@arco-design/web-react';
import { useToggle } from 'react-use';
import { IconDelete, IconPlus, IconCaretDown, IconCaretUp } from '@arco-design/web-react/icon';
import { FormInstance } from '@arco-design/web-react';
import { convertToUnit } from 'shared/helpers';
import { useSubscribe } from 'hooks';
import GridRow from 'components/_base/GridRow';

import styles from './index.module.less';

export const VARIABLES_FIELD_NAME = 'variables';
export const VARIABLES_ERROR_CHANNEL = 'project.field_variables_error';

type Props = {
  formInstance?: FormInstance;
  disabled?: boolean;
  isEdit?: boolean;
};

export type ExposedRef = {
  toggleFolded: (params: boolean) => void;
};

const EnvVariablesForm: ForwardRefRenderFunction<ExposedRef | undefined, Props> = (
  { disabled, isEdit = true },
  parentRef,
) => {
  const [isFolded, toggleFolded] = useToggle(isEdit);
  const listInnerRef = useRef<HTMLDivElement>();
  const listContainerRef = useRef<HTMLDivElement>();

  useSubscribe(VARIABLES_ERROR_CHANNEL, () => {
    toggleFolded(false);
  });

  useImperativeHandle(parentRef, () => {
    return {
      toggleFolded,
    };
  });

  const setListContainerMaxHeight = useCallback(
    (nextHeight: any) => {
      listContainerRef.current!.style.maxHeight = convertToUnit(nextHeight);
    },
    [listContainerRef],
  );
  const getListInnerHeight = useCallback(() => {
    return listInnerRef.current!.offsetHeight!;
  }, [listInnerRef]);

  useLayoutEffect(() => {
    const innerHeight = getListInnerHeight() + 30;

    if (isFolded) {
      setListContainerMaxHeight(innerHeight);
      // Q: Why read inner's height one time before set maxHeight to 0 for folding
      // A: Since we set maxHeight to 'initial' everytime unfold-transition ended, it's important
      // to re-set maxHeight to innerHeight before folding, we need a ${specific value} → 0 transition
      // not the `initial` → 0 in which case animation would lost
      getListInnerHeight();
      setListContainerMaxHeight(0);
    } else {
      setListContainerMaxHeight(innerHeight);
    }
  }, [isFolded, getListInnerHeight, setListContainerMaxHeight]);

  return (
    <div>
      {isEdit && (
        <div className={styles.header}>
          <div className={styles.toggler} onClick={toggleFolded} data-folded={String(isFolded)}>
            {isFolded ? (
              <>
                展开环境变量配置 <IconCaretDown />
              </>
            ) : (
              <>
                收起环境变量配置
                <IconCaretUp />
              </>
            )}
            {/* <CaretDown /> */}
          </div>
        </div>
      )}

      <div
        className={styles.list_container}
        ref={listContainerRef as any}
        data-folded={String(isFolded)}
        onTransitionEnd={onFoldAnimationEnd}
      >
        <Form.List field={`config.${VARIABLES_FIELD_NAME}`}>
          {(fields, { add, remove }) => (
            <div ref={listInnerRef as any}>
              {fields.map((field, index) => (
                <GridRow
                  style={{ position: 'relative', gridTemplateColumns: '1fr 1fr' }}
                  gap={10}
                  key={field.key}
                  align="start"
                >
                  <Form.Item
                    field={`${field.field}.name`}
                    rules={[{ required: true, message: '请输入变量名' }]}
                  >
                    <Input.TextArea placeholder="name" disabled={disabled} />
                  </Form.Item>

                  <Form.Item
                    field={`${field.field}.value`}
                    rules={[{ required: true, message: '请输入变量值' }]}
                  >
                    <Input.TextArea placeholder="value" disabled={disabled} />
                  </Form.Item>
                  <Button
                    className={styles.remove_button}
                    size="small"
                    icon={<IconDelete />}
                    shape="circle"
                    type="text"
                    onClick={() => remove(index)}
                  />
                </GridRow>
              ))}
              {/* Empty placeholder */}
              {isEdit && fields.length === 0 && (
                <Form.Item className={styles.no_variables}>当前没有环境变量参数</Form.Item>
              )}

              <Form.Item>
                {/* DO NOT simplify `() => add()` to `add`, it will pollute form value with $event */}
                <Button
                  className={styles.add_button}
                  size="small"
                  icon={<IconPlus />}
                  type="default"
                  onClick={() => add()}
                >
                  新增参数
                </Button>
              </Form.Item>
            </div>
          )}
        </Form.List>
      </div>
    </div>
  );

  function onFoldAnimationEnd(_: React.TransitionEvent) {
    if (!isFolded) {
      // Because of user can adjust list inner's height by resize value-textarea or add/remove variable
      // we MUST set container's maxHeight to 'initial' after unfolded (after which user can interact)
      listContainerRef.current!.style.maxHeight = 'initial';
    }
  }
};

export default forwardRef(EnvVariablesForm);
