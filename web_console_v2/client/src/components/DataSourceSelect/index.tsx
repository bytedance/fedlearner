/* istanbul ignore file */
import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { useTranslation } from 'react-i18next';
import { fetchDataSourceList } from 'services/dataset';
import { Select, Grid, Tag, Space } from '@arco-design/web-react';
import { useGetCurrentProjectId } from 'hooks';

import { SelectProps } from '@arco-design/web-react/es/Select';
import { OptionInfo } from '@arco-design/web-react/es/Select/interface';
import { DataSource, DatasetType } from 'typings/dataset';
import TitleWithIcon from 'components/TitleWithIcon';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import styled from './index.module.less';

const Row = Grid.Row;
const Col = Grid.Col;

type Props = {
  /** extra API query params */
  queryParams?: object;
  valueKey?: 'id' | 'uuid';
} & SelectProps;

function renderOption(data: DataSource) {
  const isStream = data.dataset_type === DatasetType.STREAMING;
  let dataDescText = '';
  switch (data.dataset_format) {
    case 'TABULAR':
      dataDescText = `结构化数据${data.store_format ? '/' + data.store_format : ''}`;
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
  return (
    <div>
      <Row>
        <Col span={18}>
          <span>{data.name}</span>
        </Col>
        <Col span={6}>{isStream ? <Tag color="blue">增量</Tag> : <></>}</Col>
      </Row>
      <div className={styled.data_source_select_option_text}>{dataDescText}</div>
    </div>
  );
}

export const DataSourceSelect: FC<Props> = ({
  value,
  valueKey = 'id',
  onChange,
  queryParams,
  ...props
}) => {
  const { t } = useTranslation();
  const projectId = useGetCurrentProjectId();
  const [isShowTip, setShowTip] = useState(false);
  const query = useQuery(
    ['fetchDataSourceList', projectId],
    () => fetchDataSourceList({ projectId: projectId, ...queryParams }),
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const optionList = useMemo(() => {
    if (!query.data) {
      return [];
    }

    return query.data.data.map((item) => ({
      label: renderOption(item),
      value: item[valueKey],
      extra: item,
    }));
  }, [query.data, valueKey]);

  const isControlled = typeof value !== 'undefined';
  const valueProps = isControlled ? { value } : {};

  return (
    <Space direction="vertical" className={styled.data_source_select}>
      <Select
        placeholder={t('placeholder_select')}
        onChange={onSelectChange}
        loading={query.isFetching}
        showSearch
        allowClear
        filterOption={(inputValue, option) => {
          return option.props.extra.name.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0;
        }}
        options={optionList}
        {...valueProps}
        {...props}
      />
      {isShowTip && (
        <TitleWithIcon
          title="增量数据将检查目录结构，并批量导入。导入后该数据集只能用于求交任务"
          isLeftIcon={true}
          isShowIcon={true}
          icon={IconInfoCircle}
        />
      )}
    </Space>
  );

  function onSelectChange(id: string, options: OptionInfo | OptionInfo[]) {
    setShowTip(options && (options as any).extra.dataset_type === DatasetType.STREAMING);
    onChange?.(id, options);
  }
};

export default DataSourceSelect;
