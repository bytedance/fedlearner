import React, { ReactElement } from 'react';
import ProjectForm from '../ProjectForm';
import { Spin } from 'antd';
import { useHistory, useParams } from 'react-router-dom';
import { getProjectDetailById, updateProject } from 'services/project';
import { CertificateConfigType, UpdateProjectPayload } from 'typings/project';
import { ProjectFormInitialValues } from 'typings/project';
import { useQuery } from 'react-query';
import styled from 'styled-components';
import { unwrapDomainName } from 'shared/project';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import { useTranslation } from 'react-i18next';

const SpinContainer = styled(Spin)`
  min-height: 500px;
`;

function EditProject(): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();
  const { id } = useParams<{ id: string }>();

  const projectQuery = useQuery(['getProjectDetail', id], () => getProjectDetailById(id), {
    cacheTime: 1,
    refetchOnWindowFocus: false,
  });

  const initialValues = {
    certificateConfigType: CertificateConfigType.BackendConfig,
  };

  const project = projectQuery.data?.data;

  if (project) {
    const participant = project.config.participants[0];

    Object.assign(initialValues, {
      name: project.name,
      participantName: participant.name,
      participantUrl: participant.url,
      participantDomainName: unwrapDomainName(participant.domain_name),
      comment: project.comment,
      token: project.config.token,
      variables: project.config.variables || [],
    });
  }

  return (
    <SpinContainer spinning={projectQuery.isLoading}>
      <SharedPageLayout
        title={<BackButton onClick={() => history.goBack()}>{t('menu.label_project')}</BackButton>}
      >
        {project && !projectQuery.isFetching && (
          <ProjectForm
            onSubmit={onSubmit}
            isEdit
            initialValues={initialValues as ProjectFormInitialValues}
          />
        )}
      </SharedPageLayout>
    </SpinContainer>
  );
  async function onSubmit(payload: UpdateProjectPayload) {
    try {
      await updateProject(project!.id, payload);
    } catch (error) {
      throw error;
    }
  }
}

export default EditProject;
