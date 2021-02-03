import React, { ReactElement } from 'react';
import ProjectForm from '../ProjectForm';
import BreadcrumbLink from 'components/BreadcrumbLink';
import { createProject } from 'services/project';
import { CreateProjectPayload } from 'typings/project';

function CreateProject(): ReactElement {
  return (
    <>
      <BreadcrumbLink
        paths={[{ label: 'menu.label_project', to: '/projects' }, { label: 'project.create' }]}
      />

      <ProjectForm onSubmit={onSubmit} />
    </>
  );
  async function onSubmit(payload: CreateProjectPayload) {
    try {
      await createProject(payload);
    } catch (error) {
      throw error;
    }
  }
}

export default CreateProject;
