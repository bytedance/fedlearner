import React, { useState } from 'react';
import { Table, Button, Card, Text } from '@zeit-ui/react';
import useSWR from 'swr';
import Layout from '../../components/Layout';
import Form from '../../components/Form';
import PopConfirm from '../../components/PopConfirm';
import { fetcher } from '../../libs/http';
import { createTicket, revokeTicket } from '../../services/ticket';

export default function TicketList() {
  const { data, mutate } = useSWR('tickets', fetcher);
  const tickets = data ? data.data : null;
  const columns = tickets && tickets.length > 0
    ? [
      ...Object.keys(tickets[0]).filter((x) => !['public_params', 'private_params', 'expire_time', 'created_at', 'updated_at'].includes(x)),
      'operation',
    ]
    : [];
  const operation = (actions, rowData) => {
    const onConfirm = () => revokeTicket(rowData.rowValue.id);
    const onOk = (ticket) => {
      mutate({ data: tickets.map((x) => (x.id === ticket.id ? ticket : x)) });
    };
    return (
      <>
        <PopConfirm onConfirm={() => { }} onOk={() => { }}>
          <Text className="actionText" type="error">Revoke</Text>
        </PopConfirm>
      </>
    );
  };
  const dataSource = tickets
    ? tickets.map((x) => ({
      ...x,
      operation,
    }))
    : [];
  const [formVisible, setFormVisible] = useState(false);
  const fields = [
    { key: 'name', required: true },
    { key: 'federation_id', type: 'federation', label: 'federation', required: true },
    { key: 'job_type', type: 'jobType', required: true },
    { key: 'role', type: 'jobRole', required: true },
    { key: 'sdk_version', required: true },
    { key: 'expire_time' },
    { key: 'public_params', type: 'json', required: true, span: 24 },
    { key: 'private_params', type: 'json', required: true, span: 24 },
    { key: 'comment', type: 'text', span: 24 },
  ];
  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (ticket) => {
    mutate({
      data: [...tickets, ticket],
    });
    toggleForm();
  };

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title="Create Ticket"
            fields={fields}
            onSubmit={(value) => createTicket(value)}
            onOk={onOk}
            onCancel={toggleForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>Tickets</Text>
              <Button auto type="secondary" onClick={toggleForm}>Create Ticket</Button>
            </div>
            {tickets && (
              <Card>
                <Table data={dataSource}>
                  {columns.map((x) => <Table.Column key={x} prop={x} label={x} />)}
                </Table>
              </Card>
            )}
          </>
        )}
    </Layout>
  );
}
