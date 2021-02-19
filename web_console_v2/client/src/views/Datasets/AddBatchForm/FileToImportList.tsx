import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Table, Row, Col, DatePicker, Input, Button } from 'antd';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { useTranslation } from 'react-i18next';
import dayjs, { Dayjs } from 'dayjs';
import { FileToImport } from 'typings/dataset';
import { useQuery } from 'react-query';
import { fetchFileList } from 'services/dataset';
import { Search } from 'components/IconPark';
import { isEmpty } from 'lodash';

const Container = styled.div``;
const FiltersRow = styled(Row)`
  margin-bottom: 20px;
`;
const TableContainer = styled.div`
  max-height: 50vh;
  overflow: auto;
`;

const columns = [
  {
    title: i18n.t('dataset.col_file_name'),
    dataIndex: 'path',
    key: 'path',
    ellipsis: true,
    render: (path: string) => {
      return <strong>{path}</strong>;
    },
  },
  {
    title: i18n.t('dataset.col_files_size'),
    dataIndex: 'size',
    key: 'size',
    render: (path: number) => {
      return <>{path.toLocaleString('en')}</>;
    },
  },
  {
    title: i18n.t('created_at'),
    dataIndex: 'created_at',
    name: 'created_at',
    width: 190,
    render: (date: number) => <div>{formatTimestamp(date || Date.now())}</div>,
  },
];

type Value = string[];
type Props = {
  value?: Value;
  onChange?: (val: Value) => any;
};

const FileToImportList: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState({
    dateRange: [] as Dayjs[],
    name: '',
  });

  const listQuery = useQuery('getFileList', fetchFileList, {
    refetchOnWindowFocus: false,
  });

  const listData = (listQuery.data?.data || [])
    .map((item) => ({ ...item, key: item.path }))
    .filter(filesFilter);

  return (
    <Container>
      <FiltersRow align="middle" gutter={5}>
        <Col span={4}>
          <small>{t('dataset.selected_items', { count: value?.length || 0 })}</small>
        </Col>
        <Col span={9}>
          <DatePicker.RangePicker onChange={onDateChange as any} disabledDate={disableFuture} />
        </Col>
        <Col span={9}>
          <Input
            suffix={<Search />}
            placeholder={t('dataset.placeholder_filename_filter')}
            onChange={onKeywordChange}
          />
        </Col>
        <Col span={2}>
          <Button type="link" size="small">
            {t('reset')}
          </Button>
        </Col>
      </FiltersRow>

      <TableContainer>
        <Table
          loading={listQuery.isFetching}
          size="small"
          dataSource={listData}
          columns={columns}
          pagination={false}
          rowSelection={{
            onChange(_: any, selected) {
              onChange && onChange(selected.map((item) => item.path));
            },
          }}
        />
      </TableContainer>
    </Container>
  );

  function onDateChange(val: Dayjs[]) {
    setQuery({
      ...query,
      dateRange: val,
    });
  }
  function onKeywordChange(event: any) {
    setQuery({
      ...query,
      name: event.target.value,
    });
  }
  function disableFuture(date: any) {
    return dayjs(date).valueOf() > Date.now();
  }
  function filesFilter(item: FileToImport): boolean {
    const nameMatched = item.path.includes(query.name.trim());
    const timeMatched =
      isEmpty(query.dateRange) ||
      (query.dateRange[0].isBefore(dayjs.unix(item.created_at)) &&
        query.dateRange[1].isAfter(dayjs.unix(item.created_at)));

    return nameMatched && timeMatched;
  }
};

export default FileToImportList;
