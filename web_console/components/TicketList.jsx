import React, { useState } from 'react';
import { Table, Button, Card, Text } from '@zeit-ui/react';
import useSWR from 'swr';
import Form from './Form';
import { fetcher } from '../libs/http';
import { humanizeTime } from '../utils/time';
import { getTickets, createTicket, enableTicket, revokeTicket } from '../services/ticket';

export default function TicketList() {
  const { data, mutate } = useSWR('tickets', fetcher);
  const tickets = data ? data.data : null;
  const columns = tickets
    ? [
      ...Object.keys(tickets[0]).filter((x) => x !== 'password'),
      'operation',
    ]
    : [];
  const dataSource = tickets
    ? tickets.map((x) => ({
      ...x,
      is_admin: x.is_admin ? 'Yes' : 'No',
      created_at: humanizeTime(x.created_at),
      updated_at: humanizeTime(x.updated_at),
      deleted_at: humanizeTime(x.deleted_at),
    }))
    : [];
  const [formVisible, setFormVisible] = useState(false);
  const fields = [
    { key: 'name', required: true, span: 6 },
    { key: 'federation', type: 'federation', label: 'federation', required: true, span: 6 },
    { key: 'job_type', type: 'jobType', required: true, span: 6 },
    { key: 'role', type: 'jobRole', required: true, span: 6 },
    { key: 'sdk_version', required: true },
    { key: 'docker_image', required: true },
    { key: 'expire_time' },
    { key: 'public_params', type: 'json', required: true, span: 24 },
    { key: 'private_params', type: 'json', required: true, span: 24 },
    { key: 'comment', type: 'text', span: 24 },
  ];
  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (ticket) => {
    toggleForm();
  };

  if (formVisible) {
    return (
      <Form
        title="Create Ticket"
        fields={fields}
        onSubmit={(value) => createTicket(value)}
        onOk={onOk}
        onCancel={toggleForm}
      />
    );
  }

  return (
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
  );
}
