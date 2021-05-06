import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from 'antd';

type Props = {
  value?: string;
  onChange?: any;
};

const QueryInput: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();

  return (
    <Input.TextArea
      defaultValue={value}
      onChange={onChange}
      placeholder={t('workflow.placeholder_kibana_query')}
    />
  );
};

export default QueryInput;
