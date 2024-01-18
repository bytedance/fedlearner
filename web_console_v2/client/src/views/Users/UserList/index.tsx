import React, { FC, useState, useMemo } from 'react';
import SharedPageLayout from 'components/SharedPageLayout';
import { useTranslation } from 'react-i18next';
import { Row, Button, Col, Form, Input, Table, message, Tag, Popconfirm } from 'antd';
import { useHistory, Link } from 'react-router-dom';
import styled from 'styled-components';
import { useQuery } from 'react-query';
import { deleteUser, getAllUsers } from 'services/user';
import NoResult from 'components/NoResult';
import i18n from 'i18n';
import { FedRoles, FedUserInfo } from 'typings/auth';
import GridRow from 'components/_base/GridRow';
import UserRoleBadge from 'components/UserRoleBadge';
import { userInfoQuery } from 'stores/user';
import { useRecoilQuery } from 'hooks/recoil';

const ListContainer = styled.div`
  display: flex;
  flex: 1;
`;

export const USERS_LIST_QUERY_KEY = 'userList';

const UsersList: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const [params, setParams] = useState({ keyword: '' });
  const [form] = Form.useForm();
  const userInfo = useRecoilQuery(userInfoQuery);

  const columns = useMemo(() => {
    return [
      {
        title: i18n.t('users.col_id'),
        dataIndex: 'id',
        key: 'id',
        render: (id: number) => {
          return <strong>{id}</strong>;
        },
      },
      {
        title: i18n.t('users.col_username'),
        dataIndex: 'username',
        key: 'username',
        render: (username: string, record: FedUserInfo) => {
          return (
            <>
              <Link to={`/users/edit/${record.id}`}>{username}</Link>
              {record.id === userInfo.data?.id && (
                <Tag color="geekblue" style={{ marginLeft: '5px' }}>
                  {i18n.t('users.yourself')}
                </Tag>
              )}
            </>
          );
        },
      },
      {
        title: i18n.t('users.col_role'),
        dataIndex: 'role',
        key: 'role',
        render: (role: FedRoles) => {
          return <UserRoleBadge role={role} />;
        },
      },
      {
        title: i18n.t('users.col_email'),
        dataIndex: 'email',
        key: 'email',
      },
      {
        title: i18n.t('users.col_name'),
        dataIndex: 'name',
        key: 'name',
      },
      {
        title: i18n.t('users.col_ops'),
        key: 'operations',
        render: (_: number, record: FedUserInfo) => {
          return (
            <GridRow left={-10} gap="8">
              <Button size="small" onClick={() => goEdit(record)} type="link">
                {t('edit')}
              </Button>
              {record.id !== userInfo.data?.id && (
                <Popconfirm
                  title={t('users.message_del_user')}
                  onConfirm={() => onDeleteClick(record)}
                >
                  <Button danger size="small" type="link">
                    {t('delete')}
                  </Button>
                </Popconfirm>
              )}
            </GridRow>
          );
        },
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t, userInfo]);

  const query = useQuery([USERS_LIST_QUERY_KEY, params.keyword], () => getAllUsers(), {
    retry: 2,
    cacheTime: 0,
  });

  const isEmpty = !query.isFetching && query.data?.data.length === 0;

  return (
    <SharedPageLayout title={t('menu.label_users')}>
      <Row gutter={16} justify="space-between" align="middle">
        <Col>
          <Button size="large" type="primary" onClick={goCreate}>
            {t('users.btn_create_user')}
          </Button>
        </Col>
        <Col>
          <Form initialValues={{ ...params }} layout="inline" form={form} onFinish={onSearch}>
            <Form.Item name="keyword">
              <Input.Search
                placeholder={t('users.placeholder_name_searchbox')}
                onPressEnter={form.submit}
              />
            </Form.Item>
          </Form>
        </Col>
      </Row>
      <ListContainer>
        {isEmpty ? (
          <NoResult text={t('users.no_result')} to="/users/modify" />
        ) : (
          <Table
            loading={query.isFetching}
            dataSource={query.data?.data || []}
            scroll={{ x: '100%' }}
            columns={columns}
            rowKey="name"
          />
        )}
      </ListContainer>
    </SharedPageLayout>
  );

  function goCreate() {
    history.push('/users/create');
  }
  function goEdit(userInfo: FedUserInfo) {
    history.push(`/users/edit/${userInfo.id}`);
  }
  function onSearch(values: any) {
    setParams(values);
  }
  function onDeleteClick(userInfo: FedUserInfo) {
    deleteUser(userInfo.id!.toString())
      .then(() => {
        message.success(t('users.msg_delete_done'));
        query.refetch();
      })
      .catch((err) => {
        message.error(err.message);
      });
  }
};

export default UsersList;
