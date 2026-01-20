import { Left } from 'components/IconPark';
import React, { Dispatch, FC, SetStateAction, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Form,
  Grid,
  Message,
  Modal,
  Button,
  Input,
  Popover,
  Divider,
} from '@arco-design/web-react';
import MoreActions from 'components/MoreActions';
import { Edit } from 'components/IconPark';
import InvitionTable from 'components/InvitionTable';
import { Participant, ParticipantType } from 'typings/participant';
import { useQuery, UseQueryResult } from 'react-query';
import {
  deleteRevision,
  fetchRevisionList,
  patchRevisionComment,
  getTemplateRevisionDownloadHref,
} from 'services/workflow';
import { TemplateRevision, WorkflowTemplateMenuType } from 'typings/workflow';
import CONSTANTS from 'shared/constants';
import { ResponseInfo } from 'typings/app';
import { formatTimestamp } from 'shared/date';
import { saveBlob, to } from 'shared/helpers';
import request from 'libs/request';
import { sendTemplateRevision } from 'services/workflow';
import styled from './RevisionList.module.less';

const Row = Grid.Row;
const Col = Grid.Col;

const REVISION_QUERY_KEY = 'fetchRevisionList';

interface ListProps {
  id: string;
  collapsed: boolean;
  name?: string;
  ownerType?: WorkflowTemplateMenuType;
  setRevisionId: Dispatch<SetStateAction<number>>;
  setCollapsed: Dispatch<SetStateAction<boolean>>;
}

