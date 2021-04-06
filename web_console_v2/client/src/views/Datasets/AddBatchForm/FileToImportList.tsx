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
  margin-bottom: 10px;
`;
const TableContainer = styled.div`
  .ant-table-thead {
    position: sticky;
    top: 0;
    background-color: #fafafa;
  }
`;
const FileName = styled.small`
  font-size: 0.8em;
`;

const columns = [
  {
    title: i18n.t('dataset.col_file_name'),
    dataIndex: 'path',
    key: 'path',
    ellipsis: true,
    render: (path: string) => {
      return <FileName>{path}</FileName>;
    },
  },
  {
    title: i18n.t('dataset.col_files_size'),
    dataIndex: 'size',
    key: 'size',
    width: 140,
    render: (path: number) => {
      return <>{path.toLocaleString('en')} KB</>;
    },
  },
  {
    title: i18n.t('dataset.col_modification_time'),
    dataIndex: 'mtime',
    name: 'modification_time',
    width: 130,
    render: (time: number) => <div>{time ? formatTimestamp(time, 'YYYY/MM/DD HH:mm') : '-'}</div>,
  },
];

type Value = string[];
type Props = {
  value?: Value;
  onChange?: (val: Value) => any;
};

const FileToImportList: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();
  const [query, setLocalQuery] = useState({
    dateRange: [] as Dayjs[],
    name: '',
  });
  const [directory, setDirectory] = useState('');

  const listQuery = useQuery(['getFileList'], () => fetchFileList({ directory }), {
    refetchOnWindowFocus: false,
  });

  const listData = (listQuery.data?.data || [])
    .map((item) => ({ ...item, key: item.path }))
    .filter(filesFilter);

  return (
    <Container>
      <FiltersRow>
        <Input.Search
          value={directory}
          placeholder={t('dataset.placeholder_directory_filter')}
          onChange={(event) => setDirectory(event.target.value as string)}
          onSearch={() => listQuery.refetch()}
          allowClear
        />
      </FiltersRow>

      <FiltersRow align="middle" gutter={5}>
        <Col span={3}>
          <small>{t('dataset.selected_items', { count: value?.length || 0 })}</small>
        </Col>
        <Col>
          <DatePicker.RangePicker
            value={query.dateRange as any}
            onChange={onDateChange as any}
            disabledDate={disableFuture}
          />
        </Col>
        <Col span={9}>
          <Input
            value={query.name}
            suffix={<Search />}
            placeholder={t('dataset.placeholder_filename_filter')}
            onChange={onKeywordChange}
          />
        </Col>
        <Col span={2}>
          <Button type="link" size="small" onClick={onResetClick}>
            {t('reset')}
          </Button>
        </Col>
      </FiltersRow>

      <TableContainer>
        <Table
          loading={listQuery.isFetching}
          size="small"
          scroll={{ y: 350 }}
          dataSource={listData}
          pagination={false}
          columns={columns}
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
    setLocalQuery({
      ...query,
      dateRange: val,
    });
  }
  function onKeywordChange(event: any) {
    setLocalQuery({
      ...query,
      name: event.target.value,
    });
  }
  function onResetClick() {
    setLocalQuery({
      dateRange: [] as Dayjs[],
      name: '',
    });
  }
  function disableFuture(date: any) {
    return dayjs(date).valueOf() > Date.now();
  }
  function filesFilter(item: FileToImport): boolean {
    const nameMatched = item.path.includes(query.name.trim());
    const timeMatched =
      isEmpty(query.dateRange) ||
      (query.dateRange[0].isBefore(dayjs.unix(item.mtime)) &&
        query.dateRange[1].isAfter(dayjs.unix(item.mtime)));

    return nameMatched && timeMatched;
  }
};

export default FileToImportList;
