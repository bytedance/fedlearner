import React, { ReactElement, useState, useMemo } from 'react';
import { useQuery } from 'react-query';
import { useHistory, useParams } from 'react-router-dom';
import { getProjectDetailById, updateProject } from 'services/project';
import { UpdateProjectPayload } from 'typings/project';
import { ProjectFormInitialValues } from 'typings/project';
import { Message as message, Spin } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import StepOneConfig from '../CreateProject/StepOneConfig';
import { useReloadProjectList } from 'hooks/project';

import styles from './index.module.less';

function EditProject(): ReactElement {
  const history = useHistory();
  const { id } = useParams<{ id: string }>();
  const reloadList = useReloadProjectList();
  const [isFormValueChanged, setIsFormValueChanged] = useState(false);

  const projectQuery = useQuery(['getProjectDetail', id], () => getProjectDetailById(id), {
    cacheTime: 1,
    refetchOnWindowFocus: false,
  });

  const initialValues = {};

  const project = projectQuery.data?.data;
  const projectDetail = useMemo(() => {
    return projectQuery.data?.data;
  }, [projectQuery]);

  if (project) {
    Object.assign(initialValues, {
      name: project.name,
      comment: project.comment,
      token: project?.token || '',
      variables: project?.config?.variables || [],
      participants: project.participants || '',
      abilities: project?.config?.abilities || [],
      action_rules: project.config?.action_rules || {},
    });
  }
  return (
    <div className={styles.container}>
      <Spin className={styles.spin_container} loading={projectQuery.isLoading}>
        <SharedPageLayout
          title={
            <BackButton
              onClick={() => history.replace(`/projects`)}
              isShowConfirmModal={isFormValueChanged}
            >
              工作区管理
            </BackButton>
          }
          centerTitle="编辑工作区"
        >
          {project && !projectQuery.isFetching && (
            <StepOneConfig
              isEdit={true}
              isLeftLayout={true}
              onEditFinish={onSubmit}
              initialValues={projectDetail as ProjectFormInitialValues}
              onFormValueChange={onFormValueChange}
            />
          )}
        </SharedPageLayout>
      </Spin>
    </div>
  );
  async function onSubmit(payload: UpdateProjectPayload) {
    try {
      await updateProject(project!.id, payload);
      message.success('编辑成功！');
      reloadList();
      history.push('/projects');
    } catch (error: any) {
      message.error(error.message);
    }
  }
  function onFormValueChange() {
    if (!isFormValueChanged) {
      setIsFormValueChanged(true);
    }
  }
}

export default EditProject;
