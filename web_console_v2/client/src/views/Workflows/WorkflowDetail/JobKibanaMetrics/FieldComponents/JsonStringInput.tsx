import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '@arco-design/web-react';

type Props = {
  value?: string;
  onChange?: any;
};

const JsonStringInput: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();

  return (
    <Input.TextArea
      defaultValue={value}
      onChange={onChange}
      rows={1}
      placeholder={t('workflow.placehodler_json_syntax')}
    />
  );
};

export default JsonStringInput;
