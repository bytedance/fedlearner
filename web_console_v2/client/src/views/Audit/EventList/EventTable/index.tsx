import React, { FC, useState } from 'react';
import { systemInfoQuery } from 'stores/app';
import { useRecoilQuery } from 'hooks/recoil';

import { formatTimestamp } from 'shared/date';
import WhichParticipants from '../WhichParticipants';

import { CONSTANTS } from 'shared/constants';

import { Table, Tag } from '@arco-design/web-react';
import { Label, LabelTint } from 'styles/elements';
import EventDetailDrawer from '../EventDetailDrawer';

import { EventType, Audit } from 'typings/audit';

import styles from './index.module.less';

interface Props {
  event_type: EventType;
  tableData: Audit[];
  isLoading: boolean;
}

const EventTable: FC<Props> = ({ event_type, tableData, isLoading }) => {
  const [isShowEventDetailDrawer, setIsShowEventDetailDrawer] = useState(false);
  const [selectedAudit, setSelectedAudit] = useState<Audit>();

  const { data: systemInfo } = useRecoilQuery(systemInfoQuery);
  const { name: myName, domain_name: myDomainName, pure_domain_name: myPureDomainName } =
    systemInfo || {};
  const columns = [
    {
      title: '事件时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 250,
      fixed: 'left',
      render: (value: any, record: any) => {
        return (
          <span
            className={styles.click_text}
            onClick={() => {
              setSelectedAudit(record);
              setIsShowEventDetailDrawer(() => true);
            }}
          >
            {value ? formatTimestamp(value) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        );
      },
    },
    {
      title: '用户名',
      dataIndex: 'user',
      key: 'user',
      render: (_value: any, record: any) => {
        return (
          <>
            <Label marginRight={8} fontSize={14}>
              {record.user?.username}
            </Label>
            <LabelTint fontSize={14}>{record.user?.role}</LabelTint>
          </>
        );
      },
    },
    {
      title: '事件名称',
      dataIndex: 'name',
      key: 'name',
      render: (value: any) => value || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      render: (value: any) => value || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      title: '资源名称',
      dataIndex: 'resource_name',
      key: 'resource_name',
      render: (value: any) => value || CONSTANTS.EMPTY_PLACEHOLDER,
    },
  ];
  const cross_domain_columns = [
    {
      title: '事件时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 250,
      fixed: 'left',
      render: (value: any, record: any) => {
        return (
          <span
            className={styles.click_text}
            onClick={() => {
              setSelectedAudit(record);
              setIsShowEventDetailDrawer(() => true);
            }}
          >
            {value ? formatTimestamp(value) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        );
      },
    },
    {
      title: '发起方',
      dataIndex: 'coordinator_pure_domain_name',
      key: 'coordinator_pure_domain_name',
      render: (value: any, record: any) => {
        return (
          <>
            {value === myPureDomainName ? (
              <>
                <Label marginRight={8} fontSize={14}>
                  {systemInfo?.name}
                </Label>{' '}
                <Tag color="arcoblue"> 本侧</Tag>
              </>
            ) : (
              <Label marginRight={8} fontSize={14}>
                <WhichParticipants showCoordinator={true} pureDomainName={value} />
              </Label>
            )}
          </>
        );
      },
    },
    {
      title: '协作方',
      dataIndex: 'project_id',
      key: 'participants',
      render: (value: any, record: any) => (
        <WhichParticipants
          currentDomainName={
            record.coordinator_pure_domain_name !== myPureDomainName ? myDomainName : undefined
          }
          currentName={
            record.coordinator_pure_domain_name !== myPureDomainName ? myName : undefined
          }
          pureDomainName={record.coordinator_pure_domain_name}
          projectId={value}
        />
      ),
    },

    {
      title: '事件名称 ',
      dataIndex: 'name',
      key: 'name',
      render: (value: any) => value || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      title: '资源类型 ',
      dataIndex: 'resource_type',
      key: ' resource_type',
      render: (value: any) => value || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      title: ' 资源名称 ',
      dataIndex: 'resource_name',
      key: 'resource_name',
      render: (value: any) => value || CONSTANTS.EMPTY_PLACEHOLDER,
    },
  ];

  return (
    <>
      <Table<Audit>
        className={`${styles.styled_table} ${styles.event_margin}`}
        rowKey="uuid"
        data={tableData}
        loading={isLoading}
        columns={(event_type === EventType.CROSS_DOMAIN ? cross_domain_columns : columns) as any}
        pagination={false}
        onRow={(record) => ({
          onClick: () => {
            setSelectedAudit(record);
            setIsShowEventDetailDrawer(() => true);
          },
        })}
      />
      <EventDetailDrawer
        visible={isShowEventDetailDrawer}
        data={selectedAudit}
        onCancel={onEventDetailDrawerClose}
        event_type={event_type}
      />
    </>
  );
  function onEventDetailDrawerClose() {
    setIsShowEventDetailDrawer(false);
    setSelectedAudit(undefined);
  }
};

export default EventTable;
