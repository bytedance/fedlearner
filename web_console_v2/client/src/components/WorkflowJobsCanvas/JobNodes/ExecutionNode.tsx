import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import { Container, JobName, JobStatusText, StatusIcon, InheritedTag } from './elements';
import { executionStatusText, JobNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';
import classNames from 'classnames';
import { useTranslation } from 'react-i18next';

const ExecutionJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const { t } = useTranslation();
  const icon = statusIcons[data.status];
  const text = executionStatusText[data.status];

  const isDisabled = Boolean(data.raw.disabled);

  return (
    <Container
      data-disabled={isDisabled.toString()}
      className={classNames([data.raw.is_federated && 'federated-mark', data.mark])}
    >
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>
      {isDisabled ? (
        <GridRow gap="4" style={{ fontSize: '11px' }}>
          <JobStatusText>{t('workflow.job_node_disabled')}</JobStatusText>
        </GridRow>
      ) : (
        <GridRow gap={5}>
          {icon && <StatusIcon src={icon} />}
          <JobStatusText>{text}</JobStatusText>

          {data.raw.reused && (
            <InheritedTag color="orange">{t('workflow.job_node_reused')}</InheritedTag>
          )}
        </GridRow>
      )}
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );
};

export default ExecutionJobNode;
