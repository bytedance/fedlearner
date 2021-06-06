import React, { FC } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import { Container, JobName, JobStatusText, StatusIcon, InheritedTag } from './elements';
import { executionStatusText, JobNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';
import classNames from 'classnames';
import { useTranslation } from 'react-i18next';
import { Tooltip } from 'antd';
import { ChartNodeStatus } from '../types';

const ExecutionJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const hasError = Boolean(data.raw.error_message);
  const isDisabled = Boolean(data.raw.disabled);

  const { t } = useTranslation();
  const icon = statusIcons[hasError ? ChartNodeStatus.Error : data.status];
  const text = executionStatusText[data.status];

  return (
    <Container
      data-disabled={isDisabled.toString()}
      data-has-error={hasError.toString()}
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
          <JobStatusText>
            {hasError ? (
              <Tooltip className="error-message" title={data.raw.error_message} placement="topLeft">
                {data.raw.error_message}
              </Tooltip>
            ) : (
              text
            )}
          </JobStatusText>

          {data.raw.reused && (
            <Tooltip title={t('workflow.msg_resued_job')} placement="bottom">
              <InheritedTag color="orange">{t('workflow.job_node_reused')}</InheritedTag>
            </Tooltip>
          )}
        </GridRow>
      )}
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );
};

export default ExecutionJobNode;
