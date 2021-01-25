import React, { FC, useState } from 'react';
import ListPageLayout from 'components/ListPageLayout';
import { useTranslation } from 'react-i18next';
import { Row, Button, Col, Form, Input, Table } from 'antd';
import { useHistory } from 'react-router-dom';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { Dataset } from 'typings/dataset';
import Username from 'components/Username';
import { useQuery } from 'react-query';
import { fetchDatasetList } from 'services/dataset';
import styled from 'styled-components';
import NoResult from 'components/NoResult';
import ImportProgress from '../ImportProgress';
import { getTotalDataSize } from 'shared/dataset';
import DatasetActions from '../DatasetActions';
import { noop } from 'lodash';

const ListContainer = styled.div`
  display: flex;
  flex: 1;
`;

export const getDatasetTableColumns = (options: { onSuccess: any; withoutActions?: boolean }) => {
  const ret = [
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
        return <span>{getTotalDataSize(record).toLocaleString('en')}</span>;
      },
    },
    {
      title: i18n.t('creator'),
      dataIndex: 'creator',
      name: 'creator',
      width: 130,
      render: (_: string) => <Username />,
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
    ret.push({
      title: i18n.t('operation'),
      dataIndex: 'operation',
      name: 'operation',
      render: (_: number, record: Dataset) => (
        <DatasetActions onSuccess={options.onSuccess} dataset={record} type="link" />
      ),
    } as any);
  }

  return ret;
};

const DatasetList: FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const history = useHistory();
  const [params, setParams] = useState({ keyword: '' });

  const listQuery = useQuery(['datasetList', params.keyword], () => fetchDatasetList(params), {
    retry: 2,
  });

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
            columns={getDatasetTableColumns({ onSuccess: noop })}
          />
        )}
      </ListContainer>
    </ListPageLayout>
  );

  function onSearch(values: any) {
    setParams(values);
  }
  function goCreate() {
    history.push('/datasets/create');
  }
};

export default DatasetList;
