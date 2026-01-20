import React, { FC, useState } from 'react';
import { Handle, Position } from 'react-flow-renderer';
import { Container, JobName, JobStatusText, StatusIcon, InheritedTag } from './elements';
import { configStatusText, JobNodeProps, statusIcons } from './shared';
import GridRow from 'components/_base/GridRow';
import { QuestionCircle } from 'components/IconPark';
import { useTranslation } from 'react-i18next';
import { Tooltip } from '@arco-design/web-react';

const ConfigJobNode: FC<JobNodeProps> = ({ data, id }) => {
  const { t } = useTranslation();
  const [useRawDisabled] = useState(true);

  const icon = statusIcons[data.status];
  const text = configStatusText[data.status];

  const isDisabled = Boolean(useRawDisabled ? data.raw.disabled : data.disabled);
  const isReused = Boolean(data.raw.reused);

  return (
    <Container data-disabled={isDisabled} data-reused={isReused}>
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>

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

          {isReused && (
            <Tooltip content={t('workflow.msg_resued_job')} position="bottom">
              <InheritedTag color="orange">{t('workflow.job_node_reused')}</InheritedTag>
            </Tooltip>
          )}
        </GridRow>
      )}

      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  );
};

export default ConfigJobNode;
