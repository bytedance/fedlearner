import React, { FC, useCallback, useLayoutEffect, useRef } from 'react';
import styled from './EnvsInputForm.module.less';

import { useTranslation } from 'react-i18next';
import { convertToUnit } from 'shared/helpers';

import { Form, Input, Button, Grid } from '@arco-design/web-react';
import { Delete, PlusCircle } from 'components/IconPark';

const Row = Grid.Row;

const EnvVariablesForm: FC<{
  path: any;
  disabled?: boolean;
}> = ({ path, disabled }) => {
  const { t } = useTranslation();
  const listInnerRef = useRef<HTMLDivElement>();
  const listContainerRef = useRef<HTMLDivElement>();

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
    setListContainerMaxHeight(innerHeight);
  });

  return (
    <div>
      <div
        className={styled.list_container}
        ref={listContainerRef as any}
        onTransitionEnd={onFoldAnimationEnd}
      >
        <Form.List field={path.join('.')}>
          {(fields, { add, remove }) => {
            return (
              <div ref={listInnerRef as any}>
                {fields.map((field, index) => (
                  <Row key={field.key + index} align="start" style={{ position: 'relative' }}>
                    <Form.Item
                      style={{ flex: '0 0 50%' }}
                      {...field}
                      label="Name"
                      field={[field.field, 'name'].join('.')}
                      key={[field.key, 'name'].join('.')}
                      rules={[{ required: true }]}
                    >
                      <Input placeholder="name" disabled={disabled} />
                    </Form.Item>

                    <Form.Item
                      style={{ flex: '0 0 50%' }}
                      label="Value"
                      {...field}
                      field={[field.field, 'value'].join('.')}
                      key={[field.key, 'value'].join('.')}
                      rules={[{ required: true }]}
                    >
                      <Input.TextArea placeholder="value" disabled={disabled} />
                    </Form.Item>

                    <Button
                      className={styled.remove_button}
                      size="small"
                      icon={<Delete />}
                      shape="circle"
                      type="text"
                      onClick={() => remove(field.key)}
                    />
                  </Row>
                ))}
                <Button size="small" icon={<PlusCircle />} onClick={() => add()}>
                  {t('project.add_parameters')}
                </Button>
              </div>
            );
          }}
        </Form.List>
      </div>
    </div>
  );

  function onFoldAnimationEnd(_: React.TransitionEvent) {
    // Because of user can adjust list inner's height by resize value-textarea or add/remove variable
    // we MUST set container's maxHeight to 'initial' after unfolded (after which user can interact)
    listContainerRef.current!.style.maxHeight = 'initial';
  }
};

export default EnvVariablesForm;
