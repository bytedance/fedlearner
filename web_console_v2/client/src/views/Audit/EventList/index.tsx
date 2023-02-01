import React, { FC, useState, useMemo } from 'react';

import { useUrlState, useTablePaginationWithUrlState } from 'hooks';

import dayjs, { Dayjs } from 'dayjs';
import { useQuery } from 'react-query';
import { useGetUserInfo } from 'hooks/user';

import { fetchAuditList, deleteAudit } from 'services/audit';
import { expression2Filter } from 'shared/filter';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import {
  FILTER_EVENT_OPERATOR_MAPPER,
  EVENT_SOURCE_TYPE_MAPPER,
  EVENT_TYPE_DELETE_MAPPER,
} from '../shared';

import {
  Input,
  Button,
  Radio,
  DatePicker,
  Select,
  Message,
  Pagination,
  Tabs,
} from '@arco-design/web-react';
import { IconRefresh, IconDownload, IconDelete, IconInfoCircle } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import Modal from 'components/Modal';
import SharedPageLayout from 'components/SharedPageLayout';
import TitleWithIcon from 'components/TitleWithIcon';
import EventTable from './EventTable';

import {
  EventType,
  QueryParams,
  RadioType,
  SelectType,
  CrossDomainSelectType,
} from 'typings/audit';

import styles from './index.module.less';

const { TabPane } = Tabs;
const { Search } = Input;
const { RangePicker } = DatePicker;

type Props = {};

