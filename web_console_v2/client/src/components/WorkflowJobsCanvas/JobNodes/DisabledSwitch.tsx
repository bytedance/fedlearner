import React, { FC } from 'react';
import styled from 'styled-components';
import { Switch, SwitchProps, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';

const Container = styled.div`
  position: absolute;
  right: 6px;
  top: 6px;
  transform: scale(0.8);
`;

const DisabledSwitch: FC<SwitchProps> = (props) => {
  const { t } = useTranslation();

  return (
    <Container onClick={(e) => e.stopPropagation()}>
      <Tooltip title={t('workflow.msg_toggle_job_disabled')}>
        <Switch {...props} />
      </Tooltip>
    </Container>
  );
};

export default DisabledSwitch;
