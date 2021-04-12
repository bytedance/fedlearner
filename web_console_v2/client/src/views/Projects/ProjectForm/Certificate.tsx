import React, { FC, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { readAsBinaryStringFromFile } from 'shared/file';
import styled from 'styled-components';
import { CertificateConfigType } from 'typings/project';
import { Radio } from 'antd';
import ReadFile from 'components/ReadFile';
import classNames from 'classnames';
import { MixinCommonTransition } from 'styles/mixins';

const { Upload, BackendConfig } = CertificateConfigType;

const UploadContainer = styled.div`
  ${MixinCommonTransition(['max-height', 'opacity', 'padding-top'])};
  padding-top: 15px;
  max-height: 400px;
  will-change: max-height;

  &.is-hidden {
    padding-top: 0;
    max-height: 0;
    opacity: 0;
  }
`;

type Props = {
  value?: string | null;
  disabled?: boolean;
  isEdit?: boolean;
  onChange?: (v: string) => void;
  onTypeChange?: (v: CertificateConfigType) => void;
};
const Certificate: FC<Props> = ({ value, isEdit, onChange, onTypeChange, disabled }) => {
  const [type, setType] = useState<CertificateConfigType>(
    isEdit ? (value ? Upload : BackendConfig) : Upload,
  );
  const [internalVal, setInternalVal] = useState<string>();
  const { t } = useTranslation();

  return (
    <div>
      <Radio.Group
        value={type}
        options={[
          {
            label: t('project.upload_certificate'),
            value: Upload,
          },
          {
            label: t('project.backend_config_certificate'),
            value: BackendConfig,
          },
        ]}
        optionType="button"
        onChange={onTypeChangeInternal}
        disabled={isEdit || disabled}
      />
      <UploadContainer className={classNames({ 'is-hidden': type !== Upload || isEdit })}>
        <ReadFile
          disabled={isEdit || disabled}
          accept=".gz"
          reader={readAsBinaryStringFromFile}
          value={internalVal}
          onChange={onFileChange as any}
        />
      </UploadContainer>
    </div>
  );

  function onFileChange(val: string) {
    onChange && onChange(val);
    setInternalVal(val);
  }
  function onTypeChangeInternal(event: any) {
    const val = event.target.value;
    setType(val);
    onTypeChange && onTypeChange(val);

    if (val === BackendConfig) {
      onChange && onChange(null as any);
      // HACK WARNING: Waiting for UploadContainer shrink animation finishded
      // then it's safe to set ReadFile value to null,
      // otherwise ReadFile's expand animation will break container's shrink animation
      setTimeout(() => setInternalVal(null as any), 200);
    }
  }
};

export default Certificate;
