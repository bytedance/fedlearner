import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '@arco-design/web-react';

type Props = {
  value?: string;
  onChange?: any;
};

const XAxisInput: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();

  return <Input value={value} onChange={onChange} placeholder={t('workflow.placeholder_x_asix')} />;
};

export default XAxisInput;
