import React, { ReactElement } from 'react';
import { useHistory } from 'react-router';
import MoreActions from 'components/MoreActions';
import { Project, ProjectListType, RoleType } from 'typings/project';

interface ProjectMoreActionsProps {
  project: Project;
  projectListType: ProjectListType;
  role: RoleType;
  onDeleteProject: (projectId: ID, projectListType: ProjectListType) => void;
}

function ProjectMoreActions({
  project,
  role,
  projectListType,
  onDeleteProject,
}: ProjectMoreActionsProps): ReactElement {
  const history = useHistory();
  //todo: Uncomment when editing pendingProjects is supported
  // const editDisable =
  //   project.ticket_status === ProjectTicketStatus.PENDING ||
  //   (role === RoleType.PARTICIPANT && project.state !== ProjectStateType.ACCEPTED);
  const editDisable = projectListType === ProjectListType.PENDING;
  //todo: Uncomment when deleting project is supported
  // const deleteDisable = role === RoleType.PARTICIPANT;
  const deleteDisable =
    projectListType === ProjectListType.COMPLETE || role === RoleType.PARTICIPANT;
  return (
    <MoreActions
      actionList={[
        {
          label: '编辑',
          onClick: handleEdit,
          disabled: editDisable,
        },
        {
          label: '删除',
          onClick: () => {
            onDeleteProject(project.id, projectListType);
          },
          disabled: deleteDisable,
          danger: true,
        },
      ]}
    />
  );
  function handleEdit() {
    project && history.push(`/projects/edit/${project.id}`);
  }
}

export default ProjectMoreActions;
