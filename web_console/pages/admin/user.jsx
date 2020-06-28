import React, { useState } from 'react';
import { Table, Button, Card, Text } from '@zeit-ui/react';
import useSWR from 'swr';
import Layout from '../../components/Layout';
import Form from '../../components/Form';
import PopConfirm from '../../components/PopConfirm';
import { fetcher } from '../../libs/http';
import { humanizeTime } from '../../utils/time';
import { createUser, deleteUser } from '../../services';

export default function UserList() {
  const { data, mutate } = useSWR('users', fetcher);
  const users = data ? data.data : null;
  const columns = users
    ? [
      ...Object.keys(users[0]).filter((x) => x !== 'password'),
      'operation',
    ]
    : [];
  const operation = (actions, rowData) => {
    const onConfirm = () => deleteUser(rowData.rowValue.id);
    const onOk = (user) => {
      mutate({ data: users.map((x) => (x.id === user.id ? user : x)) });
    };
    return (
      <>
        <PopConfirm onConfirm={onConfirm} onOk={onOk}>
          <Text className="actionText" type="error">Delete</Text>
        </PopConfirm>
      </>
    );
  };
  const dataSource = users
    ? users.map((x) => ({
      ...x,
      is_admin: x.is_admin ? 'Yes' : 'No',
      created_at: humanizeTime(x.created_at),
      updated_at: humanizeTime(x.updated_at),
      deleted_at: humanizeTime(x.deleted_at),
      operation,
    }))
    : [];
  const [formVisible, setFormVisible] = useState(false);
  const fields = [
    { key: 'username', required: true },
    { key: 'password', type: 'password', required: true },
    { key: 'name' },
    { key: 'email' },
    { key: 'tel', label: 'telephone' },
    { key: 'is_admin', label: 'Set as admin', type: 'boolean' },
  ];
  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (user) => {
    mutate({
      data: [...users, user],
    });
    toggleForm();
  };

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title="Create User"
            fields={fields}
            onSubmit={(value) => createUser(value)}
            onOk={onOk}
            onCancel={toggleForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>Users</Text>
              <Button auto type="secondary" onClick={toggleForm}>Create User</Button>
            </div>
            {users && (
              <Card>
                <Table data={dataSource}>
                  {columns.map((x) => <Table.Column key={x} prop={x} label={x} />)}
                </Table>
              </Card>
            )}</>
        )}
    </Layout>
  );
}
