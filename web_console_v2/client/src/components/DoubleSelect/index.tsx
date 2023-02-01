/* istanbul ignore file */

import React, { FC, useMemo, useState, useRef, useEffect } from 'react';

import { useInfiniteQuery, useQuery } from 'react-query';
import { useTranslation } from 'react-i18next';

import {
  fetchModelSetList,
  fetchModelJobList,
  fetchModelJobGroupList,
  fetchModelJobList_new,
} from 'services/modelCenter';
import { fetchProjectList, fetchProjectDetail } from 'services/algorithm';

import { Input, Grid, Select } from '@arco-design/web-react';
import { Delete } from 'components/IconPark';
import { formatListWithExtra } from 'shared/modelCenter';
import {
  AlgorithmParameter,
  AlgorithmProject,
  EnumAlgorithmProjectSource,
  EnumAlgorithmProjectType,
} from 'typings/algorithm';
import { useGetCurrentProjectId, usePrevious } from 'hooks';
import { WorkflowState } from 'typings/workflow';
import { ModelJobStatus } from 'typings/modelCenter';

import './index.less';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import {
  FILTER_MODEL_JOB_OPERATOR_MAPPER,
  FILTER_MODEL_TRAIN_OPERATOR_MAPPER,
} from 'views/ModelCenter/shared';
import { debounce } from 'lodash-es';

const { Row, Col } = Grid;

export type OptionItem = {
  /** Display label */
  label: string | number;
  /** Form value */
  value: any;
  disabled?: boolean;
  /** Extra data */
  extra?: any;
};

type Props = {
  /**
   * Form value
   *
   * { [leftField]: any,[rightField]: any }
   */
  value?: { [key: string]: any };
  onChange?: (val: any) => void;
  onLeftSelectChange?: (val: any) => void;
  onRightSelectChange?: (val: any) => void;
  onDeleteClick?: () => void;
  leftOnPopupScroll?: (element: any) => void;
  rightOnPopupScroll?: (element: any) => void;
  onLeftSearch?: (val: string) => void;
  onRightSearch?: (val: string) => void;
  /** Reset right selector when left selector change */
  isClearRightValueAfterLeftSelectChange?: boolean;
  /** Reset both side's value when left side options changed */
  isClearBothAfterLeftOptionsChange?: boolean;
  /** Left selector datasource */
  leftOptionList?: OptionItem[];
  /** Right selector datasource */
  rightOptionList?: OptionItem[];
  /** Left selector value field */
  leftField?: string;
  /** Right selector value field */
  rightField?: string;
  /** Left selector label */
  leftLabel?: string;
  /** Right selector label */
  rightLabel?: string;
  className?: any;
  /** Is show delete icon */
  isShowDelete?: boolean;
  disabled?: boolean;
  leftDisabled?: boolean;
  rightDisabled?: boolean;
  /** Container style */
  containerStyle?: React.CSSProperties;
  /** Indicate left side data fetching */
  leftLoading?: boolean;
  /** Indicate right side data fetching */
  rightLoading?: boolean;
};

export type ModelSelectProps = Props & {
  /** Cahce map, it's helpful to calc disabled per item */
  modelIdToIsSelectedMap?: {
    [key: number]: boolean;
  };
  /** Disable linkage */
  isDisabledLinkage?: boolean;
};
export type ModelGroupSelectProps = Props & {
  /** The algorithm type of the job groups */
  type: 'NN_VERTICAL' | 'NN_HORIZONTAL';
  onLeftOptionsEmpty?: () => void;
};

