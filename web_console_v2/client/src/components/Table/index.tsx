/* istanbul ignore file */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Table, TableProps } from '@arco-design/web-react';

import { useUrlState } from 'hooks';

export interface Props<RecordType = any> extends TableProps<RecordType> {
  total?: number;
  onShowSizeChange?: (current: number, size: number) => void;
  onPageChange?: (page: number, pageSize: number) => void;
  isShowTotal?: boolean;
}

function MyTable<RecordType = any>({
  isShowTotal = true,
  className,
  ...restProps
}: Props<RecordType>) {
  const { t } = useTranslation();

  const [paginationParam, setPaginationParam] = useUrlState({
    page: 1,
    pageSize: 10,
  });

  return (
    <Table
      className={`custom-table custom-table-left-side-filter ${className}`}
      pagination={{
        showSizeChanger: true,
        onPageSizeChange: onShowSizeChange,
        onChange: onPageChange,
        showTotal: isShowTotal
          ? (total) =>
              t('hint_total_table', {
                total: total || 0,
              })
          : undefined,
        current: Number(paginationParam.page),
        pageSize: Number(paginationParam.pageSize),
      }}
      {...(restProps as any)}
    />
  );

  function onShowSizeChange(size: number, current: number) {
    restProps.onShowSizeChange && restProps.onShowSizeChange(current, size);

    setPaginationParam({
      page: current,
      pageSize: size,
    });
  }
  function onPageChange(page: number, pageSize: number) {
    restProps.onPageChange && restProps.onPageChange(page, pageSize);

    setPaginationParam({
      page: page,
      pageSize: pageSize,
    });
  }
}

export { MyTable as Table };
export default MyTable;
