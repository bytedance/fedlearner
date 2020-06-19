import React, { useState } from 'react';
import css from 'styled-jsx/css';
import { Table, Button, Card, Text, useTheme } from '@zeit-ui/react';
import useSWR from 'swr';
import Form from './Form';
import PopConfirm from './PopConfirm';
import { fetcher } from '../libs/http';
import { humanizeTime } from '../utils/time';
import { createUser, deleteUser } from '../services';

function useStyles(theme) {
  return css`
    .heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: ${theme.layout.pageMargin};
    }
  `;
}

export default function UserList() {
  const theme = useTheme();
  const styles = useStyles(theme);
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

  if (formVisible) {
    return (
      <Form
        title="Create User"
        fields={fields}
        onSubmit={(value) => createUser(value)}
        onOk={onOk}
        onCancel={toggleForm}
      />
    );
  }

  return (
    <>
      <div className="heading">
        <Text h2>Users</Text>
        <Button auto type="secondary" onClick={toggleForm}>Create User</Button>
      </div>
      {users && (
        <Card style={{ marginBottom: theme.layout.pageMargin }}>
          <Table data={dataSource}>
            {columns.map((x) => <Table.Column key={x} prop={x} label={x} />)}
          </Table>
        </Card>
      )}

      <style jsx>{styles}</style>
    </>
  );
}
