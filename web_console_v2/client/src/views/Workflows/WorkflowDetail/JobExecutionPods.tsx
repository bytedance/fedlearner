import React, { FC } from 'react';
import styled from 'styled-components';
import { Table } from 'antd';
import { Pod, PodState } from 'typings/job';
import i18n from 'i18n';
import { Button } from 'antd';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { useTranslation } from 'react-i18next';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';

const Container = styled.div`
  margin-top: 30px;
`;

const stateType: { [key: string]: StateTypes } = {
  [PodState.COMPLETED]: 'success',
  [PodState.RUNNING]: 'processing',
  [PodState.FAILED]: 'error',
  [PodState.PENDING]: 'warning',
  [PodState.UNKNOWN]: 'default',
  [PodState.FL_FAILED]: 'warning',
  [PodState.FL_SUCCEED]: 'success',
};
const stateText: { [key: string]: string } = {
  [PodState.COMPLETED]: i18n.t('workflow.job_node_success'),
  [PodState.RUNNING]: i18n.t('workflow.job_node_running'),
  [PodState.FAILED]: i18n.t('workflow.job_node_failed'),
  [PodState.PENDING]: i18n.t('workflow.job_node_waiting'),
  [PodState.UNKNOWN]: i18n.t('workflow.pod_unknown'),
  [PodState.FL_FAILED]: i18n.t('workflow.pod_failed_cleared'),
  [PodState.FL_SUCCEED]: i18n.t('workflow.pod_success_cleared'),
};

type Props = {
  job: JobNodeRawData;
  isPeerSide: boolean;
};

const JobExecutionPods: FC<Props> = ({ job, isPeerSide }) => {
  const { t } = useTranslation();

  let data = job.pods;

  if (!Array.isArray(job.pods)) {
    data = [];
  }

  const tablecolumns = [
    {
      title: i18n.t('workflow.col_pod_name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 380,
    },
    {
      title: i18n.t('workflow.col_worker_status'),
      dataIndex: 'status',
      key: 'status',
      render: (val: PodState, record: Pod) => {
        let tip: string = '';
        if ([PodState.FAILED, PodState.PENDING].includes(record.status)) {
          tip = record.message || '';
        }
        return <StateIndicator type={stateType[val]} text={stateText[val]} tip={tip} />;
      },
    },
    {
      title: i18n.t('workflow.col_worker_type'),
      dataIndex: 'pod_type',
      key: 'pod_type',
    },
  ];

  if (!isPeerSide) {
    tablecolumns.push({
      title: i18n.t('workflow.col_actions'),
      dataIndex: 'actions',
      key: 'actions',
      width: 160,
      render: (_: any, record: Pod) => {
        return (
          <div style={{ marginLeft: '-13px' }}>
            {/* TODO: Enable Shell */}
            {/* <Button type="link" size="small" disabled={record.status !== PodState.RUNNING}>
              Shell
            </Button> */}
            <Button type="link" size="small" onClick={() => goInspectLogs(record)}>
              {i18n.t('workflow.btn_inspect_logs')}
            </Button>
          </div>
        );
      },
    } as any);
  }

  return (
    <Container>
      <h3>{t('workflow.label_pod_list')}</h3>
      <Table dataSource={data || []} columns={tablecolumns} size="small" />
    </Container>
  );

  function goInspectLogs(pod: Pod) {
    window.open(`/v2/logs/pod/${job.id}/${pod.name}`, '_blank noopener');
  }
};

export default JobExecutionPods;
