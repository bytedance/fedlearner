import React, { ReactElement } from 'react';
import ProjectForm from '../ProjectForm';
import { createProject } from 'services/project';
import { CreateProjectPayload } from 'typings/project';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import { useTranslation } from 'react-i18next';
import { useHistory } from 'react-router';

function CreateProject(): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();

  return (
    <SharedPageLayout
      title={<BackButton onClick={() => history.goBack()}>{t('menu.label_project')}</BackButton>}
    >
      <ProjectForm onSubmit={onSubmit} />
    </SharedPageLayout>
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
