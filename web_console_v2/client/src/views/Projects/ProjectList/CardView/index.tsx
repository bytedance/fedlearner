import React, { ReactElement } from 'react';
import { Project, ProjectListType } from 'typings/project';
import ProjectCard from './ProjectCard';

import styles from './index.module.less';

interface CardListProps {
  list: Project[];
  onViewDetail: (project: Project) => void;
  projectListType: ProjectListType;
  onDeleteProject: (projectId: ID, projectListType: ProjectListType) => void;
}

function CardList({
  list,
  onViewDetail,
  projectListType,
  onDeleteProject,
}: CardListProps): ReactElement {
  return (
    <div className={styles.card_container}>
      {list.map((item, index) => (
        <ProjectCard
          item={item}
          key={item.id}
          onViewDetail={onViewDetail}
          projectListType={projectListType}
          onDeleteProject={onDeleteProject}
        />
      ))}
    </div>
  );
}

export default CardList;