const RevisionList: FC<ListProps> = (props) => {
  const { t } = useTranslation();
  const [total, setTotal] = useState(0);
  const [choosen, setChoosen] = useState(0);
  const { id, name, collapsed, setRevisionId, setCollapsed, ownerType } = props;

  const listQuery = useQuery(
    [REVISION_QUERY_KEY, id],
    () => {
      return fetchRevisionList(id);
    },
    {
      retry: 1,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        if (res.data.length > 0) {
          setRevisionId(res.data[0].id);
        }
      },
    },
  );

  const list = useMemo(() => {
    if (!listQuery.data?.data) return [];
    if (listQuery.data?.page_meta?.total_items) {
      setTotal(listQuery.data.page_meta.total_items);
    }
    return listQuery.data.data;
  }, [listQuery.data]);

  useEffect(() => {
    if (list[choosen]) {
      setRevisionId(list[choosen].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [choosen]);

  return (
    <div
      className={styled.container}
      style={{
        width: collapsed ? '256px' : '0px',
      }}
    >
      {collapsed ? (
        <div className={styled.main}>
          <div className={styled.header}>
            <span className={styled.name}>{t('workflow.label_template_version')}</span>
            <span className={styled.number}>{`共${total}个`}</span>
          </div>
          <section className={styled.list_section}>
            {list.length === 0 ? (
              <div className={styled.empty}>{t('no_data')}</div>
            ) : (
              list.map((item, index) => {
                return (
                  <RevisionListItem
                    key={item.id}
                    params={item}
                    setChoosen={setChoosen}
                    name={name}
                    index={index}
                    choosen={choosen}
                    listQuery={listQuery}
                    ownerType={ownerType}
                  />
                );
              })
            )}
          </section>
        </div>
      ) : (
        <></>
      )}
      <div
        onClick={() => setCollapsed(!collapsed)}
        className={collapsed ? styled.collapse : styled.is_reverse}
      >
        <Left />
      </div>
    </div>
  );
};

interface ItemProps {
  params: TemplateRevision;
  index: number;
  choosen: number;
  name?: string;
  setChoosen: Dispatch<SetStateAction<number>>;
  listQuery: UseQueryResult<ResponseInfo<TemplateRevision[]>, unknown>;
  ownerType?: WorkflowTemplateMenuType;
}

export const RevisionListItem: FC<ItemProps> = (props) => {
  const { params, index, choosen, name, setChoosen, listQuery, ownerType } = props;
  const [form] = Form.useForm();
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const [sendModalVisible, setSendModalVisible] = useState(false);
  const [comment, setComment] = useState(params.comment);
  const [isSubmitDisable, setIsSubmitDisable] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const moreActionsList = useMemo(() => {
    const tempList = [
      {
        label: '下载',
        onClick: async () => {
          const { id, revision_index } = params;
          try {
            const blob = await request(getTemplateRevisionDownloadHref(id), {
              responseType: 'blob',
            });
            saveBlob(blob, `V${revision_index}-${name}.json`);
          } catch (error: any) {
            Message.error(error.message);
          }
        },
      },
      {
        label: '发送',
        onClick: () => {
          setSendModalVisible(true);
        },
      },
      {
        label: t('delete'),
        danger: true,
        onClick: () => {
          Modal.confirm({
            title: `确认删除V${params.revision_index || ''}吗?`,
            content: '删除后，该模板将无法进行操作，请谨慎删除',
            onOk() {
              deleteRevision(params.id)
                .then(() => {
                  Message.success('删除成功');
                  setChoosen(0);
                  listQuery.refetch();
                })
                .catch((error: any) => {
                  Message.error(
                    index === 0
                      ? '无法删除最新版本模板'
                      : '删除失败，该模板已关联工作流任务。如需删除，请前往工作流替换模板后再试',
                  );
                });
            },
          });
        },
      },
    ];
    ownerType === WorkflowTemplateMenuType.PARTICIPANT && tempList.splice(1, 1);
    return tempList;
  }, [ownerType, listQuery, name, t, setChoosen, params, index]);

  return (
    <div
      onClick={() => {
        setChoosen(index);
      }}
      style={{ background: choosen === index ? '#f2f3f8' : '' }}
      className={styled.item}
    >
      <Row>
        <Col className={styled.item_name} span={4}>{`V${params.revision_index}`}</Col>
        <Col className={styled.item_time} span={16}>
          {formatTimestamp(params.created_at!)}
        </Col>
        <Col span={4} style={{ textAlign: 'center' }}>
          <MoreActions actionList={moreActionsList} />
        </Col>
      </Row>
      <Row>
        <Col span={21}>
          <div className={styled.description}>{params.comment || CONSTANTS.EMPTY_PLACEHOLDER}</div>
        </Col>
        <Col span={3}>
          <Popover
            content={
              <>
                <Input
                  defaultValue={params.comment}
                  placeholder="请输入模板描述"
                  allowClear={true}
                  onChange={(value) => {
                    setComment(value);
                  }}
                />
                <Divider />
                <div className={styled.popover_bottom}>
                  <Button style={{ marginRight: '10px' }} onClick={() => setVisible(false)}>
                    取消
                  </Button>
                  <Button type="primary" onClick={onConfirm}>
                    {' '}
                    确定
                  </Button>
                </div>
              </>
            }
            title="编辑版本描述"
            trigger="click"
            popupVisible={visible}
          >
            <Button size="small" type="text" icon={<Edit />} onClick={() => setVisible(true)} />
          </Popover>
        </Col>
      </Row>
      <Modal
        title="发送至合作伙伴"
        visible={sendModalVisible}
        onOk={onOk}
        confirmLoading={isLoading}
        onCancel={() => setSendModalVisible(false)}
        okButtonProps={{ disabled: isSubmitDisable }}
        unmountOnExit={true}
        style={{ minWidth: '700px' }}
      >
        <Form form={form}>
          <Form.Item label="模版名称">
            <span>{name}</span>
          </Form.Item>
          <Form.Item label="模版版本">
            <span>{`V${params.revision_index}`}</span>
          </Form.Item>
          <Form.Item
            label="合作伙伴"
            field="participant_ids"
            normalize={(value) => value?.map((item: any) => item.id)}
          >
            <InvitionTable
              participantsType={ParticipantType.PLATFORM}
              isSupportCheckbox={false}
              onChange={(selectedParticipants: Participant[]) => {
                setIsSubmitDisable(!selectedParticipants.length);
              }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );

  async function onConfirm() {
    await to(patchRevisionComment(params.id, { comment }));
    setVisible(false);
    listQuery.refetch();
  }
  async function onOk() {
    const participant_id = form.getFieldValue('participant_ids')?.[0];
    try {
      setIsLoading(true);
      await sendTemplateRevision(params.id, participant_id);
      Message.success('发送成功!');
      setSendModalVisible(false);
    } catch (error: any) {
      Message.error(error.message);
    }
    setIsLoading(false);
  }
};

export default RevisionList;
