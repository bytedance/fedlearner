import React, { ReactElement, useMemo, useState } from 'react';
import { useInterval } from 'react-use';
import { useHistory, useParams } from 'react-router-dom';
import {
  Message as message,
  Spin,
  Typography,
  Button,
  Tag,
  Space,
  Result,
  Message,
} from '@arco-design/web-react';

import { ResultProps } from '@arco-design/web-react/es/Result';
import { authorizePendingProject, fetchPendingProjectList } from 'services/project';
import { ProjectStateType } from 'typings/project';

import { useQuery } from 'react-query';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import ProjectName from '../ProjectName';

import { getCoordinateName, getParticipantsName } from '../shard';

import styles from './index.module.less';
import Modal from 'components/Modal';

function ResultPage({ status, title }: ResultProps): ReactElement {
  const history = useHistory();
  const [redirectCountdown, setRedirectCountdown] = useState<number>(5);

  useInterval(() => {
    if (redirectCountdown === 0) {
      history.push('/projects');
      return;
    }
    setRedirectCountdown(redirectCountdown - 1);
  }, 1000);

  return (
    <div className={styles.result_container}>
      <Result
        status={status}
        title={title}
        subTitle={`${redirectCountdown}s钟后自动回到首页`}
        extra={[
          <Button
            className={styles.btn_content}
            key="back"
            type="primary"
            onClick={() => {
              history.push('/projects?project_list_type=pending');
            }}
          >
            回到首页
          </Button>,
        ]}
      />
    </div>
  );
}

function ReceiverProject(): ReactElement {
  const history = useHistory();
  const { id } = useParams<{ id: string }>();
  const [pageShow, setPageShow] = useState({
    mainPage: true,
    okPage: false,
    rejectPage: false,
  });
  const [btnLoading, setBtnLoading] = useState({
    reject: false,
    ok: false,
  });
  const pendingProjectListQuery = useQuery(['fetchPendingProjectList'], () =>
    fetchPendingProjectList(),
  );
  const pendingProjectDetail = useMemo(() => {
    return pendingProjectListQuery.data?.data.find((item) => item.id.toString() === id);
  }, [pendingProjectListQuery, id]);

  return (
    <div className={styles.container}>
      <Spin className={styles.spin_container} loading={pendingProjectListQuery.isLoading}>
        <SharedPageLayout
          title={<BackButton onClick={() => history.goBack()}>工作区管理</BackButton>}
          centerTitle="工作区邀请"
        >
          {pageShow.mainPage && (
            <div className={styles.card_container}>
              <div className={styles.card_header} />
              <div className={styles.card_content_title}>
                <ProjectName text={pendingProjectDetail?.name ?? ''} />
                <Typography.Text
                  className={styles.card_content_comment}
                  type="secondary"
                  ellipsis={{
                    rows: 2,
                    showTooltip: true,
                  }}
                >
                  {pendingProjectDetail?.comment || '-'}
                </Typography.Text>
              </div>
              <div className={styles.card_content_participant}>
                <Space>
                  <Tag color="arcoblue">创建方</Tag>

                  <Tag>
                    {getCoordinateName(pendingProjectDetail?.participants_info.participants_map)}
                  </Tag>
                </Space>
                <div>
                  <Space align="start">
                    <Tag color="arcoblue">参与方</Tag>
                    <Space wrap>
                      {getParticipantsName(
                        pendingProjectDetail?.participants_info?.participants_map,
                      ).map((item) => (
                        <Tag key={item}>{item}</Tag>
                      ))}
                    </Space>
                  </Space>
                </div>
              </div>
              <div className={styles.card_footer}>
                <Space size={'medium'}>
                  <Button
                    loading={btnLoading.reject}
                    className={styles.btn_container}
                    onClick={onReject}
                  >
                    拒绝
                  </Button>
                  <Button
                    className={styles.btn_container}
                    loading={btnLoading.ok}
                    type="primary"
                    onClick={onOK}
                  >
                    通过
                  </Button>
                </Space>
              </div>
            </div>
          )}
          {pageShow.okPage && <ResultPage status="success" title="已通过邀请" />}
          {pageShow.rejectPage && <ResultPage status="error" title="已拒绝邀请" />}
        </SharedPageLayout>
      </Spin>
    </div>
  );
  async function onOK() {
    if (!pendingProjectDetail?.id) {
      return Message.error('找不到该工作区');
    }
    try {
      await authorizePendingProject(pendingProjectDetail?.id, { state: ProjectStateType.ACCEPTED });
      setBtnLoading({ ok: true, reject: false });
      setPageShow({ mainPage: false, okPage: true, rejectPage: false });
    } catch (error: any) {
      message.error(error.message);
    }
  }
  async function onReject() {
    if (!pendingProjectDetail?.id) {
      return Message.error('找不到该工作区');
    }
    Modal.reject({
      title: '拒绝申请？',
      content: '拒绝后无法撤销此操作。',
      async onOk() {
        try {
          await authorizePendingProject(pendingProjectDetail?.id!, {
            state: ProjectStateType.CLOSED,
          });
          setBtnLoading({ ok: false, reject: true });
          setPageShow({ mainPage: false, okPage: false, rejectPage: true });
        } catch (error: any) {
          message.error(error.message);
        }
      },
    });
  }
}

export default ReceiverProject;
