import React, { FC } from 'react';
import { Form, Button } from 'antd';
import { Plus } from 'components/IconPark';
import { useTranslation } from 'react-i18next';
import VariableForm from './VariableForm';
import NoResult from 'components/NoResult';
import { cloneDeep } from 'lodash';
import { DEFAULT_VARIABLE } from '../../store';

const VariableList: FC = () => {
  const { t } = useTranslation();

  return (
    <Form.List name="variables">
      {(fields, { add, remove }) => (
        <div>
          {fields.map((field) => (
            <Form.Item
              {...field}
              noStyle
              rules={[{ required: true, message: t('project.msg_var_name') }]}
            >
              <VariableForm name={[field.name]} onRemove={() => remove(field.name)} />
            </Form.Item>
          ))}
          {fields.length === 0 && (
            <NoResult text="暂无变量，新建一个吧" style={{ margin: '20px auto', width: '30%' }} />
          )}
          <Form.Item wrapperCol={{ offset: 9 }}>
            {/* DO NOT simplify `() => add()` to `add`, it will pollute form value with $event */}
            <Button
              type="primary"
              size="small"
              icon={<Plus />}
              onClick={() => add(cloneDeep(DEFAULT_VARIABLE))}
            >
              {t('workflow.btn_add_var')}
            </Button>
          </Form.Item>
        </div>
      )}
    </Form.List>
  );
};

export default VariableList;