export type AlgorithmSelectValue = {
  algorithmProjectId?: ID;
  algorithmId?: ID;
  algorithmUuid?: ID;
  config?: AlgorithmParameter[];
  path?: string;
};
export type AlgorithmSelectProps = Omit<Props, 'leftField' | 'rightField'> & {
  value?: AlgorithmSelectValue;
  onChange?: (val: AlgorithmSelectValue) => void;
  algorithmProjectTypeList?: EnumAlgorithmProjectType[];
  disableFirstOnChange?: boolean;
  isParticipant?: boolean;
  disableHyperparameters?: boolean;
};
const DoubleSelect: FC<Props> & {
  ModelSelect: FC<ModelSelectProps>;
  AlgorithmSelect: FC<AlgorithmSelectProps>;
  ModelJobGroupSelect: FC<ModelGroupSelectProps>;
} = ({
  value,
  onChange,
  onLeftSelectChange: onLeftSelectChangeFromProps,
  onRightSelectChange: onRightSelectChangeFromProps,
  onDeleteClick,
  leftField = 'leftValue',
  rightField = 'rightValue',
  leftLabel = '',
  rightLabel = '',
  leftOptionList = [],
  rightOptionList = [],
  isClearRightValueAfterLeftSelectChange = false,
  isClearBothAfterLeftOptionsChange = false,
  className,
  isShowDelete = false,
  disabled = false,
  leftDisabled = false,
  rightDisabled = false,
  containerStyle,
  leftLoading = false,
  rightLoading = false,
  leftOnPopupScroll,
  rightOnPopupScroll,
  onLeftSearch,
  onRightSearch,
}) => {
  const isControlled = typeof value === 'object';
  const { t } = useTranslation();
  const [innerLeftValue, setInnerLeftValue] = useState();
  const [innerRightValue, setInnerRightValue] = useState();

  const leftValue = useMemo(() => {
    if (!isControlled) {
      return innerLeftValue;
    }

    if (value?.[leftField] || value?.[leftField] === 0) {
      return value[leftField];
    }

    return undefined;
  }, [value, leftField, isControlled, innerLeftValue]);

  const rightValue = useMemo(() => {
    if (!isControlled) {
      return innerRightValue;
    }

    if (value?.[rightField] || value?.[rightField] === 0) {
      return value[rightField];
    }

    return undefined;
  }, [value, rightField, isControlled, innerRightValue]);

  // clear both selectors' value when left side options changed
  const prevLeftOptionList = usePrevious(leftOptionList);
  useEffect(() => {
    // if previous option list is empty, indicating that options have just been initialized, hence ignore it.
    if (
      !isClearBothAfterLeftOptionsChange ||
      !prevLeftOptionList ||
      prevLeftOptionList.length === 0 ||
      leftOptionList.length === 0
    ) {
      return;
    }

    if (!isControlled) {
      setInnerLeftValue(undefined);
      setInnerRightValue(undefined);
    }
    onLeftSelectChangeFromProps?.(undefined);
    onChange?.({
      [leftField]: undefined,
      [rightField]: undefined,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prevLeftOptionList, leftOptionList]);

  return (
    <div className={`${className} algorithm-container`} style={containerStyle}>
      {(leftLabel || rightLabel) && (
        <Row gutter={12}>
          <Col span={12}>{leftLabel}</Col>
          <Col span={12}>{rightLabel}</Col>
        </Row>
      )}

      <Row gutter={12}>
        <Col span={12}>
          <Select
            className="algorithm-select"
            value={leftValue}
            placeholder={t('model_center.placeholder_select')}
            onChange={onLeftSelectChange}
            allowClear
            disabled={disabled || leftDisabled}
            showSearch
            loading={leftLoading}
            onPopupScroll={leftOnPopupScroll}
            filterOption={(input, option) => {
              if (option.props.children) {
                return option.props.children.toLowerCase().indexOf(input.toLowerCase()) >= 0;
              } else if (option?.props?.label) {
                return (
                  (option.props.label as string).toLowerCase().indexOf(input.toLowerCase()) >= 0
                );
              }
              return true;
            }}
            onSearch={onLeftSearch}
          >
            {leftOptionList.map((item) => {
              return (
                <Select.Option
                  key={item.value}
                  value={item.value}
                  disabled={item.disabled || disabled || leftDisabled}
                  extra={item.extra}
                >
                  {item.label}
                </Select.Option>
              );
            })}
          </Select>
        </Col>
        <Col span={12}>
          <Select
            className="algorithm-select"
            value={rightValue}
            placeholder={t('model_center.placeholder_select')}
            onChange={onRightSelectChange}
            onPopupScroll={rightOnPopupScroll}
            allowClear
            disabled={disabled || rightDisabled}
            showSearch
            loading={rightLoading}
            filterOption={(input, option) => {
              if (option?.props?.children) {
                return option.props.children.toLowerCase().indexOf(input.toLowerCase()) >= 0;
              } else if (option?.props?.label) {
                return (
                  (option.props.label as string).toLowerCase().indexOf(input.toLowerCase()) >= 0
                );
              }
              return true;
            }}
            onSearch={onRightSearch}
          >
            {rightOptionList.map((item) => {
              return (
                <Select.Option
                  key={item.value}
                  value={item.value}
                  disabled={item.disabled || disabled || rightDisabled}
                  extra={item.extra}
                >
                  {item.label}
                </Select.Option>
              );
            })}
          </Select>
        </Col>
      </Row>
      {isShowDelete && <Delete className="delete-icon" onClick={onDeleteClick} />}
    </div>
  );

  function onLeftSelectChange(val: any) {
    if (!isControlled) {
      setInnerLeftValue(val);
      if (isClearRightValueAfterLeftSelectChange) {
        setInnerRightValue(undefined);
      }
    }
    onLeftSelectChangeFromProps?.(val);
    onChange?.({
      ...value,
      [leftField]: val,
      [rightField]: isClearRightValueAfterLeftSelectChange
        ? undefined
        : isControlled
        ? value?.[rightField]
        : innerRightValue,
    });
  }
  function onRightSelectChange(val: any) {
    if (!isControlled) {
      setInnerRightValue(val);
    }
    onRightSelectChangeFromProps?.(val);
    onChange?.({
      ...value,
      [leftField]: isControlled ? value?.[leftField] : innerLeftValue,
      [rightField]: val,
    });
  }
};

export const ModelSelect: FC<ModelSelectProps> = ({
  leftField = 'model_set_id',
  rightField = 'model_id',
  modelIdToIsSelectedMap = {},
  value,
  isDisabledLinkage = false,
  ...props
}) => {
  const projectId = useGetCurrentProjectId();

  const listQuery = useQuery(['double-select-fetch-model-set-list'], () => fetchModelSetList(), {
    retry: 2,
    refetchOnWindowFocus: false,
  });

  // TODO: filter by group_id
  const modelListQuery = useQuery(
    ['double-select-fetch-model-jobs'],
    () => fetchModelJobList({ types: ['TREE_TRAINING', 'NN_TRAINING', 'TRAINING'] }),
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const leftOptionList = useMemo(() => {
    if (!listQuery.data) {
      return [];
    }

    let list = listQuery.data.data || [];

    list = formatListWithExtra(list, true);

    // filter by project_id and isCompareReport
    list = list.filter((item) => {
      return !item.isCompareReport && (!projectId || String(item.project_id) === String(projectId));
    });

    // desc sort
    list.sort((a, b) => b.created_at - a.created_at);

    return list.map((item) => ({
      label: item.name,
      value: item.id,
    }));
  }, [listQuery.data, projectId]);

  const rightOptionList = useMemo(() => {
    if (isDisabledLinkage) {
      return modelListQuery.data?.data.map((item) => ({
        label: item.name,
        value: item.id,
        disabled: modelIdToIsSelectedMap[item.id as any],
      }));
    }
    const leftValue = value?.[leftField];

    if (!modelListQuery.data || !leftValue) {
      return [];
    }

    return modelListQuery.data?.data
      .filter((item) => {
        return item.group_id === leftValue && item.state === WorkflowState.COMPLETED;
      })
      .map((item) => ({
        label: item.name,
        value: item.id,
        disabled: modelIdToIsSelectedMap[item.id as any],
      }));
  }, [modelListQuery.data, modelIdToIsSelectedMap, value, leftField, isDisabledLinkage]);

  return (
    <DoubleSelect
      value={value}
      leftField={leftField}
      rightField={rightField}
      leftOptionList={leftOptionList}
      rightOptionList={rightOptionList}
      isClearRightValueAfterLeftSelectChange={true}
      {...props}
    />
  );
};

export const ModelJobGroupSelect: FC<ModelGroupSelectProps> = ({
  type,
  onChange,
  onLeftOptionsEmpty,
  ...props
}) => {
  const projectId = useGetCurrentProjectId();
  const [selectedGroup, setSelectedGroup] = useState<number>();
  const [leftKeyWord, setLeftKeyWord] = useState<string>();
  const [rightKeyWord, setRightKeyWord] = useState<string>();

  const {
    data: pageModelJobGroupList,
    fetchNextPage: fetchModelGroupNextPage,
    isFetchingNextPage: isFetchingModelGroupNextPage,
    hasNextPage: hasModelGroupNextPage,
  } = useInfiniteQuery(
    ['fetchModelJboGroupList', projectId, type, leftKeyWord],
    ({ pageParam = 1 }) =>
      fetchModelJobGroupList(projectId!, {
        page: pageParam,
        pageSize: 10,
        filter: filterExpressionGenerator(
          {
            configured: true,
            algorithm_type: [type],
            name: leftKeyWord,
          },
          FILTER_MODEL_TRAIN_OPERATOR_MAPPER,
        ),
      }),
    {
      enabled: Boolean(projectId && type),
      keepPreviousData: true,
      getNextPageParam: (lastPage) => (lastPage.page_meta?.current_page ?? 0) + 1,
    },
  );

  const {
    data: pageModelJobList,
    fetchNextPage: fetchModelJobListNextPage,
    isFetchingNextPage: isFetchingModelJobListNextPage,
    hasNextPage: hasModelJobListNextPage,
  } = useInfiniteQuery(
    ['fetchModelJobList', selectedGroup, projectId, rightKeyWord],
    ({ pageParam = 1 }) =>
      fetchModelJobList_new(projectId!, {
        group_id: selectedGroup?.toString()!,
        page: pageParam,
        page_size: 10,
        filter: filterExpressionGenerator(
          { status: [ModelJobStatus.SUCCEEDED], name: rightKeyWord },
          FILTER_MODEL_JOB_OPERATOR_MAPPER,
        ),
      }),
    {
      enabled: Boolean(projectId && selectedGroup),
      keepPreviousData: true,
      getNextPageParam: (lastPage) => (lastPage.page_meta?.current_page ?? 0) + 1,
    },
  );

  const leftOptions = useMemo(() => {
    const resultOptions: { label: string; value: ID }[] = [];
    pageModelJobGroupList?.pages.forEach((group) => {
      resultOptions.push(...group.data.map((item) => ({ label: item.name, value: item.id })));
    });
    return resultOptions;
  }, [pageModelJobGroupList]);

  const rightOptions = useMemo(() => {
    const resultOptions: { label: string; value: ID }[] = [];
    pageModelJobList?.pages.forEach((group) => {
      resultOptions.push(...group.data.map((item) => ({ label: item.name, value: item.id })));
    });
    return resultOptions;
  }, [pageModelJobList]);

  const leftPopupScrollHandler = (element: any) => {
    const { scrollTop, scrollHeight, clientHeight } = element;
    const scrollBottom = scrollHeight - (scrollTop + clientHeight);
    const pagesNumber = pageModelJobGroupList?.pages.length || 0;
    const { current_page, total_pages } = pageModelJobGroupList?.pages?.[pagesNumber - 1]
      .page_meta || { current_page: 0, total_pages: 0 };
    if (scrollBottom < 10 && !isFetchingModelGroupNextPage && current_page < total_pages) {
      hasModelGroupNextPage && fetchModelGroupNextPage();
    }
  };
  const rightPopupScrollHandler = (element: any) => {
    const { scrollTop, scrollHeight, clientHeight } = element;
    const scrollBottom = scrollHeight - (scrollTop + clientHeight);
    const pagesNumber = pageModelJobGroupList?.pages.length || 0;
    const { current_page, total_pages } = pageModelJobGroupList?.pages?.[pagesNumber - 1]
      .page_meta || { current_page: 0, total_pages: 0 };
    if (scrollBottom < 10 && !isFetchingModelJobListNextPage && current_page < total_pages) {
      hasModelJobListNextPage && fetchModelJobListNextPage();
    }
  };

  useEffect(() => {
    if (
      props.leftField &&
      props.value?.[props.leftField] != null &&
      (!leftOptions || leftOptions.length === 0)
    ) {
      onLeftOptionsEmpty?.();
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leftOptions]);

  useEffect(() => {
    setSelectedGroup(props.leftField ? props.value?.[props.leftField] : undefined);
  }, [props.value, props.leftField]);

  return (
    <DoubleSelect
      onChange={onChange}
      leftLoading={isFetchingModelGroupNextPage}
      rightLoading={isFetchingModelJobListNextPage}
      leftOptionList={leftOptions ?? []}
      rightOptionList={rightOptions ?? []}
      onLeftSelectChange={setSelectedGroup}
      isClearBothAfterLeftOptionsChange={false}
      leftOnPopupScroll={leftPopupScrollHandler}
      rightOnPopupScroll={rightPopupScrollHandler}
      onLeftSearch={debounce((value: string) => {
        setLeftKeyWord(value);
      }, 300)}
      onRightSearch={debounce((value: string) => {
        setRightKeyWord(value);
      }, 300)}
      {...props}
    />
  );
};

export const AlgorithmSelect: FC<AlgorithmSelectProps> = ({
  value,
  onChange: onChangeFromProps,
  algorithmProjectTypeList,
  disableFirstOnChange = false,
  containerStyle,
  isParticipant = false,
  disableHyperparameters = false,
  ...props
}) => {
  const isControlled = typeof value === 'object';

  const [innerLeftValue, setInnerLeftValue] = useState<ID>();
  const [innerConfigValueList, setInnerConfigValueList] = useState<AlgorithmParameter[]>([]);
  const isAlreadyCallOnChange = useRef(false);
  const projectId = useGetCurrentProjectId();

  const { t } = useTranslation();

  const leftValue = useMemo(() => {
    if (value?.algorithmProjectId || value?.algorithmProjectId === 0) {
      return value.algorithmProjectId;
    }

    return undefined;
  }, [value]);

  const rightValue = useMemo(() => {
    if (value?.algorithmId || value?.algorithmId === 0) {
      return value?.algorithmId;
    }

    return undefined;
  }, [value]);

  const configValueList = useMemo(() => {
    if (value?.config) {
      return value.config;
    }

    return innerConfigValueList;
  }, [value, innerConfigValueList]);

  const algorithmProjectQuery = useQuery(
    ['getAllAlgorithmProjectList', projectId, ...(algorithmProjectTypeList ?? [])],
    async () => {
      let data: AlgorithmProject[] = [];
      try {
        if (projectId) {
          const resp = await fetchProjectList(projectId ?? 0, {
            type: algorithmProjectTypeList ? algorithmProjectTypeList : undefined,
          });
          data = data.concat(resp.data || []);
        }

        // preset algorithm
        const resp = await fetchProjectList(0, {
          type: algorithmProjectTypeList ? algorithmProjectTypeList : undefined,
          sources: EnumAlgorithmProjectSource.PRESET,
        });
        data = data.concat(resp.data || []);
      } catch (error) {}

      return { data };
    },

    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const algorithmProjectDetailQuery = useQuery(
    ['getAlgorithmProjectDetail', leftValue, innerLeftValue],
    () => fetchProjectDetail(isControlled ? leftValue! : innerLeftValue!),
    {
      enabled:
        (isControlled
          ? leftValue !== null && leftValue !== undefined
          : innerLeftValue !== null && innerLeftValue !== undefined) && !isParticipant,
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        if (
          isAlreadyCallOnChange.current ||
          (!leftValue && leftValue !== 0) ||
          (!rightValue && rightValue !== 0) ||
          disableFirstOnChange
        ) {
          return;
        }

        const rightItem = (res.data?.algorithms ?? []).find((item) => item.id === rightValue);

        // Because it is necessary to get extra info in edit mode, so call onChangeFromProps manually
        onChangeFromProps?.({
          algorithmProjectId: leftValue,
          algorithmId: rightValue,
          config: value?.config ?? rightItem?.parameter?.variables ?? [],
          path: value?.path ?? rightItem?.path ?? '',
          algorithmUuid: rightItem?.uuid ?? '',
        });
      },
    },
  );

  const leftOptionList = useMemo(() => {
    if (!algorithmProjectQuery.data) {
      return [];
    }

    const list = algorithmProjectQuery.data.data || [];

    return list.map((item) => ({
      label: item.name,
      value: item.id,
      extra: item,
    }));
  }, [algorithmProjectQuery.data]);

  const rightOptionList = useMemo(() => {
    if (
      !algorithmProjectDetailQuery.data ||
      (isControlled && !leftValue && leftValue !== 0) ||
      (!isControlled && !innerLeftValue && innerLeftValue !== 0)
    ) {
      return [];
    }

    return (algorithmProjectDetailQuery.data?.data?.algorithms ?? []).map((item) => ({
      label: `V${item.version}`,
      value: item.id,
      extra: item,
    }));
  }, [algorithmProjectDetailQuery.data, isControlled, leftValue, innerLeftValue]);

  return (
    <div style={containerStyle}>
      {!isParticipant && (
        <DoubleSelect
          value={value}
          leftField="algorithmProjectId"
          rightField="algorithmId"
          leftOptionList={leftOptionList}
          rightOptionList={rightOptionList}
          isClearRightValueAfterLeftSelectChange={true}
          onChange={onChange}
          containerStyle={containerStyle}
          {...props}
        />
      )}
      {configValueList.length > 0 && (
        <>
          {!isParticipant && (
            <Row gutter={[12, 12]}>
              <Col span={12}>{t('hyper_parameters')}</Col>
            </Row>
          )}
          <Row gutter={[12, 12]}>
            {configValueList.map((item, index) => (
              <React.Fragment key={`${item.name}_${index}`}>
                <Col span={12}>
                  <Input
                    defaultValue={item.name}
                    onChange={(_, event) => onConfigValueChange(event.target.value, 'name', index)}
                    disabled={true}
                  />
                </Col>
                <Col span={12}>
                  <Input
                    defaultValue={item.value}
                    onChange={(_, event) => onConfigValueChange(event.target.value, 'value', index)}
                    disabled={disableHyperparameters}
                  />
                </Col>
              </React.Fragment>
            ))}
          </Row>
        </>
      )}
      {isParticipant && configValueList.length <= 0 && (
        <Input disabled placeholder="对侧无算法超参数，无需配置" />
      )}
    </div>
  );

  function onChange(val: { algorithmProjectId: ID; algorithmId: ID }) {
    isAlreadyCallOnChange.current = true;
    const rightItem = rightOptionList.find((item) => item.value === val.algorithmId);

    const config = rightItem?.extra?.parameter?.variables ?? [];
    const path = rightItem?.extra?.path ?? [];
    const algorithmUuid = rightItem?.extra?.uuid;

    if (!isControlled) {
      if (leftValue !== val.algorithmProjectId) {
        setInnerLeftValue(val.algorithmProjectId);
      }

      setInnerConfigValueList(config);
    }

    onChangeFromProps?.({
      ...val,
      config,
      path,
      algorithmUuid,
    });
  }

  function onConfigValueChange(val: string, key: string, index: number) {
    const newConfigValueList = [...configValueList];
    newConfigValueList[index] = { ...newConfigValueList[index], [key]: val };

    if (!isControlled) {
      setInnerConfigValueList(newConfigValueList);
    }

    onChangeFromProps?.({
      ...value,
      config: newConfigValueList,
    });
  }
};

DoubleSelect.ModelSelect = ModelSelect;
DoubleSelect.ModelJobGroupSelect = ModelJobGroupSelect;
DoubleSelect.AlgorithmSelect = AlgorithmSelect;

export default DoubleSelect;
