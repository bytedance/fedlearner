import React, { useState } from 'react';
import { Table, Button, Card, Text, Link } from '@zeit-ui/react';
import NextLink from 'next/link';
import useSWR from 'swr';
import Layout from '../../components/Layout';
import Form from '../../components/Form';
// import PopConfirm from '../../components/PopConfirm';
import { fetcher } from '../../libs/http';
import Empty from '../../components/Empty';
import { createRawData } from '../../services/raw_data';

const fields = [
  { key: 'name', required: true },
  { key: 'output_partition_num', required: true },
  { key: 'data_portal_type', type: 'dataPortalType', required: true },
  { key: 'input', required: true, label: 'input_base_dir', span: 12, props: { width: '95%' } },
  { key: 'output', required: true, label: 'output_base_dir', span: 12, props: { width: '95%' } },
  { key: 'context', type: 'json', span: 24 },
  { key: 'comment', type: 'text', span: 24 },
];

export default function RawDataList() {
  const { data, mutate } = useSWR('raw_datas', fetcher);
  const rawDatas = data ? data.data : null;
  const columns = ['id', 'name', 'input', 'output', 'operation'];
  // eslint-disable-next-line arrow-body-style
  const operation = (actions, rowData) => {
    // const onConfirm = () => revokeRawData(rowData.rowValue.id);
    // const onOk = (rawData) => {
    //   mutate({ data: rawDatas.map((x) => (x.id === rawData.id ? rawData : x)) });
    // };
    return (
      <>
        <NextLink
          href={`/raw_data/${rowData.rowValue.id}`}
        >
          <Link color>View Detail</Link>
        </NextLink>
        {/* <PopConfirm onConfirm={() => { }} onOk={() => { }}>
          <Text className="actionText" type="error">Revoke</Text>
        </PopConfirm> */}
      </>
    );
  };
  const dataSource = rawDatas
    ? rawDatas.map((x) => {
      const context = JSON.stringify(x.context);
      return {
        ...x,
        context,
        operation,
      };
    })
    : [];
  const [formVisible, setFormVisible] = useState(false);

  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (rawData) => {
    mutate({
      data: [rawData, ...rawDatas],
    });
    toggleForm();
  };

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title="Create Raw Data"
            fields={fields}
            onSubmit={(value) => createRawData(value)}
            onOk={onOk}
            onCancel={toggleForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>RawDatas</Text>
              <Button auto type="secondary" onClick={toggleForm}>Create Raw Data</Button>
            </div>
            {rawDatas && (
              <Card>
                <Table data={dataSource}>
                  {columns.map((x) => <Table.Column key={x} prop={x} label={x} />)}
                </Table>
                {
                  rawDatas.length
                    ? null
                    : <Empty style={{ paddingBottom: 0 }} />
                }
              </Card>
            )}
          </>
        )}
    </Layout>
  );
}
