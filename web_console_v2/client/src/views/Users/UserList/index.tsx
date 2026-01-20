import React, { FC, useMemo } from 'react';
import styled from './index.module.less';
import { useHistory, Link } from 'react-router-dom';
import { useQuery } from 'react-query';

import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { transformRegexSpecChar } from 'shared/helpers';
import { deleteUser, getAllUsers } from 'services/user';
import { useUrlState, useTablePaginationWithUrlState } from 'hooks';

import { Table, Button, Grid, Input, Message, Tag, Form, Space } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import NoResult from 'components/NoResult';
import UserRoleBadge from 'components/UserRoleBadge';
import MoreActions from 'components/MoreActions';
import Modal from 'components/Modal';

import { FedRoles, FedUserInfo } from 'typings/auth';

const { Row } = Grid;

export const USERS_LIST_QUERY_KEY = 'userList';

const UsersList: FC = () => {
  const [form] = Form.useForm();

  const history = useHistory();
  const userInfo = useRecoilQuery(userInfoQuery);
  const [urlState, setUrlState] = useUrlState({ keyword: '' });
  const { paginationProps } = useTablePaginationWithUrlState();

  const columns = useMemo(() => {
    return [
      {
        title: 'ID',
        dataIndex: 'id',
        key: 'id',
        render: (id: number) => {
          return <strong>{id}</strong>;
        },
      },
      {
        title: '用户名',
        dataIndex: 'username',
        key: 'username',
        render: (username: string, record: FedUserInfo) => {
          return (
            <>
              <Link to={`/users/edit/${record.id}`}>{username}</Link>
              {record.id === userInfo.data?.id && (
                <Tag color="arcoblue" style={{ marginLeft: '5px' }}>
                  {'本账号'}
                </Tag>
              )}
            </>
          );
        },
      },
      {
        title: '角色',
        dataIndex: 'role',
        key: 'role',
        render: (role: FedRoles) => {
          return <UserRoleBadge role={role} />;
        },
      },
      {
        title: '邮箱',
        dataIndex: 'email',
        key: 'email',
      },
      {
        title: '显示名',
        dataIndex: 'name',
        key: 'name',
      },
      {
        title: 'Operations',
        key: 'operations',
        render: (_: number, record: FedUserInfo) => {
          return (
            <Space>
              <button className="custom-text-button" onClick={() => goEdit(record)}>
                {'编辑'}
              </button>
              <MoreActions
                actionList={[
                  {
                    label: '删除',
                    disabled: record.id === userInfo.data?.id,
                    disabledTip: '不能删除自己的账号',
                    onClick: () => {
                      Modal.delete({
                        title: '确认删除该用户吗？',
                        content: '删除后，该用户将无法操作，请谨慎删除',
                        onOk() {
                          onDeleteClick(record);
                        },
                      });
                    },
                    danger: true,
                  },
                ]}
              />
            </Space>
          );
        },
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userInfo]);

  const query = useQuery([USERS_LIST_QUERY_KEY], () => getAllUsers(), {
    retry: 2,
    cacheTime: 0,
  });

  const userListShow = useMemo(() => {
    if (!query.data) {
      return [];
    }

    let userList = query.data?.data || [];

    if (urlState.keyword) {
      const regx = new RegExp(`^.*${transformRegexSpecChar(urlState.keyword)}.*$`); // support fuzzy matching

      userList = userList.filter((item) => {
        if (regx.test(String(item.name)) || regx.test(item.username)) {
          return true;
        }
        return false;
      });
    }

    return userList;
  }, [urlState.keyword, query.data]);

  const isEmpty = !query.isFetching && userListShow.length === 0;

  return (
    <SharedPageLayout title={'用户管理'}>
      <Row justify="space-between" align="center">
        <Button type="primary" onClick={goCreate}>
          {'创建用户'}
        </Button>
        <Form
          initialValues={{ ...urlState }}
          form={form}
          onSubmit={onSearch}
          style={{ width: 280 }}
          labelCol={{ span: 0 }}
          wrapperCol={{ span: 24 }}
        >
          <Form.Item
            field="keyword"
            style={{
              marginBottom: 0,
            }}
          >
            <Input.Search
              placeholder={'输入关键词搜索用户'}
              onSearch={form.submit}
              onClear={form.submit}
              allowClear
            />
          </Form.Item>
        </Form>
      </Row>
      <div className={styled.list_container}>
        {isEmpty ? (
          <NoResult text={'暂无用户'} to="/users/create" />
        ) : (
          <Table
            loading={query.isFetching}
            data={userListShow}
            scroll={{ x: '100%' }}
            columns={columns}
            rowKey="id"
            pagination={{ ...paginationProps }}
          />
        )}
      </div>
    </SharedPageLayout>
  );

  function goCreate() {
    history.push('/users/create');
  }
  function goEdit(userInfo: FedUserInfo) {
    history.push(`/users/edit/${userInfo.id}`);
  }
  function onSearch(values: any) {
    setUrlState({ ...values, page: 1 });
  }
  function onDeleteClick(userInfo: FedUserInfo) {
    deleteUser(userInfo.id!.toString())
      .then(() => {
        Message.success('删除成功');
        query.refetch();
      })
      .catch((error) => {
        Message.error(error.message);
      });
  }
};

export default UsersList;
