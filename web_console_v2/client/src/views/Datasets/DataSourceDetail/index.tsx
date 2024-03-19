import { Grid, Space, Spin, Tabs, Tooltip, Tag, Message } from '@arco-design/web-react';
import BackButton from 'components/BackButton';
import PropertyList from 'components/PropertyList';
import SharedPageLayout from 'components/SharedPageLayout';
import GridRow from 'components/_base/GridRow';
import React, { FC, useEffect, useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { Redirect, Route, useHistory, useParams } from 'react-router';
import { fetchDataSourceDetail, deleteDataSource } from 'services/dataset';
import { formatTimestamp } from 'shared/date';
import { DatasetType, DataSource } from 'typings/dataset';
import { CONSTANTS } from 'shared/constants';
import ClickToCopy from 'components/ClickToCopy';
import MoreActions from 'components/MoreActions';
import Modal from 'components/Modal';
import PreviewFile from './PreviewFile';
import styled from './index.module.less';

const { Row } = Grid;

const { TabPane } = Tabs;

export enum DataSourceDetailSubTabs {
  PreviewFile = 'preview',
  RawDataset = 'raw_dataset',
}

const DataSourceDetail: FC<any> = () => {
  const history = useHistory();

  const { id, subtab } = useParams<{
    id: string;
    subtab: string;
  }>();
  const [activeTab, setActiveTab] = useState(subtab || DataSourceDetailSubTabs.PreviewFile);

  // ======= Data Source query ============
  const query = useQuery(['fetchDataSourceDetail', id], () => fetchDataSourceDetail({ id }), {
    refetchOnWindowFocus: false,
  });

  const dataSource = query.data?.data;

  const { type, url, created_at, dataset_type } = dataSource ?? {};

  const isStreaming = dataset_type === DatasetType.STREAMING;

  useEffect(() => {
    setActiveTab(subtab || DataSourceDetailSubTabs.PreviewFile);
  }, [subtab]);

  const deleteMutation = useMutation(
    (dataSourceId: ID) => {
      return deleteDataSource(dataSourceId);
    },
    {
      onSuccess() {
        history.push('/datasets/data_source');
        Message.success('删除成功');
      },
      onError(e: any) {
        Message.error(e.message);
      },
    },
  );

  /** IF no subtab be set, defaults to preview */
  if (!subtab) {
    return <Redirect to={`/datasets/data_source/${id}/${DataSourceDetailSubTabs.PreviewFile}`} />;
  }

  const displayedProps = [
    {
      value: String(type).toLocaleUpperCase(),
      label: '文件系统',
      proport: 0.5,
    },
    {
      value: (
        <ClickToCopy text={url || ''}>
          <Tooltip content={url}>
            <div className={styled.data_source_text}>{url || CONSTANTS.EMPTY_PLACEHOLDER}</div>
          </Tooltip>
        </ClickToCopy>
      ),
      label: '数据来源',
      proport: 1.5,
    },
    {
      value: getDataFormat(dataSource! ?? {}),
      label: '数据格式',
      proport: 1,
    },
    {
      value: created_at ? formatTimestamp(created_at) : CONSTANTS.EMPTY_PLACEHOLDER,
      label: '创建时间',
      proport: 1,
    },
  ].filter(Boolean);

  return (
    <SharedPageLayout title={<BackButton onClick={backToList}>数据源</BackButton>} cardPadding={0}>
      <div className={styled.data_source_detail_padding_box}>
        <Spin loading={query.isFetching}>
          <Row align="center" justify="space-between">
            <GridRow gap="12" style={{ maxWidth: '75%' }}>
              <div
                className={styled.data_source_detail_avatar}
                data-name={query.data?.data.name.slice(0, 2)}
              />
              <div>
                <div className={styled.data_source_name_container}>
                  <h3 className={styled.data_source_name}>{query.data?.data.name ?? '....'}</h3>
                </div>
                {(isStreaming || query.data?.data.comment) && (
                  <Space>
                    {isStreaming && <Tag color="blue">增量</Tag>}
                    {query.data?.data.comment && (
                      <small className={styled.comment}>{query.data?.data.comment}</small>
                    )}
                  </Space>
                )}
              </div>
            </GridRow>

            <Space>
              <MoreActions
                actionList={[
                  {
                    label: '删除',
                    onClick: onDeleteClick,
                    danger: true,
                  },
                ]}
              />
            </Space>
          </Row>
        </Spin>
        <PropertyList
          properties={displayedProps}
          cols={displayedProps.length}
          minWidth={150}
          align="center"
          colProportions={displayedProps.map((item) => item.proport)}
        />
      </div>
      <Tabs activeTab={activeTab} onChange={onSubtabChange} className={styled.data_detail_tab}>
        <TabPane
          className={styled.data_source_detail_tab_pane}
          title="文件预览"
          key={DataSourceDetailSubTabs.PreviewFile}
        />
        {/* <TabPane
          className={styled.data_source_detail_tab_pane}
          title="原始数据集"
          key={DataSourceDetailSubTabs.RawDataset}
        /> */}
      </Tabs>
      <div className={`${styled.data_source_detail_padding_box}`}>
        <Route
          path={`/datasets/data_source/:id/${DataSourceDetailSubTabs.PreviewFile}`}
          exact
          render={() => {
            return <PreviewFile />;
          }}
        />
        {/* <Route
          path={`/datasets/data_source/:id/${DataSourceDetailSubTabs.RawDataset}`}
          exact
          render={() => {
            return <div>原始数据集</div>;
          }}
        /> */}
      </div>
    </SharedPageLayout>
  );

  function getDataFormat(dataSource: DataSource) {
    let dataDescText = '';
    switch (dataSource.dataset_format) {
      case 'TABULAR':
        dataDescText = `结构化数据${dataSource.store_format ? '/' + dataSource.store_format : ''}`;
        break;
      case 'NONE_STRUCTURED':
        dataDescText = '非结构化数据';
        break;
      case 'IMAGE':
        dataDescText = '图片';
        break;
      default:
        dataDescText = '未知';
        break;
    }
    return dataDescText;
  }

  function backToList() {
    history.goBack();
  }

  function onDeleteClick() {
    Modal.delete({
      title: '确认删除数据源？',
      content: '删除后，当该数据源将无法恢复，请谨慎操作。',
      onOk: async () => {
        deleteMutation.mutate(id);
      },
    });
  }

  function onSubtabChange(val: string) {
    setActiveTab(val as DataSourceDetailSubTabs);
    history.replace(`/datasets/data_source/${id}/${val}`);
  }
};

export default DataSourceDetail;
