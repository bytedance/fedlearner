import React, { FC } from 'react';
import styled from 'styled-components';
import { Table } from 'antd';
import { Pod, PodState } from 'typings/job';
import i18n from 'i18n';
import { Button } from 'antd';
import StateIndicator, { StateTypes } from 'components/StateIndicator';

const Container = styled.div`
  margin-top: 30px;
`;

const stateType: { [key: string]: StateTypes } = {
  [PodState.COMPLETE]: 'success',
  [PodState.RUNNING]: 'processing',
  [PodState.FAILED]: 'error',
};
const stateText: { [key: string]: string } = {
  [PodState.COMPLETE]: '成功',
  [PodState.RUNNING]: '运行中',
  [PodState.FAILED]: '失败',
};
const tablecolumns = [
  {
    title: i18n.t('workflow.name'),
    dataIndex: 'name',
    key: 'name',
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
            查看日志
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
  return (
    <Container>
      <h3>各 worker 运行日志及状态</h3>
      <Table dataSource={pods || []} columns={tablecolumns} size="small" />
    </Container>
  );
};

export default JobExecutionPODs;
