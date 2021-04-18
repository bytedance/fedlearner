import React, { FC, useEffect, useMemo, useRef } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { Button, ButtonProps, Dropdown, Menu, Tooltip } from 'antd';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import AccessSwitch from './AccessSwitch';
import { Workflow } from 'typings/workflow';
import { useToggle } from 'react-use';
import { toggleMetricsPublic, toggleWofklowForkable } from 'services/workflow';
import { giveWeakRandomKey } from 'shared/helpers';
import { QuestionCircle } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';

const StyledMenu = styled(Menu)`
  width: 250px;
  padding: 8px 5px;
  background-color: #edeeee;
  border-radius: 5px;
`;

const ControlItem = styled(Menu.Item)`
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 38px;
  padding: 0 13px;
  border-radius: 5px;

  &:hover {
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  }
`;

const ResourceName = styled.strong`
  font-size: 14px;
`;

const WorkflowAccessControl: FC<ButtonProps & { workflow: Workflow; onSuccess?: any }> = (
  props,
) => {
  const uuid = useMemo(() => giveWeakRandomKey(), []);
  const { t } = useTranslation();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [visible, toggleVisible] = useToggle(false);

  // Click away hide the dropdown
  useEffect(() => {
    const handler = (event: MouseEvent) => {
      const el = document.getElementById(uuid);
      if (!el) return;

      if (event.target && !el.contains(event.target as any)) {
        if (!buttonRef.current?.contains(event.target as any)) {
          toggleVisible(false);
        }
      }
    };

    document.addEventListener('click', handler);

    return () => document.removeEventListener('click', handler);
  }, [uuid, toggleVisible]);

  return (
    <ErrorBoundary>
      <Dropdown
        visible={visible}
        overlay={
          <StyledMenu id={uuid}>
            <ControlItem>
              <ResourceName>{t('workflow.label_forkable')}</ResourceName>
              <AccessSwitch
                keyOfSource="forkable"
                patcher={toggleWofklowForkable}
                workflow={props.workflow}
                onSuccess={onAccessChange}
              />
            </ControlItem>
            <Menu.Divider />
            <ControlItem>
              <GridRow gap="5">
                <ResourceName>{t('workflow.label_metric_public')}</ResourceName>
                <Tooltip title={t('workflow.msg_metric_public')}>
                  <QuestionCircle style={{ fontSize: '12px' }} />
                </Tooltip>
              </GridRow>
              <AccessSwitch
                keyOfSource="metric_is_public"
                patcher={toggleMetricsPublic}
                workflow={props.workflow}
                onSuccess={onAccessChange}
              />
            </ControlItem>
          </StyledMenu>
        }
        placement="bottomCenter"
      >
        <Button ref={buttonRef} {...props} onClick={() => toggleVisible()}>
          {t('workflow.btn_access_ctrl')}
        </Button>
      </Dropdown>
    </ErrorBoundary>
  );

  function onAccessChange() {
    props.onSuccess && props.onSuccess();
  }
};

export default WorkflowAccessControl;
