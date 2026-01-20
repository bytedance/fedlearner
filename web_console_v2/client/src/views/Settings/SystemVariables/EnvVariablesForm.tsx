import React, { FC, useCallback, useLayoutEffect, useRef } from 'react';
import styled from './EnvVariablesForm.module.less';

import { convertToUnit, isStringCanBeParsed } from 'shared/helpers';

import { Form, Input, Button, Grid, Switch } from '@arco-design/web-react';
import { Delete, Plus } from 'components/IconPark';

import { FormInstance } from '@arco-design/web-react/es/Form';
import { SystemVariable } from 'typings/settings';

const { Row, Col } = Grid;

export const VARIABLES_FIELD_NAME = 'variables';
export const VARIABLES_ERROR_CHANNEL = 'system.field_variables_error';

const DEFAULT_VARIABLE = {
  name: '',
  value: '',
  fixed: false,
  value_type: 'STRING',
};

const EnvVariablesForm: FC<{
  layout: {
    labelCol: { span: number };
    wrapperCol: { span: number };
  };
  formInstance?: FormInstance;
  disabled?: boolean;
}> = ({ layout, disabled, formInstance }) => {
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
    <div className={styled.container}>
      <div className={styled.header}>
        <Row align="center">
          <Col {...layout.labelCol}>
            <h3 className={styled.heading}>{'环境变量参数配置'}</h3>
          </Col>
        </Row>
      </div>

      <div
        className={styled.list_container}
        ref={listContainerRef as any}
        onTransitionEnd={onFoldAnimationEnd}
      >
        <Form.List field={VARIABLES_FIELD_NAME}>
          {(fields, { add, remove }) => (
            <div ref={listInnerRef as any}>
              {fields.map((field, index) => {
                const list = (formInstance?.getFieldValue(VARIABLES_FIELD_NAME) ??
                  []) as SystemVariable[];
                const isFixed = list[index]?.fixed ?? false;
                const valueType = list[index]?.value_type ?? 'STRING';

                return (
                  <Row key={field.key} align="center" style={{ position: 'relative' }}>
                    <Form.Item
                      style={{ flex: '0 0 50%' }}
                      label="Name"
                      field={field.field + '.name'}
                      rules={[{ required: true, message: '请输入变量名' }]}
                    >
                      <Input placeholder="name" disabled={disabled || isFixed} />
                    </Form.Item>

                    <Form.Item
                      labelCol={{ span: 4 }}
                      wrapperCol={{ span: 18 }}
                      style={{ flex: '0 0 50%' }}
                      label="Value"
                      field={field.field + '.value'}
                      rules={[
                        { required: true, message: '请输入变量值' },
                        valueType === 'LIST' || valueType === 'OBJECT'
                          ? {
                              validator: (value, callback) => {
                                if (isStringCanBeParsed(value)) {
                                  callback();
                                } else {
                                  callback(`JSON ${valueType} 格式错误`);
                                }
                              },
                            }
                          : {},
                      ]}
                    >
                      <Input.TextArea placeholder="value" disabled={disabled} />
                    </Form.Item>
                    <Form.Item
                      label="fixed"
                      field={field.field + '.fixed'}
                      triggerPropName="checked"
                      hidden
                    >
                      <Switch />
                    </Form.Item>
                    <Form.Item label="value_type" field={field.field + '.value_type'} hidden>
                      <Input />
                    </Form.Item>

                    {!isFixed && (
                      <Button
                        className={styled.remove_button}
                        size="small"
                        icon={<Delete />}
                        type="text"
                        onClick={() => remove(index)}
                      />
                    )}
                  </Row>
                );
              })}
              {/* Empty placeholder */}
              {fields.length === 0 && (
                <Form.Item className={styled.no_variables} wrapperCol={{ offset: 3 }}>
                  {'当前没有环境变量参数，请添加'}
                </Form.Item>
              )}

              <Form.Item wrapperCol={{ offset: 3 }}>
                {/* DO NOT simplify `() => add()` to `add`, it will pollute form value with $event */}
                <Button
                  type="primary"
                  size="small"
                  icon={<Plus />}
                  onClick={() => add(DEFAULT_VARIABLE)}
                >
                  {'添加参数'}
                </Button>
              </Form.Item>
            </div>
          )}
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
