import React, { FC, useState, useMemo } from 'react';
import { useRecoilValue } from 'recoil';
import { useToggle } from 'react-use';
import { useQuery } from 'react-query';

import { fetchModelList, updateModel, deleteModel } from 'services/modelCenter';

import { TIME_INTERVAL } from 'shared/constants';
import { projectState } from 'stores/project';
import { useUrlState } from 'hooks';

import { Input, Message } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout from 'components/SharedPageLayout';
import Modal from 'components/Modal';
import ModelTable from './ModelTable';
import ModelFormModal, { ModelFormData } from './ModelFormModal';

import { Model, ModelUpdatePayload } from 'typings/modelCenter';

import styles from './index.module.less';

type Props = {
  isOldModelCenter: boolean;
};

const Page: FC<Props> = ({ isOldModelCenter = false }) => {
  const [selectedData, setSelectedData] = useState<Model>();

  const [isModelFormModalVisiable, toggleIsModelFormModalVisiable] = useToggle(false);
  const [isUpdating, toggleIsUpdating] = useToggle(false);

  const selectedProject = useRecoilValue(projectState);
  const [urlState, setUrlState] = useUrlState({
    keyword: '',
  });

  const listQuery = useQuery(
    ['fetchModelList', urlState.keyword, selectedProject.current?.id],
    () => {
      if (!selectedProject.current?.id) {
        Message.info('请选择工作区');
        return;
      }
      return fetchModelList(selectedProject.current?.id, {
        keyword: urlState.keyword,
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
    },
  );

  const tableDataSource = useMemo(() => {
    if (!listQuery.data) {
      return [];
    }
    let list = listQuery.data.data || [];

    // Filter deleted model
    list = list.filter((item) => !item.deleted_at);

    return list;
  }, [listQuery.data]);

  return (
    <SharedPageLayout title={'模型仓库'}>
      <GridRow justify="end" align="center">
        <Input.Search
          className={`${styles.search_container} custom-input`}
          allowClear
          onSearch={onSearch}
          onClear={() => onSearch('')}
          placeholder={'输入模型名称'}
          defaultValue={urlState.keyword}
        />
      </GridRow>
      <ModelTable
        loading={listQuery.isFetching}
        dataSource={tableDataSource}
        onDeleteClick={onDeleteClick}
        onEditClick={onEditClick}
        isOldModelCenter={isOldModelCenter}
      />
      <ModelFormModal
        visible={isModelFormModalVisiable}
        isEdit={true}
        isLoading={isUpdating}
        onCancel={onModalClose}
        onOk={onModalSubmit}
        initialValues={selectedData}
      />
    </SharedPageLayout>
  );

  function onSearch(
    value: string,
    event?:
      | React.ChangeEvent<HTMLInputElement>
      | React.MouseEvent<HTMLElement>
      | React.KeyboardEvent<HTMLInputElement>,
  ) {
    setUrlState((prevState) => ({
      ...prevState,
      keyword: value,
      page: 1,
    }));
  }

  function onDeleteClick(record: Model) {
    Modal.delete({
      title: '确认要删除该模型吗？',
      content: '删除后，不影响正在使用该模型的任务，使用该模型的历史任务不能再正常运行，请谨慎删除',
      onOk: async () => {
        try {
          if (!selectedProject.current?.id) {
            Message.info('请选择工作区');
            return;
          }
          await deleteModel(selectedProject.current?.id, record.id);
          listQuery.refetch();
          Message.success('删除成功');
        } catch (error) {
          Message.error(error.message);
        }
      },
    });
  }

  function onEditClick(record: Model) {
    setSelectedData(record);
    toggleIsModelFormModalVisiable(true);
  }

  async function onModalSubmit(value: ModelFormData) {
    toggleIsUpdating(true);

    try {
      const payload: ModelUpdatePayload = {
        comment: value.comment,
      };
      if (!selectedProject.current?.id) {
        Message.info('请选择工作区');
        return;
      }
      await updateModel(selectedProject.current?.id, selectedData?.id!, payload);
      toggleIsModelFormModalVisiable(false);
      listQuery.refetch();
      Message.success('修改成功');
    } catch (error) {
      Message.error(error.message);
    } finally {
      toggleIsUpdating(false);
    }
  }

  function onModalClose() {
    setSelectedData(undefined);
    toggleIsModelFormModalVisiable(false);
  }
};

export default Page;
