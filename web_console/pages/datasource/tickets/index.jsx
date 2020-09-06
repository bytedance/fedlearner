import React, { useState } from 'react';
import { Table, Button, Card, Text, Link } from '@zeit-ui/react';
import useSWR from 'swr';
import Layout from '../../../components/Layout';
import Form from '../../../components/Form';
import { fetcher } from '../../../libs/http';
import { createTicket, updateTicket } from '../../../services/ticket';

const DEFAULT_FIELDS = [
  { key: 'name', required: true },
  { key: 'federation_id', type: 'federation', label: 'federation', required: true },
  { key: 'job_type', type: 'jobType', required: true },
  { key: 'role', type: 'jobRole', required: true },
  { key: 'sdk_version' },
  { key: 'expire_time' },
  { key: 'public_params', type: 'json', span: 24 },
  { key: 'private_params', type: 'json', span: 24 },
  { key: 'remark', type: 'text', span: 24 },
];

function mapValueToFields(ticket, fields) {
  return fields.map((x) => {
    const field = { ...x, value: ticket[x.key] };

    if (x.key === 'name') {
      field.props = {
        disabled: true,
      };
    }

    if ((x.key === 'public_params' || x.key === 'private_params') && field.value) {
      field.value = JSON.stringify(field.value, null, 2);
    }

    return field;
  });
}

export default function TicketList() {
  const { data, mutate } = useSWR('tickets', fetcher);
  const tickets = data ? data.data : null;
  const columns = tickets && tickets.length > 0
    ? [
      ...Object.keys(tickets[0]).filter((x) => !['public_params', 'private_params', 'expire_time', 'created_at', 'updated_at', 'deleted_at'].includes(x)),
      'operation',
    ]
    : [];
  const [formVisible, setFormVisible] = useState(false);
  const [fields, setFields] = useState(DEFAULT_FIELDS);
  const [currentTicket, setCurrentTicket] = useState(null);
  const title = currentTicket ? `Edit Ticket: ${currentTicket.name}` : 'Create Ticket';
  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (ticket) => {
    mutate({
      data: [...tickets, ticket],
    });
    toggleForm();
  };
  const handleEdit = (ticket) => {
    setCurrentTicket(ticket);
    setFields(mapValueToFields(ticket, fields));
    setFormVisible(true);
  };
  const handleSubmit = (value) => {
    const json = {
      ...value,
      public_params: value.public_params ? JSON.parse(value.public_params) : null,
      private_params: value.private_params ? JSON.parse(value.private_params) : null,
    };

    if (currentTicket) {
      return updateTicket(currentTicket.id, json);
    }

    return createTicket(json);
  };
  const operation = (actions, rowData) => {
    const onHandleEdit = (e) => {
      e.preventDefault();
      handleEdit(rowData.rowValue);
    };
    return <Link href="#" color onClick={onHandleEdit}>Edit</Link>;
  };
  const dataSource = tickets
    ? tickets.map((x) => ({ ...x, operation }))
    : [];

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title={title}
            fields={fields}
            onSubmit={handleSubmit}
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