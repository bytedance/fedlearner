import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Input, Button, Col, Radio, Popconfirm, FormInstance } from 'antd';
import { useTranslation } from 'react-i18next';
import { Variable, VariableAccessMode } from 'typings/variable';
import { Delete, Down } from 'components/IconPark';
import { MixinCommonTransition } from 'styles/mixins';
import VariablePermission from 'components/VariblePermission';
import { indicators } from 'components/VariableLabel';
import WidgetSchema from './WidgetSchema';
import { useToggle } from 'react-use';

const Details = styled.details`
  margin-bottom: 20px;

  .open-indicator {
    ${MixinCommonTransition()}
  }
  &[open] {
    .open-indicator {
      transform: rotate(180deg);
    }
  }
`;
const Summary = styled.summary`
  display: flex;
  align-items: center;
  height: 46px;
  padding: 0 20px;
  background-color: var(--backgroundColor);
  cursor: pointer;

  &:hover {
    background-color: #f0f0f0;
  }
`;
const Name = styled.strong`
  flex: 1;
  padding-left: 10px;
  font-size: 12px;
  line-height: 0;
  user-select: none;
`;
const Container = styled.div`
  padding-right: 60px;
  padding-top: 20px;
`;

type Props = {
  path: (number | string)[];
  value?: Variable;
  form: FormInstance;
  onChange?: (val: Variable) => any;
  onRemove: any;
};

/**
 * Dynamic Variable form list
 * MUST wrap with a antd.Form
 */
const VariableForm: FC<Props> = ({ form, path, value, onRemove }) => {
  const { t } = useTranslation();
  const [isOpen] = useToggle(!value?.name);

  if (!value) {
    return null;
  }

  const data = value;

  const PermissionIndicator = indicators[data.access_mode];

  return (
    <Details open={isOpen}>
      <Summary>
        <PermissionIndicator />

        <Name>{data.name || '点击编辑变量'}</Name>
        <Col>
          <Popconfirm title={t('确认删除该变量吗')} onConfirm={onRemoveClick as any}>
            <Button type="link" size="small" icon={<Delete />}>
              删除
            </Button>
          </Popconfirm>

          <Down className="open-indicator" />
        </Col>
      </Summary>

      <Container>
        <Form.Item
          name={[...path, 'name']}
          label={t('workflow.label_var_name')}
          rules={[
            { required: true, message: t('workflow.msg_varname_required') },
            {
              pattern: /^[a-zA-Z_0-9-]+$/g,
              message: t('workflow.msg_varname_invalid'),
            },
          ]}
        >
          <Input placeholder={t('workflow.placeholder_var_name')} />
        </Form.Item>

        <Form.Item
          name={[...path, 'access_mode']}
          label={t('workflow.label_peer_access')}
          rules={[{ required: true }]}
        >
          <Radio.Group>
            <Radio.Button value={VariableAccessMode.PEER_WRITABLE}>
              <VariablePermission.Writable desc />
            </Radio.Button>
            <Radio.Button value={VariableAccessMode.PEER_READABLE}>
              <VariablePermission.Readable desc />
            </Radio.Button>
            <Radio.Button value={VariableAccessMode.PRIVATE}>
              <VariablePermission.Private desc />
            </Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item name={[...path, 'widget_schema']} noStyle>
          <WidgetSchema form={form} path={[...path, 'widget_schema']} />
        </Form.Item>
      </Container>
    </Details>
  );

  function onRemoveClick(event: MouseEvent) {
    event.stopPropagation();

    onRemove && onRemove(value);
  }
};

export default VariableForm;
