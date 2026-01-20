/* istanbul ignore file */

import React, { FC, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { Select, Grid, Tag, Statistic } from '@arco-design/web-react';
import { useQuery } from 'react-query';
import { DATASET_LIST_QUERY_KEY } from 'views/Datasets/DatasetList';
import { fetchDatasetList, fetchParticipantDatasetList } from 'services/dataset';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Dataset,
  DatasetDataType,
  DatasetDataTypeText,
  DatasetKindBackEndType,
  DatasetStateFront,
  ParticipantDataset,
  DatasetType__archived,
} from 'typings/dataset';
import { useRecoilValue } from 'recoil';
import { projectState } from 'stores/project';
import { SelectProps } from '@arco-design/web-react/es/Select';
import { PageMeta } from 'typings/app';
import { debounce } from 'lodash-es';
import { FILTER_OPERATOR_MAPPER, filterExpressionGenerator } from 'views/Datasets/shared';
import { humanFileSize } from 'shared/file';
import { FilterOp } from 'typings/filter';

const Row = Grid.Row;
const Col = Grid.Col;

const EmptyPlaceholder = styled.div`
  line-height: 32px;
`;

const StyledOptionContainer = styled.div``;
interface ILazyLoad {
  enable: boolean;
  page_size?: number;
}

interface IFilterOption {
  dataset_type?: DatasetType__archived;
  cron_interval?: Array<'DAYS' | 'HOURS'>;
  dataset_format?: DatasetDataType[];
  dataset_kind?: DatasetKindBackEndType[];
  participant_id?: ID;
}
interface Props extends Omit<SelectProps, 'value'> {
  /** Accept Dataset */
  value?: Dataset | ParticipantDataset;
  /** Accept Dataset */
  onChange?: (val?: Dataset | ParticipantDataset) => void;
  /** Is participant dataset */
  isParticipant?: boolean;
  /** extra API query params */
  queryParams?: object;
  /** open pagination and fetch list with page params */
  lazyLoad?: ILazyLoad;
  /** placeholder change */
  placeholder?: string;
  /** */
  filterOptions?: IFilterOption;
  /** is create button visible */
  isCreateVisible?: boolean;
}

const FILTER_OPERATOR_MAPPER_List = {
  ...FILTER_OPERATOR_MAPPER,
  dataset_kind: FilterOp.IN,
};

export function renderOption(data: ParticipantDataset | Dataset, isParticipant: boolean) {
  let formatText = DatasetDataTypeText.STRUCT;
  const format: DatasetDataType = isParticipant
    ? (data as ParticipantDataset).format
    : (data as Dataset).dataset_format;

  if (format === DatasetDataType.STRUCT) {
    formatText = DatasetDataTypeText.STRUCT;
  }
  if (format === DatasetDataType.PICTURE) {
    formatText = DatasetDataTypeText.PICTURE;
  }
  if (format === DatasetDataType.NONE_STRUCTURED) {
    formatText = DatasetDataTypeText.NONE_STRUCTURED;
  }

  let tagText = '';
  if (data.dataset_kind === DatasetKindBackEndType.RAW) {
    tagText = '原始';
  }
  if (data.dataset_kind === DatasetKindBackEndType.PROCESSED) {
    tagText = '结果';
  }

  return (
    <StyledOptionContainer>
      <Row>
        <Col span={18}>
          <span>{data.name}</span>
        </Col>
        <Col span={6}>{tagText ? <Tag>{tagText}</Tag> : <></>}</Col>
      </Row>
      <Row>
        <Col span={6}>{formatText}</Col>
        <Col span={2}>
          <span> | </span>
        </Col>
        <Col span={6}>{humanFileSize(data.file_size)}</Col>
        <Col span={2}>
          <span> | </span>
        </Col>
        {Object.prototype.hasOwnProperty.call(data, 'num_example') && (
          <Col span={6}>
            样本量
            {
              <Statistic
                groupSeparator={true}
                styleValue={{ fontSize: '14px', fontWeight: 400 }}
                value={(data as Dataset).num_example!}
              />
            }
          </Col>
        )}
      </Row>
    </StyledOptionContainer>
  );
}

