import { Table } from '@arco-design/web-react';
import React, { FC, useMemo } from 'react';
import { useQuery } from 'react-query';
import { fetchChildrenDatasetList } from 'services/dataset';
import { formatTimestamp } from 'shared/date';
import { DatasetJobListItem, DatasetKindLabel } from 'typings/dataset';
import { TIME_INTERVAL } from 'shared/constants';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantList } from 'hooks';
import { Link } from 'react-router-dom';
import { DatasetDetailSubTabs } from '.';
import ImportProgress from '../DatasetList/ImportProgress';

const getTableColumns = (allParticipantName: string) => {
  return [
    {
      title: '名称',
      dataIndex: 'name',
      name: 'name',
      render: (id: string, record: DatasetJobListItem) => {
        return (
          <Link
            to={`/datasets/${DatasetKindLabel.PROCESSED}/detail/${record.id}/${DatasetDetailSubTabs.DatasetJobDetail}`}
          >
            {record.name}
          </Link>
        );
      },
    },
    {
      title: '数据集状态',
      dataIndex: 'state_frontend',
      width: 180,
      render: (_: any, record: any) => {
        return <ImportProgress dataset={record} />;
      },
    },
    {
      title: '参与方',
      dataIndex: '__participant_name__',
      name: '__participant_name__',
      render: () => allParticipantName,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      name: 'created_at',
      sorter(a: DatasetJobListItem, b: DatasetJobListItem) {
        return a.created_at - b.created_at;
      },
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
  ];
};

type Props = {
  datasetId: ID;
};

const ProcessedDatasetTable: FC<Props> = ({ datasetId }) => {
  const projectId = useGetCurrentProjectId();
  const participantList = useGetCurrentProjectParticipantList();

  const listQuery = useQuery(
    ['fetchChildrenDatasetList', datasetId],
    () => {
      return fetchChildrenDatasetList(datasetId!);
    },
    {
      enabled: Boolean(projectId && datasetId),
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
    },
  );

  const filteredList = useMemo(() => {
    if (!listQuery.data) {
      return [];
    }
    const list = listQuery.data.data || [];

    // desc sort
    list.sort((a, b) => b.created_at - a.created_at);

    return list;
  }, [listQuery.data]);

  const allParticipantName = useMemo(() => {
    return participantList.map((item) => item.name).join('\n');
  }, [participantList]);

  return (
    <Table
      loading={listQuery.isFetching}
      data={filteredList || []}
      scroll={{ x: '100%' }}
      columns={getTableColumns(allParticipantName)}
      rowKey="uuid"
    />
  );
};

export default ProcessedDatasetTable;
