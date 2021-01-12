import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { Form, Input, Space } from 'antd';
import { useTranslation } from 'react-i18next';
import AddField from './AddField';
import TrashCan from '../../../components/Container/TrashCan';
import { useToggle } from 'react-use';

const Container = styled.div``;

const Body = styled.div`
  width: 800px;
  .ant-space-item {
    &:nth-child(1) {
      flex: 1;
      .ant-form-item-label {
        min-width: 166px;
      }
    }

    &:nth-child(2) {
      flex: 1;
      .ant-form-item-label {
        max-width: 100px;
        .ant-form-item-required {
          &::before {
            display: none;
          }
        }
      }
    }
  }
`;

const Header = styled.div`
  position: relative;
  padding-bottom: 32px;
  .title {
    font-weight: 600;
    font-size: 16px;
    line-height: 24px;
    color: var(--gray10);
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    font-size: 14px;
    line-height: 24px;
    color: var(--arcoblue6);
    position: absolute;
    left: 166px;
    &::after {
      width: 0;
      height: 0;
      content: '';
      display: inline-block;
      margin-left: 8px;
      transform: translateY(2px);
      border: 3px solid transparent;
      border-top: 4px solid var(--arcoblue6);
    }

    &.show {
      &::after {
        transform: translateY(-2px) rotate(180deg);
      }
    }
  }
`;

interface Props {}

interface EnvPath {
  name: string;
  value: string;
}

function EnvPathsForm({}: Props): ReactElement {
  const { t } = useTranslation();
  const [isFolded, toggleFolded] = useToggle(true);
  return (
    <Container>
      <Header>
        {isFolded ? (
          <>
            <span className="toggle hide" onClick={toggleFolded}>
              {t('project.env_path_config')}
            </span>
          </>
        ) : (
          <>
            <span className="title"> {t('project.show_env_path_config')}</span>
            <span className="toggle show" onClick={toggleFolded}>
              {t('project.hide_env_path_config')}
            </span>
          </>
        )}
      </Header>
      {isFolded ? null : (
        <Body>
          <Form.List name="variables">
            {(fields, { add, remove }, { errors }) => (
              <>
                {fields.map((field, index) => (
                  <Space
                    key={field.key}
                    style={{ display: 'flex', marginBottom: 8 }}
                    align="baseline"
                  >
                    <Form.Item
                      {...field}
                      label="Name"
                      name={[field.name, 'name']}
                      fieldKey={[field.fieldKey, 'name']}
                      rules={[{ required: true, message: 'Missing first name' }]}
                    >
                      <Input placeholder="name" />
                    </Form.Item>
                    <Form.Item
                      label="Value"
                      {...field}
                      name={[field.name, 'value']}
                      fieldKey={[field.fieldKey, 'value']}
                      rules={[{ required: true, message: 'Missing first name' }]}
                    >
                      <Input.TextArea placeholder="value" />
                    </Form.Item>
                    <TrashCan onClick={() => remove(field.name)} />
                  </Space>
                ))}
                <Form.Item>
                  <AddField onClick={() => add()} />
                </Form.Item>
              </>
            )}
          </Form.List>
        </Body>
      )}
    </Container>
  );
}

export default EnvPathsForm;
