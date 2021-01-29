import React, { FC, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { Form, Input, Button, Row, Col } from 'antd';
import { useTranslation } from 'react-i18next';
import { useToggle } from 'react-use';
import { CaretDown, Delete, Plus } from 'components/IconPark';
import { MixinCommonTransition } from 'styles/mixins';
import { FormInstance } from 'antd/lib/form';
import { convertToUnit, giveWeakRandomKey } from 'shared/helpers';
import { useSubscribe } from 'hooks';

const Container = styled.div`
  margin-top: 30px;
`;
const Header = styled.div`
  margin-bottom: 20px;
`;
const Heading = styled.h3`
  ${MixinCommonTransition()}
  margin-bottom: 0;
  font-size: 16px;
  font-weight: 500;
  line-height: 24px;
  color: var(--gray10);

  &[data-folded='true'] {
    opacity: 0;
    transform: translateX(30px);
  }
`;
const Toggler = styled.div`
  display: inline-flex;

  align-items: center;
  font-size: 14px;
  line-height: 1;
  color: var(--arcoblue6);
  cursor: pointer;
  user-select: none;

  > .anticon {
    ${MixinCommonTransition()}
    margin-left: 5px;
  }

  &[data-folded='false'] {
    > .anticon {
      transform: rotate(-180deg);
    }
  }
`;
const NoVariable = styled(Form.Item)`
  color: var(--textColorSecondary);
`;
const AddButton = styled(Button)``;
const ListContainer = styled.div`
  ${MixinCommonTransition()}
  width: calc(var(--form-width, 500px) * 2);
  overflow: hidden;

  &.is-folded {
    opacity: 0;
    overflow: hidden;
  }
`;
const RemoveButton = styled(Button)`
  position: absolute;
  right: 0;
`;

export const VARIABLES_FIELD_NAME = 'variables';
export const VARIABLES_ERROR_CHANNEL = 'project.field_variables_error';
export const VARIABLES_CHANGE_CHANNEL = 'project.variables_change';

type EnvVariable = { name: string; value: string };

const EnvVariablesForm: FC<{
  layout: {
    labelCol: { span: number };
    wrapperCol: { span: number };
  };
  formInstance?: FormInstance;
}> = ({ layout }) => {
  const { t } = useTranslation();
  const [isFolded, toggleFolded] = useToggle(true);
  const [seed, setSeed] = useState(giveWeakRandomKey());
  const listDom = useRef<HTMLDivElement>();
  const [listMaxHeight, setMaxHeight] = useState<number>(0);

  useSubscribe(VARIABLES_ERROR_CHANNEL, () => {
    toggleFolded(false);
    // TODO: find a better way to implement next-tick
    // Re calc max height at next-tick
    setImmediate(() => {
      setSeed(giveWeakRandomKey());
    });
  });
  useSubscribe(VARIABLES_CHANGE_CHANNEL, () => {
    // When variables change, re-set a random seed to trigger re-setMaxHeight effect below!
    setSeed(giveWeakRandomKey());
  });

  useEffect(() => {
    setMaxHeight((listDom.current?.offsetHeight || 0) + 30);
  }, [seed, listDom, isFolded]);

  return (
    <Container>
      <Header>
        <Row align="middle">
          <Col {...layout.labelCol}>
            <Heading data-folded={String(isFolded)}>{t('project.show_env_path_config')}</Heading>
          </Col>
          <Col {...layout.wrapperCol}>
            <Toggler onClick={toggleFolded} data-folded={String(isFolded)}>
              {t('project.hide_env_path_config')} <CaretDown />
            </Toggler>
          </Col>
        </Row>
      </Header>

      <ListContainer
        className={isFolded ? 'is-folded' : ''}
        style={{
          maxHeight: convertToUnit(isFolded ? 0 : listMaxHeight),
        }}
      >
        <Form.List name={VARIABLES_FIELD_NAME}>
          {(fields, { add, remove }) => (
            <div ref={listDom as any}>
              {fields.map((field, index) => (
                <Row key={field.fieldKey + index} align="top" style={{ position: 'relative' }}>
                  <Form.Item
                    style={{ flex: '0 0 50%' }}
                    {...field}
                    label="Name"
                    name={[field.name, 'name']}
                    fieldKey={[field.fieldKey, 'name']}
                    rules={[{ required: true, message: t('project.msg_var_name') }]}
                  >
                    <Input placeholder="name" />
                  </Form.Item>

                  <Form.Item
                    labelCol={{ span: 4 }}
                    wrapperCol={{ span: 18 }}
                    style={{ flex: '0 0 50%' }}
                    label="Value"
                    {...field}
                    name={[field.name, 'value']}
                    fieldKey={[field.fieldKey, 'value']}
                    rules={[{ required: true, message: t('project.msg_var_value') }]}
                  >
                    <Input.TextArea placeholder="value" />
                  </Form.Item>

                  <RemoveButton
                    size="small"
                    icon={<Delete />}
                    shape="circle"
                    type="text"
                    onClick={() => remove(field.name)}
                  />
                </Row>
              ))}

              {fields.length === 0 && (
                <NoVariable wrapperCol={{ offset: 4 }}>{t('project.msg_no_var_yet')}</NoVariable>
              )}
              <Form.Item wrapperCol={{ offset: 4 }}>
                {/* DO NOT simplify `() => add()` to `add`, it will pollute form value with $event */}
                <AddButton type="primary" size="small" icon={<Plus />} onClick={() => add()}>
                  {t('project.add_parameters')}
                </AddButton>
              </Form.Item>
            </div>
          )}
        </Form.List>
      </ListContainer>
    </Container>
  );
};

export default EnvVariablesForm;
