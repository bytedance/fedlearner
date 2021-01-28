import React, { FunctionComponent } from 'react';
import { Button } from 'antd';
import {
  SchemaForm,
  FormButtonGroup,
  Submit,
  IAntdSchemaFormProps,
  createFormActions,
} from '@formily/antd';
import {
  Input,
  NumberPicker,
  Select,
  Radio,
  Checkbox,
  Switch,
  Upload,
} from '@formily/antd-components';
import styled from 'styled-components';

const components = {
  Input,
  NumberPicker,
  Select,
  Radio,
  Checkbox,
  TextArea: Input.TextArea,
  Switch,
  Upload,
};

const StyledSchemaForm = styled(SchemaForm)`
  .ant-form-item-label > .ant-form-item-required::before {
    order: 2;
  }
`;
interface Props extends IAntdSchemaFormProps {
  onConfirm: (val: any) => void;
  onCancel: (_: any) => void;
  confirmText: string;
  cancelText: string;
}

export const formActions = createFormActions();

const VariableSchemaForm: FunctionComponent<Props> = ({
  schema,
  onConfirm,
  onCancel,
  cancelText,
  confirmText,
}: Props) => {
  return (
    <StyledSchemaForm
      labelAlign="left"
      components={components}
      schema={schema}
      actions={formActions}
      labelCol={8}
      onSubmit={onConfirm}
    >
      <FormButtonGroup offset={8}>
        <Submit>{confirmText}</Submit>

        {cancelText && <Button onClick={onCancel}>{cancelText}</Button>}
      </FormButtonGroup>
    </StyledSchemaForm>
  );
};

export default VariableSchemaForm;
