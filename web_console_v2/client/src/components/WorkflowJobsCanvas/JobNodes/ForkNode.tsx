import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import {
  Container,
  JobName,
  JobStatusText,
  InheritButton,
  StatusIcon,
  ArrowDown,
  InheritMentItem,
} from './elements';
import { configStatusText, JobNodeProps, statusIcons, WORKFLOW_JOB_NODE_CHANNELS } from './shared';
import GridRow from 'components/_base/GridRow';
import { useTranslation } from 'react-i18next';
import classNames from 'classnames';
import { Dropdown, Modal, Menu } from 'antd';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { MenuInfo } from 'rc-menu/lib/interface';
import DisabledSwitch from './DisabledSwitch';
import PubSub from 'pubsub-js';
import { QuestionCircle } from 'components/IconPark';
import { Tooltip } from 'antd';

const ForkJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const { t } = useTranslation();
  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

  const labelReusable = t('workflow.label_job_reuseable');
  const labelNonreusable = t('workflow.label_job_nonreusable');

  const isDisabled = Boolean(data.disabled);

  return (
    <Container
      data-inherited={data.inherited!.toString()}
      data-disabled={isDisabled.toString()}
      className={classNames([data.raw.is_federated && 'federated-mark', data.mark])}
    >
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>

      <DisabledSwitch size="small" checked={!isDisabled} onChange={onDisabledChange} />

      {isDisabled ? (
        <Tooltip title={t('workflow.msg_diable_job_will_cause')} placement="bottomLeft">
          <GridRow gap="4" style={{ fontSize: '11px' }}>
            <JobStatusText>{t('workflow.job_node_disabled')}</JobStatusText>
            <QuestionCircle />
          </GridRow>
        </Tooltip>
      ) : (
        <GridRow gap={5}>
          {icon && <StatusIcon src={icon} />}
          <JobStatusText>{text}</JobStatusText>
        </GridRow>
      )}

      <Dropdown
        overlay={
          <Menu>
            <InheritMentItem key="0" onClick={(e) => changeInheritance(e, true)}>
              {labelReusable}
            </InheritMentItem>
            <InheritMentItem key="1" onClick={(e) => changeInheritance(e, false)}>
              {labelNonreusable}
            </InheritMentItem>
          </Menu>
        }
      >
        <InheritButton
          data-inherited={data.inherited!.toString()}
          onClick={(e) => e.stopPropagation()}
        >
          {data.inherited ? labelReusable : labelNonreusable} <ArrowDown />
        </InheritButton>
      </Dropdown>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );

  function onDisabledChange(val: boolean) {
    PubSub.publish(WORKFLOW_JOB_NODE_CHANNELS.disable_job, { id, data, disabled: !val });
  }

  function changeInheritance(event: MenuInfo, whetherInherit: boolean) {
    event.domEvent.stopPropagation();

    if (whetherInherit === data.inherited) {
      return;
    }

    Modal.confirm({
      title: t('workflow.title_toggle_reusable', {
        state: whetherInherit ? labelReusable : labelNonreusable,
      }),
      zIndex: Z_INDEX_GREATER_THAN_HEADER,
      icon: null,
      content: whetherInherit
        ? t('workflow.msg_reuse_noti', {
            name: id,
          })
        : t('workflow.msg_non_reuse_noti', {
            name: id,
          }),

      mask: false,
      okText: t('confirm'),
      cancelText: t('cancel'),
      style: {
        top: '35%',
      },
      onOk() {
        PubSub.publish(WORKFLOW_JOB_NODE_CHANNELS.change_inheritance, { id, data, whetherInherit });
      },
    });
  }
};

export default ForkJobNode;
