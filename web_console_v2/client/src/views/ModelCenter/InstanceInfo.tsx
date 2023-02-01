import React, { CSSProperties } from 'react';
import { Table } from '@arco-design/web-react';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import { useQuery } from 'react-query';
import { fetchJobById } from 'services/workflow';
import { useRecoilValue } from 'recoil';
import { projectState } from 'stores/project';
import StateIndicator from 'components/StateIndicator';
import { formatTimestamp } from 'shared/date';
import { Pod, PodState } from 'typings/job';
import { getPodState } from 'views/Workflows/shared';
import { Link } from 'react-router-dom';

type ColumnOptions = {
  id: ID;
  jobId: ID;
};

const getColumns = (options: ColumnOptions): ColumnProps[] => {
  return [
    {
      dataIndex: 'name',
      title: '实例 ID',
      width: 400,
    },
    {
      dataIndex: 'state',
      title: '运行状态',
      filters: [
        PodState.SUCCEEDED,
        PodState.RUNNING,
        PodState.FAILED,
        PodState.PENDING,
        PodState.FAILED_AND_FREED,
        PodState.SUCCEEDED_AND_FREED,
        PodState.UNKNOWN,
      ].map((state) => {
        const { text } = getPodState({ state } as Pod);
        return {
          text,
          value: state,
        };
      }),
      onFilter: (state, record: Pod) => {
        return record?.state === state;
      },
      render(state, record: Pod) {
        return <StateIndicator {...getPodState(record)} />;
      },
    },
    {
      dataIndex: 'creation_timestamp',
      title: '创建时间',
      width: 200,
      render(value) {
        return formatTimestamp(value);
      },
    },
    {
      key: 'operate',
      title: '操作',
      render(_, record: Pod) {
        return (
          <Link target={'_blank'} to={`/logs/pod/${options.jobId}/${record.name}`}>
            查看日志
          </Link>
        );
      },
    },
  ];
};

const PAGE_SIZE = 10;

const InstanceInfo: React.FC<{ id: ID; jobId: ID; style?: CSSProperties }> = ({
  id,
  jobId,
  style,
}) => {
  const selectedProject = useRecoilValue(projectState);
  const projectId = selectedProject.current?.id;
  const { data } = useQuery(
    ['workflow', '/jobs/:job_id'],
    () => fetchJobById(jobId as number).then((res) => res.data.pods),
    {
      enabled: Boolean(projectId),
    },
  );

  return (
    <>
      <Table
        rowKey="name"
        data={data}
        style={{ marginTop: 20, ...style }}
        className="custom-table custom-table-left-side-filter"
        columns={getColumns({
          id,
          jobId,
        })}
        pagination={!data || data.length <= PAGE_SIZE ? false : { pageSize: PAGE_SIZE }}
      />
    </>
  );
};

export default InstanceInfo;
