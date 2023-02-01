import React, { FC, useMemo } from 'react';
import { Drawer, Table, Empty } from '@arco-design/web-react';
import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import { Cleanup } from 'typings/cleanup';
import { LabelStrong } from 'styles/elements';
import PropertyList from 'components/PropertyList';
import StateIndicator from 'components/StateIndicator';
import { calcStateIndicatorProps } from '../CleanupList';
import { formatTimestamp } from 'shared/date';
import CONSTANTS from 'shared/constants';

export interface Props extends DrawerProps {
  data?: Cleanup;
}

export interface TableProps {
  file_path?: string;
}

const CleanupDetailDrawer: FC<Props> = ({ visible, data, title = 'Cleanup详情', ...restProps }) => {
  const displayedProps = useMemo(
    () => [
      {
        value: data?.id,
        label: 'ID',
      },
      {
        value: <StateIndicator {...calcStateIndicatorProps(data?.state)} />,
        label: '状态',
      },
      {
        value: (
          <span>
            {data?.target_start_at
              ? formatTimestamp(data?.target_start_at)
              : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
        label: '目标开始时间',
      },
      {
        value: (
          <span>
            {data?.completed_at ? formatTimestamp(data?.completed_at) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
        label: '完成时间',
      },
      {
        value: <span>{data?.resource_id}</span>,
        label: 'Resource ID',
      },
      {
        value: <span>{data?.resource_type}</span>,
        label: '资源类型',
      },
      {
        value: (
          <span>
            {data?.created_at ? formatTimestamp(data?.created_at) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
        label: '创建时间',
      },
      {
        value: (
          <span>
            {data?.updated_at ? formatTimestamp(data?.updated_at) : CONSTANTS.EMPTY_PLACEHOLDER}
          </span>
        ),
        label: '更新时间',
      },
    ],
    [data],
  );

  const filePathList = useMemo(() => {
    if (!data || data.payload.paths.length === 0) return [];
    const list = data.payload.paths.map((item) => {
      return { file_path: item };
    });
    return list;
  }, [data]);

  const columns = useMemo(
    () => [
      {
        title: 'payload文件路径',
        dataIndex: 'file_path',
        name: 'file_path',
        render: (_: any, record: TableProps) => <span>{record.file_path}</span>,
      },
    ],
    [],
  );

  return (
    <Drawer
      placement="right"
      visible={visible}
      title={title}
      closable={true}
      width="50%"
      unmountOnExit
      {...restProps}
    >
      {renderBaseInfo()}
      <Table
        data={filePathList}
        columns={columns}
        rowKey="file_path"
        noDataElement={<Empty description="暂无数据" />}
      />
    </Drawer>
  );

  function renderBaseInfo() {
    return (
      <>
        <LabelStrong isBlock={true}>基础信息</LabelStrong>
        <PropertyList cols={12} colProportions={[1, 1]} properties={displayedProps} />
      </>
    );
  }
};

export default CleanupDetailDrawer;
