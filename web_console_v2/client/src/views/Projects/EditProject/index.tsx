import React, { ReactElement } from 'react';
import BaseForm from '../BaseForm';
import { Breadcrumb, Spin } from 'antd';
import BreadcrumbSplit from 'components/Container/BreadcrumbSplit';
import { useHistory, useParams } from 'react-router-dom';
import { getProjectDetailById, updateProject } from 'services/project';
import { useTranslation } from 'react-i18next';
import { CertificateConfigType } from 'typings/project';
import { ProjectFormInitialValues } from 'typings/project';
import { useQuery } from 'react-query';

function EditProject(): ReactElement {
  const history = useHistory();
  const { t } = useTranslation();
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
      variables: project.config.variables || [],
    });
  }

  return (
    <Spin spinning={projectQuery.isLoading}>
      <Breadcrumb separator={<BreadcrumbSplit />}>
        <Breadcrumb.Item
          onClick={() => {
            history.push('/projects');
          }}
        >
          {t('menu.label_project')}
        </Breadcrumb.Item>
        <Breadcrumb.Item>{t('project.edit')}</Breadcrumb.Item>
      </Breadcrumb>

      {project && (
        <BaseForm
          onSubmit={onSubmit}
          edit
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
