import React, { ReactElement, useRef } from 'react';
import { useGetCurrentPureDomainName } from 'hooks';
import { Button, Table, Tag } from '@arco-design/web-react';
import ProjectConnectionStatus, { ExposedRef } from 'views/Projects/ConnectionStatus';
import ProjectMoreActions from 'views/Projects/ProjectMoreActions';
import GridRow from 'components/_base/GridRow';
import { ParticipantType } from 'typings/participant';
import {
  Project,
  ProjectBlockChainType,
  ProjectListType,
  ProjectStateType,
  ProjectTicketStatus,
  RoleType,
} from 'typings/project';
import { formatTimestamp } from 'shared/date';
import { ProjectProgress } from '../../shard';
import { getCoordinateName, PARTICIPANT_TYPE_TAG_MAPPER } from '../../shard';
import { CONSTANTS } from 'shared/constants';
import styles from './index.module.less';

interface TableListProps {
  list: Project[];
  onViewDetail: (project: Project) => void;
  onParticipantTypeChange: (value: string[]) => void;
  participantType?: string[];
  projectLisType: ProjectListType;
  onDeleteProject: (projectId: ID, projectListType: ProjectListType) => void;
}

function TableList({
  list,
  onViewDetail,
  onParticipantTypeChange,
  participantType,
  projectLisType,
  onDeleteProject,
}: TableListProps): ReactElement {
  const myDomainName = useGetCurrentPureDomainName();

  const projectConnectionStatusListRef = useRef<ExposedRef[]>(
    list.map((_) => {
      return {
        checkConnection: () => {},
      };
    }),
  );

  const statefulList = list.map((item, index) => {
    return {
      ...item,
      onCheckConnectionClick: () => {
        if (
          projectConnectionStatusListRef.current &&
          projectConnectionStatusListRef.current[index] &&
          projectConnectionStatusListRef.current[index].checkConnection
        ) {
          projectConnectionStatusListRef.current[index].checkConnection();
        }
      },
    };
  });

  const columns = [
    {
      title: '工作区名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record: Project) => {
        return (
          <span className={styles.project_name} onClick={() => onViewDetail(record)}>
            {name}
          </span>
        );
      },
    },
    {
      title: '任务数',
      dataIndex: 'num_workflow',
      name: 'num_workflow',
      width: 80,
      render: (value: any) => value ?? 0,
    },
    {
      title: '区块链存证',
      dataIndex: 'config.support_blockchain',
      name: 'config.support_blockchain',
      width: 100,
      render: (value: boolean) =>
        value ? ProjectBlockChainType.OPEN : ProjectBlockChainType.CLOSED,
    },
    {
      title: '审批状态',
      dataIndex: 'ticket_status',
      name: 'ticket_status',
      width: 100,
      render: (value: any, record: any) => (
        <ProjectProgress
          ticketStatus={
            record.state === ProjectStateType.FAILED ? ProjectTicketStatus.FAILED : value
          }
        />
      ),
    },
    {
      title: '连接状态',
      dataIndex: 'status',
      name: 'status',
      width: 100,
      render: (_: any, record: Project, index: number) => {
        const isLightClient = record.participant_type === ParticipantType.LIGHT_CLIENT;
        if (isLightClient || projectLisType === ProjectListType.PENDING) {
          return CONSTANTS.EMPTY_PLACEHOLDER;
        }

        return (
          <ProjectConnectionStatus
            project={record}
            ref={(ref) => (projectConnectionStatusListRef.current[index] = ref!)}
          />
        );
      },
    },
    {
      title: '合作伙伴类型',
      dataIndex: 'participant_type',
      width: 120,
      filters: [
        {
          text: '轻量级',
          value: ParticipantType.LIGHT_CLIENT,
        },
        {
          text: '标准',
          value: ParticipantType.PLATFORM,
        },
      ],
      defaultFilters: participantType ?? [],
      render: (value: ParticipantType) => (
        <Tag color={PARTICIPANT_TYPE_TAG_MAPPER?.[value || ParticipantType.PLATFORM].color}>
          {PARTICIPANT_TYPE_TAG_MAPPER?.[value || ParticipantType.PLATFORM].label}
        </Tag>
      ),
    },
    {
      title: '创建方',
      dataIndex: 'participants_info',
      name: 'participants_info',
      width: 100,
      render: (value: any) => (
        <Tag>
          {value?.participants_map?.[myDomainName]?.role === RoleType.COORDINATOR
            ? '我方'
            : getCoordinateName(value?.participants_map) ?? '我方'}
        </Tag>
      ),
    },
    {
      title: '创建人',
      dataIndex: 'creator',
      name: 'creator',
      render: (creator: string, record: Project) =>
        creator || record.creator_username || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      name: 'created_at',
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },

    {
      title: '操作',
      dataIndex: 'operation',
      name: 'operation',
      fixed: 'right' as any,
      width: 140,
      render: (_: any, record: Project & { onCheckConnectionClick: any }) => (
        <GridRow left={-12}>
          <Button
            size="mini"
            type="text"
            onClick={record.onCheckConnectionClick}
            disabled={
              record.participant_type === ParticipantType.LIGHT_CLIENT ||
              projectLisType === ProjectListType.PENDING
            }
          >
            检查连接
          </Button>
          <ProjectMoreActions
            project={record}
            projectListType={projectLisType}
            role={
              record?.participants_info?.participants_map?.[myDomainName]?.role ??
              RoleType.COORDINATOR
            }
            onDeleteProject={onDeleteProject}
          />
        </GridRow>
      ),
    },
  ];
  return (
    <div className={styles.table_list_container}>
      <Table
        className="custom-table"
        data={statefulList}
        columns={columns}
        rowKey="id"
        scroll={{ x: '100%' }}
        pagination={false}
        onChange={(_paginationProps, _sorterResult, filters) => {
          onParticipantTypeChange(filters.participant_type!);
        }}
      />
    </div>
  );
}

export default TableList;
