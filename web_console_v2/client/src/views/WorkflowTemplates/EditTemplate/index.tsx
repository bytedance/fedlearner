import React, { FC, useRef } from 'react';
import TemplateForm from '../TemplateForm';

const EditTemplate: FC = () => {
  const isHydrated = useRef(false);
  return <TemplateForm isEdit isHydrated={isHydrated} />;
};

export default EditTemplate;
