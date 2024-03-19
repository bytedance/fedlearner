import React, { FC, useRef } from 'react';
import TemplateForm from '../TemplateForm';

const CreateTemplate: FC = () => {
  const isHydrated = useRef(false);
  return <TemplateForm isHydrated={isHydrated} />;
};

export default CreateTemplate;
