import React, { useState } from 'react';
import { Table, Button, Card, Text, Link } from '@zeit-ui/react';
import useSWR from 'swr';
import Layout from '../../components/Layout';
import Form from '../../components/Form';
import PopConfirm from '../../components/PopConfirm';
import { fetcher } from '../../libs/http';
import { humanizeTime } from '../../utils/time';
import { createUser, updateUser, deleteUser } from '../../services';

const DEFAULT_FIELDS = [
  { key: 'username', required: true },
  { key: 'password', type: 'password', required: true },
  { key: 'name' },
  { key: 'email' },
  { key: 'tel', label: 'telephone' },
  { key: 'is_admin', label: 'Set as admin', type: 'boolean' },
];

function mapValueToFields(user, fields) {
  return fields.map((x) => {
    const field = { ...x, value: user[x.key] };

    if (x.key === 'username') {
      field.props = {
        disabled: true,
      };
    }

    return field;
  });
}

export default function UserList() {
  const { data, mutate } = useSWR('users', fetcher);
  const users = data ? data.data : null;
  const columns = users
    ? [
      // users won't be null
      ...Object.keys(users[0]).filter((x) => !['password', 'updated_at', 'deleted_at'].includes(x)),
      'operation',
    ]
    : [];
  const [formVisible, setFormVisible] = useState(false);
  const [fields, setFields] = useState(DEFAULT_FIELDS);
  const [currentUser, setCurrentUser] = useState(null);
  const title = currentUser ? `Edit User: ${currentUser.name}` : 'Create User';
  const toggleForm = () => {
    setFormVisible(!formVisible);
    setCurrentUser(null);
    setFields(DEFAULT_FIELDS);
  };
  const handleEdit = (user) => {
    setCurrentUser(user);
    setFields(mapValueToFields(user, fields));
    setFormVisible(true);
  };
  const operation = (actions, rowData) => {
    const onConfirm = () => deleteUser(rowData.rowValue.id);
    const onOk = (user) => {
      mutate({ data: users.map((x) => (x.id === user.id ? user : x)) });
    };
    const onHandleEdit = (e) => {
      e.preventDefault();
      handleEdit(rowData.rowValue);
    };

    return (
      <>
        <Link href="#" color style={{ marginRight: '8px' }} onClick={onHandleEdit}>Edit</Link>
        <PopConfirm onConfirm={onConfirm} onOk={onOk}>
          <Text className="actionText" type="error">Delete</Text>
        </PopConfirm>
      </>
    );
  };
  const dataSource = users
    ? users.map((x) => ({
      ...x,
      is_admin_label: x.is_admin ? 'Yes' : 'No',
      created_at: humanizeTime(x.created_at),
      updated_at: humanizeTime(x.updated_at),
      deleted_at: humanizeTime(x.deleted_at),
      operation,
    }))
    : [];
  const onOk = (user) => {
    mutate({
      data: [...users, user],
    });
    toggleForm();
  };
  const handleSubmit = (value) => {
    const json = { ...value };

    if (currentUser) {
      return updateUser(currentUser.id, json);
    }

    return createUser(json);
  };

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
              <Text h2>Users</Text>
              <Button auto type="secondary" onClick={toggleForm}>Create User</Button>
            </div>
            {users && (
              <Card>
                <Table data={dataSource}>
                  {columns.map((x) => <Table.Column key={x} prop={x === 'is_admin' ? 'is_admin_label' : x} label={x} />)}
                </Table>
              </Card>
            )}</>
        )}
    </Layout>
  );
}
