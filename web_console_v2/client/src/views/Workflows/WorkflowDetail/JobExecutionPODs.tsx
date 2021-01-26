import React, { FC } from 'react';
import styled from 'styled-components';
import { Table } from 'antd';
import { Pod, PodState } from 'typings/job';
import i18n from 'i18n';
import { Button } from 'antd';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { useTranslation } from 'react-i18next';
import { JobRawData } from 'components/WorkflowJobsFlowChart/helpers';

const Container = styled.div`
  margin-top: 30px;
`;

const stateType: { [key: string]: StateTypes } = {
  [PodState.COMPLETE]: 'success',
  [PodState.RUNNING]: 'processing',
  [PodState.FAILED]: 'error',
};
const stateText: { [key: string]: string } = {
  [PodState.COMPLETE]: i18n.t('workflow.job_node_success'),
  [PodState.RUNNING]: i18n.t('workflow.job_node_running'),
  [PodState.FAILED]: i18n.t('workflow.job_node_failed'),
};

type Props = {
  job: JobRawData;
};

const JobExecutionPODs: FC<Props> = ({ job }) => {
  const { t } = useTranslation();

  let data = job.pods;

  if (!Array.isArray(job.pods)) {
    data = [];
  }

  const tablecolumns = [
    {
      title: i18n.t('workflow.name'),
      dataIndex: 'name',
      key: 'name',
      width: 400,
    },
    {
      title: i18n.t('workflow.col_worker_status'),
      dataIndex: 'state',
      key: 'state',
      render: (val: PodState) => <StateIndicator type={stateType[val]} text={stateText[val]} />,
    },
    {
      title: i18n.t('workflow.col_worker_type'),
      dataIndex: 'pod_type',
      key: 'pod_type',
    },

    {
      title: i18n.t('workflow.col_actions'),
      dataIndex: 'actions',
      key: 'actions',
      render: (_: any, record: Pod) => {
        return (
          <>
            <Button type="link" size="small" disabled={record.state !== PodState.RUNNING}>
              Shell
            </Button>
            <Button type="link" size="small" onClick={() => goInspectLogs(record)}>
              {i18n.t('workflow.btn_inspect_logs')}
            </Button>
          </>
        );
      },
    },
  ];

  return (
    <Container>
      <h3>{t('workflow.label_pod_list')}</h3>
      <Table dataSource={data || []} columns={tablecolumns} size="small" />
    </Container>
  );

  function goInspectLogs(pod: Pod) {
    window.open(`/v2/logs/pod/${job.id}/${pod.name}`, 'noopener');
  }
};

export default JobExecutionPODs;
