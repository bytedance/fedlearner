import React, { FC, useMemo, useState } from 'react';
import { useHistory, useParams } from 'react-router';
import { useQuery } from 'react-query';
import {
  Button,
  Grid,
  Input,
  Message,
  Progress,
  Space,
  Tabs,
  Tag,
  Tooltip,
} from '@arco-design/web-react';
import { useGetCurrentProjectId } from 'hooks';
import { useTranslation } from 'react-i18next';

import Modal from 'components/Modal';
import BackButton from 'components/BackButton';
import SharedPageLayout from 'components/SharedPageLayout';
import WhichParticipant from 'components/WhichParticipant';
import MoreActions from 'components/MoreActions';
import PropertyList from 'components/PropertyList';
import WhichDataset from 'components/WhichDataset';

import atomIcon from 'assets/icons/atom-icon-algorithm-management.svg';
import { Avatar } from '../shared';
import routeMaps from '../routes';
import { formatTimestamp } from 'shared/date';
import CONSTANTS from 'shared/constants';
import styled from './index.module.less';

import {
  deleteTrustedJobGroup,
  fetchTrustedJobGroupById,
  launchTrustedJobGroup,
} from 'services/trustedCenter';
import {
  AuthStatus,
  TrustedJobGroup,
  TrustedJobGroupStatus,
  TrustedJobGroupTabType,
} from 'typings/trustedCenter';
import ComputingJobTab from './ComputingJobTab';
import ExportJobTab from './ExportJobTab';
import { to } from 'shared/helpers';
import { getTicketAuthStatus } from 'shared/trustedCenter';

const Row = Grid.Row;
const Col = Grid.Col;

export enum CommentModalType {
  INITIATE = 'initiate',
  EDIT = 'edit',
}