const DatasetSelect: FC<Props> = ({
  value,
  onChange,
  queryParams,
  isParticipant = false,
  placeholder,
  lazyLoad = {
    enable: false,
    page_size: 10,
  },
  filterOptions = {},
  isCreateVisible = true,
  ...props
}) => {
  const { t } = useTranslation();
  const selectedProject = useRecoilValue(projectState);
  const [pageInfo, setPageInfo] = useState({
    page: 1,
    totalPages: 0,
    keyword: '',
  });
  const [options, setOptions] = useState([] as Array<ParticipantDataset | Dataset>);
  const [selectDataset, setSelectDataset] = useState<ParticipantDataset | Dataset>();
  const refCanTriggerLoadMore = useRef(true);
  const query = useQuery<{
    data: Array<Dataset | ParticipantDataset>;
    page_meta?: PageMeta;
  }>(
    [
      DATASET_LIST_QUERY_KEY,
      selectedProject.current?.id,
      isParticipant,
      lazyLoad?.enable ? pageInfo.page : null,
      lazyLoad?.enable ? pageInfo.keyword : null,
      filterOptions?.dataset_type,
      filterOptions?.dataset_kind,
      filterOptions?.cron_interval,
      queryParams,
    ],
    () => {
      const pageParams = lazyLoad?.enable
        ? {
            page: pageInfo.page,
            page_size: lazyLoad.page_size,
          }
        : {};
      const filter = filterExpressionGenerator(
        {
          project_id: selectedProject.current?.id,
          name: pageInfo.keyword,
          is_published: isParticipant ? undefined : true,
          dataset_type: filterOptions?.dataset_type,
          dataset_format: filterOptions?.dataset_format,
          dataset_kind: filterOptions?.dataset_kind,
        },
        FILTER_OPERATOR_MAPPER_List,
      );
      if (isParticipant) {
        return fetchParticipantDatasetList(selectedProject.current?.id!, {
          ...queryParams,
          ...pageParams,
          cron_interval: filterOptions?.cron_interval,
        });
      }
      return fetchDatasetList({
        filter,
        ...queryParams,
        ...pageParams,
        state_frontend: [DatasetStateFront.SUCCEEDED],
        cron_interval: filterOptions?.cron_interval,
      });
    },
    {
      enabled: Boolean(selectedProject.current),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess: (res) => {
        setPageInfo((pre) => {
          const { page_meta } = res;
          return {
            ...pre,
            page: page_meta?.current_page || pre.page,
            totalPages: page_meta?.total_pages || pre.totalPages,
          };
        });
        setOptions((pre) => {
          const { data } = res;
          let addOption = (data ?? []) as Dataset[];
          // 由于目前合作伙伴接口不支持过滤， 需要前端过滤
          if (isParticipant) {
            addOption = addOption.filter((item: any) => {
              let isShow = true;
              if (filterOptions && filterOptions.dataset_type) {
                isShow = Boolean(filterOptions.dataset_type === item.dataset_type);
              }
              if (filterOptions && isShow && filterOptions.dataset_format) {
                isShow = filterOptions.dataset_format?.includes(item.format);
              }
              if (isShow && filterOptions?.participant_id) {
                isShow = filterOptions.participant_id === item.participant_id;
              }
              if (isShow && filterOptions?.dataset_kind) {
                isShow = filterOptions?.dataset_kind.includes(item.dataset_kind);
              }
              return isShow;
            });
          }
          return pre.concat(addOption);
        });
      },
    },
  );

  useEffect(() => {
    setOptions([]);
    setPageInfo((pre) => ({
      ...pre,
      page: 1,
    }));
  }, [filterOptions.dataset_type, filterOptions.cron_interval]);
  // Empty only if there is no keyword, and the 1st page is requested, and there is no data
  const isEmpty =
    options.length === 0 && !query.isFetching && !pageInfo.keyword && pageInfo.page === 1;

  const popupScrollHandler = (element: any) => {
    if (!lazyLoad?.enable || pageInfo.page >= pageInfo.totalPages) {
      return;
    }
    const { scrollTop, scrollHeight, clientHeight } = element;
    const scrollBottom = scrollHeight - (scrollTop + clientHeight);
    if (scrollBottom < 10) {
      if (!query.isFetching && refCanTriggerLoadMore.current) {
        setPageInfo((pre) => ({
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
    setOptions([]);
  }, 500);

  return (
    <>
      {isEmpty ? (
        <EmptyPlaceholder>
          {t('dataset.no_result')}{' '}
          {!isParticipant && isCreateVisible && (
            <Link to="/datasets/raw/create">{t('app.go_create')}</Link>
          )}
        </EmptyPlaceholder>
      ) : (
        <Select
          onSearch={debouncedFetchUser}
          onPopupScroll={popupScrollHandler}
          value={isParticipant ? (value as ParticipantDataset)?.uuid : (value as Dataset)?.id}
          placeholder={placeholder || t('placeholder_select')}
          onChange={onSelectChange}
          showSearch
          allowClear
          filterOption={(inputValue, option) => {
            return option.props.extra.name.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0;
          }}
          loading={query.isFetching}
          {...props}
        >
          {options.map((item) => (
            <Select.Option
              key={isParticipant ? (item as ParticipantDataset).uuid : (item as Dataset).id}
              value={isParticipant ? (item as ParticipantDataset).uuid : (item as Dataset).id}
              extra={item}
            >
              {renderOption(item, isParticipant)}
            </Select.Option>
          ))}
          {Boolean(selectDataset && selectDataset?.name) && (
            <Select.Option
              key={
                isParticipant
                  ? (selectDataset as ParticipantDataset).uuid
                  : (selectDataset as Dataset).id
              }
              value={
                isParticipant
                  ? (selectDataset as ParticipantDataset).uuid
                  : (selectDataset as Dataset).id
              }
              extra={selectDataset}
            >
              {renderOption(selectDataset!, isParticipant)}
            </Select.Option>
          )}
        </Select>
      )}
    </>
  );

  function onSelectChange(id: string) {
    const target = options.find((item) => {
      if (isParticipant) {
        return (item as ParticipantDataset).uuid === id;
      }
      return (item as Dataset).id === id;
    });
    setSelectDataset(target);
    onChange?.(target);
  }
};

type PathProps = {
  /** Accept dataset path */
  value?: string;
  /** Accept dataset path */
  onChange?: (val?: string) => void;
};

export const DatasetPathSelect: FC<PathProps> = ({ value, onChange, ...props }) => {
  const query = useQuery([DATASET_LIST_QUERY_KEY], () => fetchDatasetList(), {
    retry: 2,
  });

  const dataset = query.data?.data.find((item) => item.path === value);

  return (
    <DatasetSelect value={dataset} onChange={onDatasetChange} {...props} isParticipant={false} />
  );

  function onDatasetChange(item?: Dataset | ParticipantDataset) {
    onChange?.((item as Dataset)?.path);
  }
};

export default DatasetSelect;