const EventList: FC<Props> = (props) => {
  const userInfo = useGetUserInfo();
  const {
    urlState: pageInfoState,
    reset: resetPageInfoState,
    paginationProps,
  } = useTablePaginationWithUrlState();
  const [urlState, setUrlState] = useUrlState({
    radioType: RadioType.ALL,
    selectType: SelectType.EVENT_NAME,
    crossDomainSelectType: CrossDomainSelectType.EVENT_NAME,
    eventType: EventType.INNER,
    filter: initFilter(EventType.INNER),
  });

  const initFilterParams = expression2Filter(urlState.filter);
  const keyword =
    urlState.eventType === EventType.CROSS_DOMAIN
      ? initFilterParams[urlState.crossDomainSelectType]
      : initFilterParams[urlState.selectType];
  const [filterParams, setFilterParams] = useState<QueryParams>({
    keyword: keyword || '',
    startTime: '',
    endTime: '',
  });

  const [dateList, setDateList] = useState<null | Dayjs[]>(() => {
    if (initFilterParams.start_time && initFilterParams.end_time) {
      return [dayjs.unix(initFilterParams.start_time), dayjs.unix(initFilterParams.end_time)];
    }

    if (filterParams.startTime && filterParams.endTime) {
      return [
        dayjs(filterParams.startTime, 'YYYY-MM-DD HH:mm:ss'),
        dayjs(filterParams.endTime, 'YYYY-MM-DD HH:mm:ss'),
      ];
    }
    return null;
  });

  const auditListQuery = useQuery(
    [
      'fetchAuditList',
      dateList,
      pageInfoState.page,
      pageInfoState.pageSize,
      filterParams.keyword,
      urlState.filter,
    ],
    () =>
      fetchAuditList({
        filter: urlState.filter,
        page: pageInfoState.page,
        page_size: pageInfoState.pageSize,
      }),
    {
      retry: 2,
      refetchOnWindowFocus: false,
      enabled: Boolean(userInfo?.id),
    },
  );

  const auditList = useMemo(() => {
    return auditListQuery.data?.data ?? [];
  }, [auditListQuery]);

  return (
    <SharedPageLayout
      title="审计日志"
      isNeedHelp={false}
      rightTitle={
        <TitleWithIcon
          className={styles.styled_title_icon}
          title="以下列表最长展示过去9个月的事件记录"
          isLeftIcon={true}
          isShowIcon={true}
          icon={IconInfoCircle}
        />
      }
    >
      <Tabs defaultActiveTab={urlState.eventType ?? EventType.INNER} onChange={onTabChange}>
        <TabPane key="inner" title="内部事件" destroyOnHide={false} />
        <TabPane key="cross_domain" title="跨域事件" destroyOnHide={true} />
      </Tabs>
      <GridRow justify="space-between" align="center">
        <div className={styles.left}>
          <Radio.Group
            value={urlState.radioType || null}
            onChange={onRadioTypeChange}
            type="button"
          >
            <Radio value={RadioType.ALL}>全部</Radio>
            <Radio value={RadioType.WEEK}>近七天</Radio>
            <Radio value={RadioType.ONE_MONTH}>近1月</Radio>
            <Radio value={RadioType.THREE_MONTHS}>近3月</Radio>
          </Radio.Group>
          <RangePicker showTime value={dateList as any} onChange={onRangePickerChange} />
        </div>
        <div>
          {urlState.eventType === EventType.CROSS_DOMAIN ? (
            <Select
              className={styles.styled_select}
              value={urlState.crossDomainSelectType}
              onChange={onCrossDomainSelectTypeChange}
            >
              <Select.Option value={CrossDomainSelectType.EVENT_NAME}>事件名称</Select.Option>
              <Select.Option value={CrossDomainSelectType.RESOURCE_TYPE}>资源类型</Select.Option>
              <Select.Option value={CrossDomainSelectType.RESOURCE_NAME}>资源名称</Select.Option>
              <Select.Option value={CrossDomainSelectType.COORDINATOR_PURE_DOMAIN_NAME}>
                发起方
              </Select.Option>
            </Select>
          ) : (
            <Select
              className={styles.styled_select}
              value={urlState.selectType}
              onChange={onSelectTypeChange}
            >
              <Select.Option value={SelectType.EVENT_NAME}>事件名称</Select.Option>
              <Select.Option value={SelectType.RESOURCE_TYPE}>资源类型</Select.Option>
              <Select.Option value={SelectType.RESOURCE_NAME}>资源名称</Select.Option>
              <Select.Option value={SelectType.USER_NAME}>用户名</Select.Option>
            </Select>
          )}

          <Search
            className={styles.styled_search}
            allowClear
            onSearch={onSearchTextChange}
            onClear={() => onSearchTextChange('')}
            placeholder="搜索关键词"
            defaultValue={
              filterParams.keyword ||
              initFilterParams[urlState.selectType] ||
              initFilterParams[urlState.crossDomainSelectType] ||
              ''
            }
          />
          <Button className={styles.styled_button} icon={<IconRefresh />} onClick={onRefresh} />
          <Button className={styles.styled_button} icon={<IconDownload />} onClick={onDownload} />
        </div>
      </GridRow>

      <EventTable
        event_type={urlState.eventType || EventType.INNER}
        tableData={auditList}
        isLoading={auditListQuery.isLoading}
      />
      <div className={styles.footer}>
        <Button
          className={styles.styled_footer_button}
          icon={<IconDelete />}
          onClick={onDelete}
          type="text"
        >
          删除6个月前的记录
        </Button>
        <Pagination
          sizeCanChange={true}
          total={auditListQuery.data?.page_meta?.total_items ?? undefined}
          {...paginationProps}
        />
      </div>
    </SharedPageLayout>
  );
  function onTabChange(tab: string) {
    constructFilterArray({ ...filterParams, ...urlState, eventType: tab as EventType });
  }

  function onRadioTypeChange(value: any) {
    const type: RadioType = value;

    let currentDay = null;
    let startDay: Dayjs | null = null;
    let endDay: Dayjs | null = null;
    switch (type) {
      case RadioType.WEEK:
        currentDay = dayjs();
        startDay = currentDay.subtract(7, 'day');
        endDay = dayjs();
        break;
      case RadioType.ONE_MONTH:
        currentDay = dayjs();
        startDay = currentDay.subtract(1, 'month');
        endDay = dayjs();
        break;
      case RadioType.THREE_MONTHS:
        currentDay = dayjs();
        startDay = currentDay.subtract(3, 'month');
        endDay = dayjs();
        break;
      case RadioType.ALL:
      default:
        break;
    }
    if (startDay && endDay) {
      setDateList([startDay, endDay]);
    } else {
      setDateList(null);
    }

    constructFilterArray({
      ...filterParams,
      ...urlState,
      startTime: startDay?.format('YYYY-MM-DD HH:mm:ss') ?? '',
      endTime: endDay?.format('YYYY-MM-DD HH:mm:ss') ?? '',
      radioType: type,
    });
  }
  function onSelectTypeChange(value: any) {
    constructFilterArray({ ...filterParams, ...urlState, selectType: value });
  }
  function onCrossDomainSelectTypeChange(value: any) {
    constructFilterArray({ ...filterParams, ...urlState, crossDomainSelectType: value });
  }
  function onRangePickerChange(dateString: string[], date: any[]) {
    setDateList(date as any);
    if (date) {
      // Clear radio type
      constructFilterArray({
        ...filterParams,
        ...urlState,
        startTime: date?.[0]?.format('YYYY-MM-DD HH:mm:ss') ?? '',
        endTime: date?.[1]?.format('YYYY-MM-DD HH:mm:ss') ?? '',
        radioType: undefined,
      });
    } else {
      // Reset radio type
      constructFilterArray({
        ...filterParams,
        ...urlState,
        startTime: '',
        endTime: '',
        radioType: RadioType.ALL,
      });
    }
  }
  function onSearchTextChange(value: string) {
    constructFilterArray({ ...filterParams, ...urlState, keyword: value });
  }
  function onRefresh() {
    auditListQuery.refetch();
  }
  function onDownload() {
    // TODO: onDownload
    Message.info('Coming soon');
  }
  function onDelete() {
    Modal.delete({
      title:
        urlState.eventType === EventType.CROSS_DOMAIN
          ? '确定要删除跨域事件吗'
          : '确定要删除内部事件吗？',
      content: '基于安全审核的原因，平台仅支持清理6个月前的事件记录',
      onOk() {
        // Delete audit data from 6 month ago
        deleteAudit({
          event_type: EVENT_TYPE_DELETE_MAPPER[urlState.eventType as EventType],
        })
          .then(() => {
            if (String(pageInfoState.page) !== '1') {
              // Reset page info and refresh audit list data
              resetPageInfoState();
            } else {
              // Only refresh audit list data
              auditListQuery.refetch();
            }

            Message.success('删除成功');
          })
          .catch((error) => {
            Message.error(error.message);
          });
      },
    });
  }
  function constructFilterArray(value: QueryParams) {
    let start_time = 0;
    let end_time = 0;

    if (value.startTime && value.endTime) {
      start_time = dayjs(value.startTime).utc().unix();
      end_time = dayjs(value.endTime).utc().unix();
    } else {
      const currentDay = dayjs();
      const nineMonthAgoDay = currentDay.subtract(9, 'month');
      start_time = nineMonthAgoDay.utc().unix();
      end_time = currentDay.utc().unix();
    }
    const keywordType =
      value.eventType === EventType.CROSS_DOMAIN ? value.crossDomainSelectType : value.selectType;
    const serialization = filterExpressionGenerator(
      {
        [keywordType!]: value.keyword,
        start_time: start_time,
        end_time: end_time,
        source: EVENT_SOURCE_TYPE_MAPPER[value.eventType || EventType.INNER],
      },
      FILTER_EVENT_OPERATOR_MAPPER,
    );

    setFilterParams({
      keyword: value.keyword,
      startTime: value.startTime,
      endTime: value.endTime,
    });
    setUrlState((prevState) => ({
      ...prevState,
      filter: serialization,
      radioType: value.radioType,
      selectType: value.selectType,
      crossDomainSelectType: value.crossDomainSelectType,
      eventType: value.eventType,
      page: 1,
    }));
  }
  function initFilter(event_type: EventType) {
    const currentDay = dayjs();
    const nineMonthAgoDay = currentDay.subtract(9, 'month');
    const start_time = nineMonthAgoDay.utc().unix();
    const end_time = currentDay.utc().unix();
    const filter = filterExpressionGenerator(
      {
        start_time: start_time,
        end_time: end_time,
        source: EVENT_SOURCE_TYPE_MAPPER[event_type ?? EventType.INNER],
      },
      FILTER_EVENT_OPERATOR_MAPPER,
    );
    return filter;
  }
};
export default EventList;
