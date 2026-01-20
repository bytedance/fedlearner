import React from 'react';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import { useHistory, useParams } from 'react-router';
import { useIsFormValueChange, useGetCurrentProjectId } from 'hooks';
import { Spin, Message } from '@arco-design/web-react';
import FormModal, { FormData } from './FormModel/index';
import { createDataSource } from 'services/dataset';
import { DataSourceCreatePayload } from 'typings/dataset';
import { useMutation } from 'react-query';

const NewCreateDataSource: React.FC = function () {
  const history = useHistory();
  const { action } = useParams<{
    action: 'create' | 'edit';
  }>();
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();
  const projectId = useGetCurrentProjectId();

  const isLoading = false;
  const isEdit = action === 'edit';

  const createMutation = useMutation(
    (payload: DataSourceCreatePayload) => {
      return createDataSource(payload);
    },
    {
      onSuccess() {
        Message.success('创建成功');
        goBackToListPage();
      },
      onError(e: any) {
        Message.error(e.message);
      },
    },
  );

  return (
    <SharedPageLayout
      title={
        <BackButton isShowConfirmModal={isFormValueChanged} onClick={goBackToListPage}>
          数据源
        </BackButton>
      }
      centerTitle={isEdit ? '编辑数据源' : '创建数据源'}
    >
      <Spin loading={isLoading}>
        <FormModal
          isEdit={isEdit}
          onCancel={backToList}
          onChange={onFormValueChange}
          onOk={onFormModalSubmit}
        />
      </Spin>
    </SharedPageLayout>
  );

  function goBackToListPage() {
    history.push('/datasets/data_source');
  }

  function backToList() {
    history.goBack();
  }

  async function onFormModalSubmit(values: FormData) {
    createMutation.mutate({
      project_id: projectId!,
      data_source: values,
    });
  }
};

export default NewCreateDataSource;
