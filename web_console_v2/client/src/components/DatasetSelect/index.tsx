import React, { FC } from 'react';
import styled from 'styled-components';
import { Select } from 'antd';
import { useQuery } from 'react-query';
import { DATASET_LIST_QUERY_KEY } from 'views/Datasets/DatasetList';
import { fetchDatasetList } from 'services/dataset';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

const EmptyPlaceholder = styled.div`
  line-height: 32px;
`;

type Props = {
  value?: string;
  onChange?: (val: string) => void;
};
const DatasetSelect: FC<Props> = ({ value, onChange, ...props }) => {
  const { t } = useTranslation();

  const query = useQuery([DATASET_LIST_QUERY_KEY, ''], () => fetchDatasetList(), {
    retry: 2,
  });

  const isEmpty = !query.isFetching && query.data?.data.length === 0;

  return (
    <>
      {isEmpty ? (
        <EmptyPlaceholder>
          {t('dataset.no_result')} <Link to="/datasets/create">{t('app.go_create')}</Link>
        </EmptyPlaceholder>
      ) : (
        <Select
          value={value}
          placeholder={t('workflow.placeholder_dataset')}
          onChange={onSelectChange}
          {...props}
        >
          {query.data?.data.map((item) => {
            return (
              <Select.Option key={item.id} value={item.path}>
                {item.name}
              </Select.Option>
            );
          })}
        </Select>
      )}
    </>
  );

  function onSelectChange(val: string) {
    onChange && onChange(val);
  }
};

export default DatasetSelect;
