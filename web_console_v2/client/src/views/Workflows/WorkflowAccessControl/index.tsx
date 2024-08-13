import React, { FC, useEffect, useMemo, useRef } from 'react';
import styled from './index.module.less';
import { useTranslation } from 'react-i18next';
import { Button, ButtonProps, Dropdown, Tooltip } from '@arco-design/web-react';
import ErrorBoundary from 'components/ErrorBoundary';
import AccessSwitch from './AccessSwitch';
import { Workflow } from 'typings/workflow';
import { useToggle } from 'react-use';
import { toggleMetricsPublic, toggleWofklowForkable } from 'services/workflow';
import { giveWeakRandomKey } from 'shared/helpers';
import { IconQuestionCircle } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import PrettyMenu, { PrettyMenuItem } from 'components/PrettyMenu';

const WorkflowAccessControl: FC<ButtonProps & { workflow: Workflow; onSuccess?: any }> = ({
  onSuccess,
  workflow,
  ...restProps
}) => {
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
        popupVisible={visible}
        droplist={
          <PrettyMenu id={uuid}>
            <PrettyMenuItem key="forkable">
              <strong className={styled.resource_name}>{t('workflow.label_forkable')}</strong>
              <AccessSwitch
                keyOfSource="forkable"
                patcher={toggleWofklowForkable}
                workflow={workflow}
                onSuccess={onAccessChange}
              />
            </PrettyMenuItem>
            <PrettyMenuItem key="metric">
              <GridRow gap="5">
                <strong className={styled.resource_name}>
                  {t('workflow.label_metric_public')}
                </strong>
                <Tooltip content={t('workflow.msg_metric_public')}>
                  <IconQuestionCircle style={{ fontSize: '12px' }} />
                </Tooltip>
              </GridRow>
              <AccessSwitch
                keyOfSource="metric_is_public"
                patcher={toggleMetricsPublic}
                workflow={workflow}
                onSuccess={onAccessChange}
              />
            </PrettyMenuItem>
          </PrettyMenu>
        }
        position="bottom"
      >
        <Button ref={buttonRef} {...restProps} onClick={() => toggleVisible()}>
          {t('workflow.btn_access_ctrl')}
        </Button>
      </Dropdown>
    </ErrorBoundary>
  );

  function onAccessChange() {
    onSuccess?.();
  }
};

export default WorkflowAccessControl;
