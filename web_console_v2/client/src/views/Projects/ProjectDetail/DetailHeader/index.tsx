import React, { ReactElement, useRef } from 'react';
import { useGetCurrentPureDomainName } from 'hooks';
import ProjectConnectionStatus, { ExposedRef } from '../../ConnectionStatus';
import GridRow from 'components/_base/GridRow';
import { Button, Grid, Popover, Space, Table, Tag, Tooltip } from '@arco-design/web-react';
import ProjectMoreActions from 'views/Projects/ProjectMoreActions';
import PropertyList from 'components/PropertyList';
import { formatTimestamp } from 'shared/date';
import { ParticipantType } from 'typings/participant';
import {
  Project,
  ProjectListType,
  ProjectStateType,
  ProjectTicketStatus,
  RoleType,
  ProjectBlockChainType,
  ProjectTaskType,
  ProjectActionType,
  ProjectAbilityType,
} from 'typings/project';
import { CONSTANTS } from 'shared/constants';
import {
  PARTICIPANT_TYPE_TAG_MAPPER,
  ProjectProgress,
  PROJECT_ABILITY_LABEL_MAPPER,
  PROJECT_TASK_LABEL_MAPPER,
  resetAbilitiesTableData,
} from '../../shard';

import styles from './index.module.less';

interface Props {
  project: Project;
  projectListType: ProjectListType;
  onDeleteProject: (projectId: ID, projectListType: ProjectListType) => void;
}

const { Row } = Grid;
const variableColumns = [
  {
    title: 'name',
    dataIndex: 'name',
  },
  {
    title: 'value',
    dataIndex: 'value',
  },
];
const abilitiesColumns = [
  {
    title: '能力',
    dataIndex: 'ability',
    render: (value: ProjectActionType) => PROJECT_TASK_LABEL_MAPPER?.[value],
  },
  {
    title: '授权策略',
    dataIndex: 'rule',
    render: (value: ProjectAbilityType) => PROJECT_ABILITY_LABEL_MAPPER?.[value],
  },
];
const ABILITY_LABEL_MAPPER = {
  [ProjectTaskType.ALIGN]: 'ID对齐',
  [ProjectTaskType.HORIZONTAL]: '横向联邦学习',
  [ProjectTaskType.VERTICAL]: '纵向联邦学习',
  [ProjectTaskType.TRUSTED]: '可信分析服务',
};

function DetailHeader({ project, projectListType, onDeleteProject }: Props): ReactElement {
  const myPureDomainName = useGetCurrentPureDomainName();

  const projectConnectionStatusRef = useRef<ExposedRef>(null);

  const isLightClient = project?.participant_type === ParticipantType.LIGHT_CLIENT;
  const isPendingProject = projectListType === ProjectListType.PENDING;

  const properties = [
    { label: '工作区ID', value: project?.id ?? CONSTANTS.EMPTY_PLACEHOLDER },
    {
      label: '区块链存证 ',
      value: project?.config?.support_blockchain
        ? ProjectBlockChainType.OPEN
        : ProjectBlockChainType.CLOSED,
    },
    {
      label: '合作伙伴类型',
      value: (
        <Tag
          color={
            PARTICIPANT_TYPE_TAG_MAPPER?.[project?.participant_type || ParticipantType.PLATFORM]
              .color
          }
          size="small"
        >
          {
            PARTICIPANT_TYPE_TAG_MAPPER?.[project?.participant_type || ParticipantType.PLATFORM]
              .label
          }
        </Tag>
      ),
    },
    {
      label: '连接状态',
      value:
        !isLightClient && project && !isPendingProject ? (
          <ProjectConnectionStatus ref={projectConnectionStatusRef} project={project} />
        ) : (
          CONSTANTS.EMPTY_PLACEHOLDER
        ),
    },
    {
      label: '创建人',
      value: project?.creator || project?.creator_username || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      label: '创建时间',
      value: project?.created_at
        ? formatTimestamp(project.created_at)
        : CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      label: '环境变量',
      value: project?.config?.variables?.length ? (
        <Popover
          className={styles.popover_container}
          content={
            <Table
              className={styles.popover_table}
              columns={variableColumns}
              rowKey="name"
              data={project.config.variables}
              pagination={false}
            />
          }
          position="bottom"
        >
          <span className={styles.variables_color}>查看</span>
        </Popover>
      ) : (
        CONSTANTS.EMPTY_PLACEHOLDER
      ),
    },
    {
      label: '能力规格',
      value: project?.config?.abilities?.length ? (
        <Popover
          className={styles.popover_container}
          content={
            <Table
              className={styles.popover_table}
              columns={abilitiesColumns}
              rowKey="ability"
              data={resetAbilitiesTableData(project.config.action_rules)}
              pagination={false}
            />
          }
          position="bottom"
        >
          <span className={styles.variables_color}>
            {ABILITY_LABEL_MAPPER?.[project.config.abilities?.[0]]}
          </span>
        </Popover>
      ) : (
        CONSTANTS.EMPTY_PLACEHOLDER
      ),
    },
  ];

  return (
    <>
      <Row justify="space-between" align="center">
        <Row align="center" justify="space-between">
          <GridRow gap="12">
            <div
              className={styles.avatar_container}
              data-name={project?.name ? project.name.slice(0, 1) : CONSTANTS.EMPTY_PLACEHOLDER}
            />
            <div>
              <Space>
                <h3 className={styles.project_name}>{project?.name || '....'}</h3>
                <ProjectProgress
                  className={styles.project_progress}
                  ticketStatus={
                    project?.state === ProjectStateType.FAILED
                      ? ProjectTicketStatus.FAILED
                      : project?.ticket_status
                  }
                />
              </Space>
              <Tooltip content={project?.comment}>
                <small className={styles.comment}>
                  {project?.comment || CONSTANTS.EMPTY_PLACEHOLDER}
                </small>
              </Tooltip>
            </div>
          </GridRow>
        </Row>
        <GridRow gap="10" style={{ flexBasis: 'auto' }}>
          <Button
            size="small"
            onClick={onCheckConnectionClick}
            disabled={isLightClient || isPendingProject}
          >
            检查连接
          </Button>
          <GridRow>
            <ProjectMoreActions
              project={project}
              projectListType={projectListType}
              role={
                project?.participants_info?.participants_map?.[myPureDomainName]?.role ??
                RoleType.COORDINATOR
              }
              onDeleteProject={onDeleteProject}
            />
          </GridRow>
        </GridRow>
      </Row>
      <PropertyList properties={properties} cols={4} />
    </>
  );

  function onCheckConnectionClick() {
    if (projectConnectionStatusRef.current?.checkConnection) {
      projectConnectionStatusRef.current.checkConnection();
    }
  }
}

export default DetailHeader;
