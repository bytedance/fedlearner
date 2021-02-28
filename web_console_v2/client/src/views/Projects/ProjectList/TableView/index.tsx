import React, { ReactElement, useState } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { Button, Table } from 'antd';
import { ConnectionStatus, Project } from 'typings/project';
import { useHistory } from 'react-router-dom';
import ProjectConnectionStatus from 'views/Projects/ConnectionStatus';
import Username from 'components/Username';
import { formatTimestamp } from 'shared/date';
import { checkConnection } from 'services/project';
import ProjectMoreActions from 'views/Projects/ProjectMoreActions';
import GridRow from 'components/_base/GridRow';

const Container = styled.div`
  width: 100%;
`;
const Name = styled.strong`
  color: var(--primaryColor);
  cursor: pointer;
  font-weight: 500;
  font-size: 13px;
`;

interface TableListProps {
  list: Project[];
  onViewDetail: (project: Project) => void;
}

function TableList({ list, onViewDetail }: TableListProps): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();

  const [statuses, setStatuses] = useState(
    list.map((_) => {
      return ConnectionStatus.Waiting;
    }),
  );

  const statefulList = list.map((item, index) => {
    const onCheckConnectionClick = async () => {
      try {
        setProjectStatus(index, ConnectionStatus.Checking);

        const res = await checkConnection(item.id);
        if (res.data.success) {
          setProjectStatus(index, ConnectionStatus.Success);
        } else {
          setProjectStatus(index, ConnectionStatus.Failed);
        }
      } catch (error) {
        setProjectStatus(index, ConnectionStatus.CheckFailed);
      }
    };
    return {
      ...item,
      onCheckConnectionClick,
    };
  });

  const columns = [
    {
      title: t('project.name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record: Project) => {
        return <Name onClick={() => onViewDetail(record)}>{name}</Name>;
      },
    },
    {
      title: t('project.connection_status'),
      dataIndex: 'status',
      name: 'status',
      width: 120,
      render: (_: any, record: Project, index: number) => (
        <ProjectConnectionStatus status={statuses[index]} />
      ),
    },
    {
      title: t('project.workflow_number'),
      dataIndex: 'num_workflow',
      name: 'num_workflow',
    },
    {
      title: t('project.creator'),
      dataIndex: 'creator',
      name: 'creator',
      render: (_: string) => <Username />,
    },
    {
      title: t('project.creat_time'),
      dataIndex: 'created_at',
      name: 'created_at',
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },

    {
      title: t('operation'),
      dataIndex: 'created_at',
      name: 'created_at',
      fixed: 'right' as any,
      width: 240,
      render: (_: any, record: Project & { onCheckConnectionClick: any }) => (
        <GridRow left={-12}>
          <Button size="small" type="link" onClick={record.onCheckConnectionClick}>
            {t('project.check_connection')}
          </Button>
          <Button
            size="small"
            type="link"
            onClick={() => history.push(`/workflows/initiate/basic?project=${record.id}`)}
          >
            {t('project.create_work_flow')}
          </Button>

          <ProjectMoreActions
            style={{ marginTop: '13px' }}
            onEdit={() => {
              history.push(`/projects/edit/${record.id}`);
            }}
            onViewDetail={() => onViewDetail(record)}
          />
        </GridRow>
      ),
    },
  ];
  return (
    <Container>
      <Table dataSource={statefulList} columns={columns} rowKey="name" scroll={{ x: '100%' }} />
    </Container>
  );

  function setProjectStatus(index: number, newStatus: ConnectionStatus) {
    let newStatuses = [...statuses];
    newStatuses[index] = newStatus;
    setStatuses(newStatuses);
  }
}

export default TableList;