const TrustedJobGroupDetail: FC<{ isEdit?: boolean }> = ({ isEdit }) => {
  const history = useHistory();
  const { t } = useTranslation();
  const projectId = useGetCurrentProjectId();
  const params = useParams<{ id: string; tabType: TrustedJobGroupTabType }>();
  const [trustedJobGroup, setTrustedJobGroup] = useState<TrustedJobGroup>();
  const [commentVisible, setCommentVisible] = useState(false);
  const [comment, setComment] = useState('');

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const trustedJobGroupQuery = useQuery(
    ['fetchTrustedJobGroupById', params.id],
    () => {
      return fetchTrustedJobGroupById(projectId!, params.id);
    },
    {
      retry: 1,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        setTrustedJobGroup(res.data);
      },
    },
  );

  const displayedProps = useMemo(
    () => [
      {
        value:
          trustedJobGroup?.coordinator_id === 0 ? (
            t('trusted_center.label_coordinator_self')
          ) : (
            <WhichParticipant id={trustedJobGroup?.coordinator_id} />
          ),
        label: t('trusted_center.col_trusted_job_coordinator'),
      },
      {
        value: (
          <div>
            <div>{getTicketAuthStatus(trustedJobGroup!).text}</div>
            <Progress
              percent={getTicketAuthStatus(trustedJobGroup!).percent}
              showText={false}
              style={{ width: 100 }}
              status={getTicketAuthStatus(trustedJobGroup!).type}
            />
          </div>
        ),
        label: t('trusted_center.col_trusted_job_status'),
      },
      {
        value: renderDatasetTooltip(trustedJobGroup!),
        label: t('trusted_center.col_trusted_job_dataset'),
      },
      {
        value: trustedJobGroup?.creator_username || CONSTANTS.EMPTY_PLACEHOLDER,
        label: t('trusted_center.col_trusted_job_creator'),
      },
      {
        value: formatTimestamp(trustedJobGroup?.updated_at || 0),
        label: t('trusted_center.col_trusted_job_update_at'),
      },
      {
        value: formatTimestamp(trustedJobGroup?.created_at || 0),
        label: t('trusted_center.col_trusted_job_create_at'),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [trustedJobGroup],
  );

  return (
    <SharedPageLayout
      title={
        <BackButton onClick={goBackToListPage}>
          {t('trusted_center.label_trusted_center')}
        </BackButton>
      }
      cardPadding={0}
    >
      <div className={styled.padding_container}>
        <Row>
          <Col span={12}>
            <Space size="medium">
              <Avatar data-name={CONSTANTS.EMPTY_PLACEHOLDER} bgSrc={atomIcon} />
              <div>
                <div className={styled.header_name}>
                  <div>{trustedJobGroup?.name ?? '....'}</div>
                  <Tag className={styled.header_name__tag}>可信计算</Tag>
                  <Tag className={styled.header_name__tag}> {`ID  ${params.id}`}</Tag>
                </div>
                <Space className={styled.header_comment}>
                  {trustedJobGroup?.comment ?? CONSTANTS.EMPTY_PLACEHOLDER}
                </Space>
              </div>
            </Space>
          </Col>
          <Col span={12} className={styled.header_col}>
            <Space>
              <Button
                type="primary"
                disabled={
                  !trustedJobGroup?.name ||
                  trustedJobGroup.status !== TrustedJobGroupStatus.SUCCEEDED ||
                  trustedJobGroup.auth_status !== AuthStatus.AUTHORIZED ||
                  trustedJobGroup.unauth_participant_ids?.length !== 0
                }
                onClick={() => {
                  setCommentVisible(true);
                }}
              >
                {t('trusted_center.btn_post_task')}
              </Button>
              <Button
                disabled={
                  !trustedJobGroup?.name ||
                  trustedJobGroup.status !== TrustedJobGroupStatus.SUCCEEDED
                }
                onClick={() =>
                  trustedJobGroup?.coordinator_id
                    ? history.push(`/trusted-center/edit/${params.id}/receiver`)
                    : history.push(`/trusted-center/edit/${params.id}/sender`)
                }
              >
                {t('edit')}
              </Button>
              <MoreActions
                actionList={[
                  {
                    label: t('delete'),
                    danger: true,
                    disabled: !trustedJobGroup?.name || Boolean(trustedJobGroup.coordinator_id),
                    onClick: () => {
                      Modal.confirm({
                        title: `确认删除${trustedJobGroup?.name || ''}吗?`,
                        content: '删除后，该可信计算将无法进行操作，请谨慎删除',
                        onOk() {
                          deleteTrustedJobGroup(projectId!, params.id)
                            .then(() => {
                              Message.success(t('trusted_center.msg_delete_success'));
                            })
                            .catch((error) => {
                              Message.error(error.message);
                            });
                        },
                      });
                    },
                  },
                ]}
              />
            </Space>
          </Col>
        </Row>
        <PropertyList
          cols={6}
          colProportions={[1, 1, 1, 1, 1.5, 1.5]}
          properties={displayedProps}
        />
      </div>
      <Tabs
        defaultActiveTab={params.tabType}
        onChange={(tab) => history.push(getTabPath(tab))}
        style={{ marginBottom: 0 }}
        className={styled.data_detail_tab}
      >
        <Tabs.TabPane
          title="计算任务"
          key={TrustedJobGroupTabType.COMPUTING}
          className={styled.data_detail_tab_pane}
        />
        <Tabs.TabPane
          title="导出任务"
          key={TrustedJobGroupTabType.EXPORT}
          className={styled.data_detail_tab_pane}
        />
      </Tabs>
      <div style={{ padding: '20px 20px 0' }}>
        {params.tabType === TrustedJobGroupTabType.COMPUTING && (
          <ComputingJobTab trustedJobGroup={trustedJobGroup!} />
        )}
        {params.tabType === TrustedJobGroupTabType.EXPORT && <ExportJobTab />}
      </div>
      <Modal
        title={t('trusted_center.title_initiate_trusted_job', { name: trustedJobGroup?.name })}
        visible={commentVisible}
        onOk={() => onCommentModalConfirm()}
        onCancel={() => {
          setCommentVisible(false);
          setComment('');
        }}
        autoFocus={false}
        focusLock={true}
      >
        <div className={styled.modal_label}>{t('trusted_center.label_trusted_job_comment')}</div>
        <Input.TextArea
          placeholder={t('trusted_center.placeholder_trusted_job_set_comment')}
          autoSize={{ minRows: 3 }}
          value={comment}
          onChange={setComment}
        />
      </Modal>
    </SharedPageLayout>
  );

  function getTabPath(tabType: string) {
    let path = `/trusted-center/detail/${params.id}/computing`;
    switch (tabType) {
      case TrustedJobGroupTabType.COMPUTING:
        path = `/trusted-center/detail/${params.id}/${TrustedJobGroupTabType.COMPUTING}`;
        break;
      case TrustedJobGroupTabType.EXPORT:
        path = `/trusted-center/detail/${params.id}/${TrustedJobGroupTabType.EXPORT}`;
        break;
      default:
        break;
    }
    return path;
  }

  function goBackToListPage() {
    history.push(routeMaps.TrustedJobGroupList);
  }

  function renderDatasetTooltip(record: TrustedJobGroup) {
    if (!record) {
      return CONSTANTS.EMPTY_PLACEHOLDER;
    }
    // without participant datasets
    if (record.participant_datasets.items?.length === 0) {
      return <WhichDataset.DatasetDetail id={record.dataset_id} />;
    }

    const hasMyDataset = record.dataset_id !== 0;
    let length = record.participant_datasets.items?.length || 0;
    if (hasMyDataset) {
      length += 1;
    }
    const datasets = record.participant_datasets.items!;
    const nameList = datasets.map((item) => {
      return item.name;
    });

    return (
      <div className={styled.display_dataset__tooltip}>
        {hasMyDataset ? (
          <WhichDataset.DatasetDetail id={record.dataset_id} />
        ) : (
          <div style={{ marginTop: '3px' }}>{nameList[0]}</div>
        )}
        {length > 1 ? (
          <Tooltip
            position="top"
            trigger="hover"
            color="#FFFFFF"
            content={nameList.map((item, index) => {
              if (!hasMyDataset && index === 0) return <></>;
              return (
                <>
                  <Tag style={{ marginTop: '5px' }} key={index}>
                    {item}
                  </Tag>
                  <br />
                </>
              );
            })}
          >
            <Tag>{`+${length - 1}`}</Tag>
          </Tooltip>
        ) : (
          <></>
        )}
      </div>
    );
  }

  async function onCommentModalConfirm() {
    const [res, error] = await to(
      launchTrustedJobGroup(projectId!, params.id, {
        comment: comment,
      }),
    );
    setCommentVisible(false);
    setComment('');
    if (error) {
      Message.error(error.message);
      return;
    }
    if (res.data) {
      const msg = '发布成功';
      Message.success(msg);
      return;
    }
  }
};

export default TrustedJobGroupDetail;
