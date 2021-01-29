import React, { ReactElement } from 'react';
import ProjectForm from '../ProjectForm';
import { Spin } from 'antd';
import { useParams } from 'react-router-dom';
import { getProjectDetailById, updateProject } from 'services/project';
import { CertificateConfigType } from 'typings/project';
import { ProjectFormInitialValues } from 'typings/project';
import { useQuery } from 'react-query';
import BreadcrumbLink from 'components/BreadcrumbLink';

function EditProject(): ReactElement {
  const { id } = useParams<{ id: string }>();

  const projectQuery = useQuery(['getProjectDetail', id], () => getProjectDetailById(id), {
    cacheTime: 1,
  });

  const initialValues = {
    certificateConfigType: CertificateConfigType.BackendConfig,
  };

  const project = projectQuery.data?.data;

  if (project) {
    Object.assign(initialValues, {
      name: project.name,
      participantName: project.config.participants[0].name,
      participantUrl: project.config.participants[0].url,
      participantDomainName: project.config.participants[0].domain_name,
      comment: project.comment,
      domain_name: project.config.domain_name,
      variables: project.config.variables || [],
    });
  }

  return (
    <Spin spinning={projectQuery.isLoading}>
      <BreadcrumbLink
        paths={[{ label: 'menu.label_project', to: '/projects' }, { label: 'project.edit' }]}
      />

      {project && (
        <ProjectForm
          onSubmit={onSubmit}
          isEdit
          initialValues={initialValues as ProjectFormInitialValues}
        />
      )}
    </Spin>
  );
  async function onSubmit<UpdateProjectFormData>(payload: UpdateProjectFormData) {
    try {
      await updateProject(project!.id, payload);
    } catch (error) {
      throw error;
    }
  }
}

export default EditProject;
