import React, { FC } from 'react';
import styled from 'styled-components';
import { Table } from 'antd';
import { Pod, PodState } from 'typings/job';
import i18n from 'i18n';
import { Button } from 'antd';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { useTranslation } from 'react-i18next';

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
          <Button type="link" size="small">
            {i18n.t('workflow.btn_inspect_logs')}
          </Button>
        </>
      );
    },
  },
];

type Props = {
  pods: Pod[];
};

const JobExecutionPODs: FC<Props> = ({ pods }) => {
  const { t } = useTranslation();
  let data = pods;
  if (!Array.isArray(pods)) {
    data = [];
  }
  return (
    <Container>
      <h3>{t('workflow.label_pod_list')}</h3>
      <Table dataSource={data || []} columns={tablecolumns} size="small" />
    </Container>
  );
};

export default JobExecutionPODs;
