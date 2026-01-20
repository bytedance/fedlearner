/* istanbul ignore file */
import React, { FC, useEffect, useMemo, useRef, useState } from 'react';
import { Select } from '@arco-design/web-react';
import { fetchDatasetDetail } from 'services/dataset';
import { useTranslation } from 'react-i18next';
import { Dataset, DatasetKindLabel, ParticipantDataset, DataJobBackEndType } from 'typings/dataset';
import { SelectProps } from '@arco-design/web-react/es/Select';
import { OptionInfo } from '@arco-design/web-react/es/Select/interface';
import { debounce } from 'lodash-es';
import { useGetDatasetList, useGetLastSelectedDataset } from './hooks';
import { renderOption } from '../DatasetSelect';

interface ILazyLoad {
  enable: boolean;
  page_size?: number;
}

export interface IPageInfo {
  page?: number;
  totalPages?: number;
  keyword?: string;
}

export interface Props extends SelectProps {
  /** Is participant dataset */
  isParticipant?: boolean;
  /** extra API query params */
  queryParams?: object;
  /** raw or processed dataset */
  kind?: DatasetKindLabel;
  shouldGetDatasetDetailAfterOnChange?: boolean;
  onChange?: (value: any, option: OptionInfo | OptionInfo[], datasetDetail?: Dataset) => void;
  /** open pagination and fetch list with page params */
  lazyLoad?: ILazyLoad;
  /** DATA_ALIGNMENT or other type dataset */
  datasetJobKind?: DataJobBackEndType;
}

const DatasetSelect: FC<Props> = ({
  value,
  onChange,
  queryParams,
  isParticipant = false,
  kind = DatasetKindLabel.PROCESSED,
  shouldGetDatasetDetailAfterOnChange = false,
  lazyLoad = {
    enable: false,
    page_size: 10,
  },
  disabled = false,
  datasetJobKind,
  ...props
}) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const refCanTriggerLoadMore = useRef(true);
  const pageInit = useRef(true);
  const [
    datasetList,
    datasetQuery,
    pageInfo,
    setPageInfo,
    clearList,
    setOptions,
  ] = useGetDatasetList({
    isParticipant,
    queryParams,
    kind,
    lazyLoad,
    disabled,
    datasetJobKind,
  });

  // fetch the details of the last selected dataset
  const [lastDatasetLoading, lastDatasetDetail] = useGetLastSelectedDataset(
    value as ID,
    pageInit.current,
  );

  const popupScrollHandler = (element: any) => {
    const curPage = pageInfo.page || 0;
    const curTotalPage = pageInfo.totalPages || 0;
    if (!lazyLoad?.enable || curPage >= curTotalPage) {
      return;
    }
    const { scrollTop, scrollHeight, clientHeight } = element;
    const scrollBottom = scrollHeight - (scrollTop + clientHeight);
    if (scrollBottom < 10) {
      if (!datasetQuery.isFetching && refCanTriggerLoadMore.current) {
        setPageInfo((pre: any) => ({
          ...pre,
          page: pre.page + 1,
        }));
        refCanTriggerLoadMore.current = false;
      }
    } else {
      refCanTriggerLoadMore.current = true;
    }
  };

  const debouncedFetchUser = debounce((inputValue: string) => {
    if (!lazyLoad?.enable) {
      return;
    }
    setPageInfo({
      keyword: inputValue,
      page: 1,
      totalPages: 0,
    });
    clearList();
  }, 500);

  const isControlled = typeof value !== 'undefined';
  const valueProps = isControlled ? { value } : {};
  const disableProps = isLoading || disabled ? { disabled: true } : {};
  useEffect(() => {
    setPageInfo({
      keyword: '',
      page: 1,
      totalPages: 0,
    });
    setOptions([]);
  }, [datasetJobKind, setPageInfo, setOptions]);

  return (
    <Select
      onSearch={debouncedFetchUser}
      onPopupScroll={popupScrollHandler}
      placeholder={t('placeholder_select')}
      onChange={onSelectChange}
      value={value}
      showSearch
      allowClear
      filterOption={(inputValue, option) => {
        return option.props.extra.name.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0;
      }}
      loading={datasetQuery.isFetching || isLoading || lastDatasetLoading}
      {...valueProps}
      {...props}
      {...disableProps}
    >
      {datasetList.map((item) => (
        <Select.Option
          key={isParticipant ? (item as ParticipantDataset).uuid : (item as Dataset).id}
          value={isParticipant ? (item as ParticipantDataset).uuid : (item as Dataset).id}
          extra={item}
        >
          {renderOption(item, isParticipant)}
        </Select.Option>
      ))}
      {Boolean(lastDatasetDetail && lastDatasetDetail?.name) && (
        <Select.Option
          key={
            isParticipant
              ? (lastDatasetDetail as ParticipantDataset).uuid
              : (lastDatasetDetail as Dataset).id
          }
          value={
            isParticipant
              ? (lastDatasetDetail as ParticipantDataset).uuid
              : (lastDatasetDetail as Dataset).id
          }
          extra={lastDatasetDetail}
        >
          {renderOption(lastDatasetDetail!, isParticipant)}
        </Select.Option>
      )}
    </Select>
  );

  async function onSelectChange(id: string, options: OptionInfo | OptionInfo[]) {
    pageInit.current = false;
    let datasetDetail;
    try {
      if (shouldGetDatasetDetailAfterOnChange && !isParticipant) {
        setIsLoading(true);
        const resp = await fetchDatasetDetail(id);
        datasetDetail = resp.data;
      }
    } catch (error) {}
    setIsLoading(false);
    onChange?.(id, options, datasetDetail);
  }
};

type PathProps = {
  /** Accept dataset path */
  value?: string;
  /** Accept dataset path */
  onChange?: (val?: string, options?: OptionInfo | OptionInfo[]) => void;
} & Omit<Props, 'value' | 'onChange' | 'isParticipant'>;

export const DatasetPathSelect: FC<PathProps> = ({
  value,
  onChange,
  queryParams,
  kind = DatasetKindLabel.PROCESSED,
  ...props
}) => {
  const [datasetList] = useGetDatasetList({
    isParticipant: false, // Don't support participant dataset, because it's no path field
    queryParams,
    kind,
  });

  const datasetId = useMemo(() => {
    const dataset = datasetList.find((item) => {
      return (item as Dataset).path === value;
    }) as Dataset;

    return dataset?.id;
  }, [datasetList, value]);

  const valueProps = datasetId ? { value: datasetId } : {};

  return (
    <DatasetSelect
      onChange={(_, option) => {
        const dataset = (option as OptionInfo)?.extra;
        onChange?.(dataset?.path ?? undefined, option);
      }}
      {...valueProps}
      {...props}
    />
  );
};

export default DatasetSelect;
