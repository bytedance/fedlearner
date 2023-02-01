import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import { Container, JobName, JobStatusText, StatusIcon } from './elements';
import { configStatusText, JobNodeProps, statusIcons, WORKFLOW_JOB_NODE_CHANNELS } from './shared';
import GridRow from 'components/_base/GridRow';
import DisabledSwitch from './DisabledSwitch';
import PubSub from 'pubsub-js';
import { QuestionCircle } from 'components/IconPark';
import { useTranslation } from 'react-i18next';
import { Tooltip } from '@arco-design/web-react';

const ConfigJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const { t } = useTranslation();
  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

  const isDisabled = Boolean(data.disabled);

  return (
    <Container data-disabled={isDisabled.toString()}>
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>

      <DisabledSwitch size="small" checked={!isDisabled} onChange={onDisabledChange} />

      {isDisabled ? (
        <Tooltip content={t('workflow.msg_diable_job_will_cause')} position="bl">
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

      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );

  function onDisabledChange(val: boolean) {
    PubSub.publish(WORKFLOW_JOB_NODE_CHANNELS.disable_job, { id, data, disabled: !val });
  }
};

export default ConfigJobNode;
