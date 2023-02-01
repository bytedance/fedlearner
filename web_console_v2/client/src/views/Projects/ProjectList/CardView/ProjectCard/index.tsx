import React, { ReactElement } from 'react';
import { useGetCurrentPureDomainName } from 'hooks';
import { Tooltip, Grid, Tag, Space, Divider } from '@arco-design/web-react';
import ProjectMoreActions from '../../../ProjectMoreActions';
import CreateTime from '../../../CreateTime';
import ProjectName from '../../../ProjectName';
import {
  Project,
  ProjectListType,
  ProjectStateType,
  ProjectTicketStatus,
  RoleType,
} from 'typings/project';
import { ParticipantType } from 'typings/participant';
import { getCoordinateName, PARTICIPANT_TYPE_TAG_MAPPER } from 'views/Projects/shard';
import { ProjectProgress } from 'views/Projects/shard';

import styles from './index.module.less';

const { Row, Col } = Grid;

interface CardProps {
  item: Project;
  projectListType: ProjectListType;
  onViewDetail: (project: Project) => void;
  onDeleteProject: (projectId: ID, projectListType: ProjectListType) => void;
}

function Card({
  item: project,
  onViewDetail,
  projectListType,
  onDeleteProject,
}: CardProps): ReactElement {
  const myPureDomainName = useGetCurrentPureDomainName();
  const tagConfig =
    PARTICIPANT_TYPE_TAG_MAPPER?.[project?.participant_type || ParticipantType.PLATFORM];

  return (
    <div className={styles.card_container}>
      <div className={styles.card_header} onClick={viewDetail}>
        <div className={styles.card_header_left}>
          <ProjectName text={project.name} />
        </div>
        <ProjectMoreActions
          project={project}
          projectListType={projectListType}
          role={
            project?.participants_info?.participants_map?.[myPureDomainName]?.role ??
            RoleType.COORDINATOR
          }
          onDeleteProject={onDeleteProject}
        />
      </div>

      <div className={styles.card_main} onClick={viewDetail}>
        {`${String(project.num_workflow || 0)}个任务`}
      </div>
      <div>
        <Space split={<Divider type="vertical" />}>
          <Tag color={tagConfig.color}>{tagConfig.label}</Tag>
          <Tag color="gray">{`${
            project?.participants_info?.participants_map?.[myPureDomainName]?.role ===
            RoleType.COORDINATOR
              ? '我方'
              : getCoordinateName(project?.participants_info?.participants_map) ?? '我方'
          }创建`}</Tag>
        </Space>
      </div>
      <Row gutter={24} className={styles.card_footer} align="center">
        <Col span={6} className={styles.card_footer_left}>
          <ProjectProgress
            ticketStatus={
              project.state === ProjectStateType.FAILED
                ? ProjectTicketStatus.FAILED
                : project.ticket_status
            }
          />
        </Col>
        <Col span={18} className={styles.card_footer_right}>
          <Tooltip content={project.creator ?? project.creator_username}>
            <div className={styles.participant_name}>
              {project.creator ?? project.creator_username ?? '-'}
            </div>
          </Tooltip>
          <Divider type="vertical" />
          <CreateTime className={styles.create_time} time={project.created_at} />
        </Col>
      </Row>
    </div>
  );

  function viewDetail() {
    onViewDetail(project);
  }
}

export default Card;
