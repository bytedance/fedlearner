import React, { FC } from 'react';
import styled from 'styled-components';
import { Table } from 'antd';
import { Pod, PodState } from 'typings/job';
import i18n from 'i18n';
import { Button } from 'antd';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { useTranslation } from 'react-i18next';
import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/helpers';

const Container = styled.div`
  margin-top: 30px;
`;

const stateType: { [key: string]: StateTypes } = {
  [PodState.COMPLETE]: 'success',
  [PodState.RUNNING]: 'processing',
  [PodState.FAILED]: 'error',
  [PodState.PENDING]: 'warning',
  [PodState.UNKNOWN]: 'default',
  [PodState.FL_FAILED]: 'error',
  [PodState.FL_SUCCEED]: 'success',
};
const stateText: { [key: string]: string } = {
  [PodState.COMPLETE]: i18n.t('workflow.job_node_success'),
  [PodState.RUNNING]: i18n.t('workflow.job_node_running'),
  [PodState.FAILED]: i18n.t('workflow.job_node_failed'),
  [PodState.PENDING]: i18n.t('workflow.job_node_waiting'),
  [PodState.UNKNOWN]: i18n.t('workflow.pod_unknown'),
  [PodState.FL_FAILED]: '清理资源失败',
  [PodState.FL_SUCCEED]: '清理资源完成',
};

type Props = {
  job: NodeDataRaw;
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
      ellipsis: true,
      width: 380,
    },
    {
      title: i18n.t('workflow.col_worker_status'),
      dataIndex: 'status',
      key: 'status',
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
      width: 160,
      render: (_: any, record: Pod) => {
        return (
          <div style={{ marginLeft: '-13px' }}>
            <Button type="link" size="small" disabled={record.status !== PodState.RUNNING}>
              Shell
            </Button>
            <Button type="link" size="small" onClick={() => goInspectLogs(record)}>
              {i18n.t('workflow.btn_inspect_logs')}
            </Button>
          </div>
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
