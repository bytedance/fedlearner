import React, { FC, useState } from 'react';
import ListPageLayout from 'components/SharedPageLayout';
import { useTranslation } from 'react-i18next';
import { Row, Button, Col, Form, Input, Table, message } from 'antd';
import { useHistory } from 'react-router-dom';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { Dataset } from 'typings/dataset';
import { useQuery } from 'react-query';
import { fetchDatasetList } from 'services/dataset';
import styled from 'styled-components';
import NoResult from 'components/NoResult';
import ImportProgress from './ImportProgress';
import { getTotalDataSize, isImporting } from 'shared/dataset';
import DatasetActions, { DatasetAction } from './DatasetActions';
import { noop } from 'lodash';
import BatchImportRecordsModal from './BatchImportRecordsModal';
import { useToggle } from 'react-use';
import AddBatchModal from './AddBatchModal';
import { copyToClipboard } from 'shared/helpers';
import WhichProject from 'components/WhichProject';
import { useRecoilValue } from 'recoil';
import { projectState } from 'stores/project';

const ListContainer = styled.div`
  display: flex;
  flex: 1;
`;

type ColumnsGetterOptions = {
  onViewReordsClick?: any;
  onDeleteClick?: any;
  onAddDataBatchClick?: any;
  onCopyPathClick?: any;
  onSuccess?: any;
  withoutActions?: boolean;
};
export const getDatasetTableColumns = (options: ColumnsGetterOptions) => {
  const onPerformAction = (payload: { action: DatasetAction; dataset: Dataset }) => {
    return {
      delete: options.onDeleteClick,
      'add-batch': options.onAddDataBatchClick,
      'view-records': options.onViewReordsClick,
      'copy-path': options.onCopyPathClick,
    }[payload.action](payload.dataset);
  };

  const cols = [
    {
      title: i18n.t('dataset.col_name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string) => {
        return <strong>{name}</strong>;
      },
    },
    {
      title: i18n.t('dataset.col_type'),
      dataIndex: 'dataset_type',
      name: 'dataset_type',
      width: 150,
    },
    {
      title: i18n.t('dataset.status'),
      dataIndex: 'state',
      name: 'state',
      width: 210,
      render: (_: any, record: Dataset) => {
        return <ImportProgress dataset={record} />;
      },
    },
    {
      title: i18n.t('dataset.col_files_size'),
      dataIndex: 'file_size',
      name: 'file_size',
      width: 130,
      render: (_: any, record: Dataset) => {
        return <span>{getTotalDataSize(record).toLocaleString('en')} KB</span>;
      },
    },
    {
      title: i18n.t('workflow.col_project'),
      dataIndex: 'project_id',
      name: 'project_id',
      width: 150,
      render: (project_id: number) => <WhichProject id={project_id} />,
    },
    {
      title: i18n.t('created_at'),
      dataIndex: 'created_at',
      name: 'created_at',
      width: 190,
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
  ];
  if (!options.withoutActions) {
    cols.push({
      title: i18n.t('operation'),
      dataIndex: 'operation',
      name: 'operation',
      fixed: 'right',
      render: (_: number, record: Dataset) => (
        <DatasetActions onPerformAction={onPerformAction} dataset={record} type="link" />
      ),
    } as any);
  }

  return cols;
};

export const DATASET_LIST_QUERY_KEY = 'datasetList';

const DatasetList: FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const history = useHistory();
  const [params, setParams] = useState({ keyword: '' });
  const [recordsVisible, toggleRecordsVisible] = useToggle(false);
  const [addBatchVisible, toggleAddBatchVisible] = useToggle(false);
  const [curDataset, setCurDataset] = useState<Dataset>();
  const project = useRecoilValue(projectState);

  const listQuery = useQuery(
    [DATASET_LIST_QUERY_KEY, params.keyword, project.current?.id],
    () => fetchDatasetList({ ...params, project: project.current?.id }),
    {
      retry: 2,
      refetchInterval: 90 * 1000, // auto refresh every 1.5 min
    },
  );

  const isEmpty = !listQuery.isFetching && listQuery.data?.data.length === 0;

  return (
    <ListPageLayout title={t('menu.label_datasets')}>
      <Row gutter={16} justify="space-between" align="middle">
        <Col>
          <Button size="large" type="primary" onClick={goCreate}>
            {t('dataset.btn_create')}
          </Button>
        </Col>
        <Col>
          <Form initialValues={{ ...params }} layout="inline" form={form} onFinish={onSearch}>
            <Form.Item name="keyword">
              <Input.Search
                placeholder={t('dataset.placeholder_name_searchbox')}
                onPressEnter={form.submit}
              />
            </Form.Item>
          </Form>
        </Col>
      </Row>

      <ListContainer>
        {isEmpty ? (
          <NoResult text={t('dataset.no_result')} to="/datasets/create" />
        ) : (
          <Table
            loading={listQuery.isFetching}
            dataSource={listQuery.data?.data || []}
            scroll={{ x: '100%' }}
            columns={getDatasetTableColumns({
              onSuccess: noop,
              onViewReordsClick,
              onAddDataBatchClick,
              onDeleteClick,
              onCopyPathClick,
            })}
            rowKey="name"
          />
        )}
      </ListContainer>

      <BatchImportRecordsModal
        records={curDataset?.data_batches || []}
        visible={recordsVisible}
        toggleVisible={toggleRecordsVisible}
        onOk={showAddBatchModal}
      />

      <AddBatchModal
        datasetType={curDataset?.dataset_type}
        datasetId={curDataset?.id}
        visible={addBatchVisible}
        toggleVisible={toggleAddBatchVisible}
        onSuccess={onAddBatchSuccess}
      />
    </ListPageLayout>
  );

  function onSearch(values: any) {
    setParams(values);
  }
  function onViewReordsClick(dataset: Dataset) {
    setCurDataset(dataset);
    toggleRecordsVisible(true);
  }
  function onCopyPathClick(dataset: Dataset) {
    const okay = copyToClipboard(dataset.path);
    if (okay) {
      message.success(t('app.copy_success'));
    }
  }
  function onAddDataBatchClick(dataset: Dataset) {
    if (!checkIfHasImportingBatches(dataset)) {
      return;
    }

    setCurDataset(dataset);
    toggleAddBatchVisible(true);
  }
  function onAddBatchSuccess() {
    toggleAddBatchVisible(false);
    listQuery.refetch();
  }

  function showAddBatchModal() {
    if (!curDataset) return;

    if (!checkIfHasImportingBatches(curDataset)) {
      return;
    }

    toggleRecordsVisible(false);
    toggleAddBatchVisible(true);
  }
  function onDeleteClick() {
    // TODO: coming soon
    message.info('Coming soon');
  }
  function goCreate() {
    history.push('/datasets/create');
  }
  /** DOESN'T SUPPORT add batches for dataset which has unfinished importing YET */
  function checkIfHasImportingBatches(dataset: Dataset) {
    if (isImporting(dataset)) {
      message.info(t('dataset.msg_is_importing'));
      return false;
    }

    return true;
  }
};

export default DatasetList;
