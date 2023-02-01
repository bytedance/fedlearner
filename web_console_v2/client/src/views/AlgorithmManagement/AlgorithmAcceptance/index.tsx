import React, { FC, useState } from 'react';
import styled from './index.module.less';
import { useParams, useHistory } from 'react-router';
import { useQuery, useMutation } from 'react-query';
import {
  Typography,
  Divider,
  Form,
  Input,
  Button,
  Space,
  Result,
  Drawer,
  RulesProps,
  Message,
} from '@arco-design/web-react';
import { useRecoilValue } from 'recoil';
import BackButton from 'components/BackButton';
import {
  postAcceptAlgorithm,
  fetchProjectPendingList,
  fetchProjectDetail,
} from 'services/algorithm';
import { projectState } from 'stores/project';
import SharedPageLayout from 'components/SharedPageLayout';
import { AlgorithmManagementTabType } from 'typings/modelCenter';
import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';
import { useInterval } from 'hooks';
import AlgorithmType from 'components/AlgorithmType';
import AlgorithmInfo from 'components/AlgorithmDrawer/AlgorithmInfo';
import { Avatar } from '../shared';

enum FormField {
  NAME = 'name',
  COMMENT = 'comment',
}

const rules: Record<string, RulesProps[]> = {
  [FormField.NAME]: [
    { required: true, message: '算法名称不能为空' },
    {
      match: validNamePattern,
      message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
    },
  ],
  [FormField.COMMENT]: [
    {
      maxLength: MAX_COMMENT_LENGTH,
      message: '最多为 200 个字符',
    },
  ],
};

type TMutationParams = {
  projId: ID;
  id: ID;
  payload: {
    name: string;
    comment?: string;
  };
};

const REDIRECT_COUNTDOWN_DURATION = 3;
const AlgorithmAcceptance: FC = () => {
  const [form] = Form.useForm();
  const selectedProject = useRecoilValue(projectState);
  const { id } = useParams<{ id: string }>();
  const history = useHistory();
  const [successful, setSuccessful] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [redirectCountdown, setRedirectCountdown] = useState(REDIRECT_COUNTDOWN_DURATION);
  const query = useQuery(
    ['algorithm_acceptance', id, selectedProject.current?.id],
    () => {
      return fetchProjectPendingList(selectedProject.current?.id).then((res) => {
        const algorithm = res.data.find((item) => item.id.toString() === id);
        if (!algorithm) {
          throw new Error('算法不存在');
        }
        return algorithm;
      });
    },
    {
      refetchOnWindowFocus: false,
      retry: 1,
      onSuccess(res) {
        form.setFieldsValue(res);
      },
      onError(e: any) {
        Message.error(e.message);
      },
    },
  );

  // Get algorithm project name
  useQuery(
    ['fetch_algorithm_project_detail', query?.data?.algorithm_project_id],
    () => {
      return fetchProjectDetail(query!.data!.algorithm_project_id!);
    },
    {
      enabled: Boolean(query?.data?.algorithm_project_id),
      onSuccess(res) {
        if (res?.data?.name) {
          form.setFieldsValue({
            name: res.data.name,
          });
        }
      },
    },
  );

  const accept = useMutation(
    ({ projId, id, payload }: TMutationParams) => {
      return postAcceptAlgorithm(projId, id, payload);
    },
    {
      onSuccess() {
        setSuccessful(true);
      },
      onError(e: any) {
        if (e.code === 409 || /already\s*exist/.test(e.message)) {
          Message.error('算法名称已存在');
        }
      },
    },
  );
  const detail = query.data;
  const layoutTitle = <BackButton onClick={goBackMyAlgorithmList}>{'算法仓库'}</BackButton>;

  useInterval(
    () => {
      if (redirectCountdown === 0) {
        goBackMyAlgorithmList();
        return;
      }
      setRedirectCountdown(redirectCountdown - 1);
    },
    successful ? 1000 : undefined,
    {
      immediate: false,
    },
  );

  if (successful) {
    return (
      <SharedPageLayout title={layoutTitle}>
        <Result
          className={styled.styled_result}
          status={null}
          icon={<i className={styled.styled_success_icon} />}
          title={`已同意并保存『${form.getFieldValue('name')}-V${detail?.version}』`}
          subTitle={`${redirectCountdown}S 后自动前往算法列表`}
          extra={[
            <Button key="back" type="primary" onClick={goBackMyAlgorithmList}>
              {'前往算法列表'}
            </Button>,
          ]}
        />
      </SharedPageLayout>
    );
  }

  return (
    <SharedPageLayout title={layoutTitle}>
      <div className={styled.styled_container}>
        <header className={styled.styled_header}>
          <Avatar />
          <br />
          <Typography.Text type="secondary">{detail?.comment}</Typography.Text>
        </header>
        <Divider />
        <Form form={form} labelCol={{ span: 5 }} onSubmit={acceptAlgorithm}>
          <Form.Item
            label={'名称'}
            field="name"
            rules={rules[FormField.NAME]}
            disabled={Boolean(detail?.algorithm_project_id)}
          >
            <Input placeholder={'请输入算法名称'} />
          </Form.Item>
          <Form.Item label={'描述'} field="comment" rules={rules[FormField.COMMENT]}>
            <Input.TextArea rows={2} placeholder={'最多为 200 个字符'} />
          </Form.Item>
          <Form.Item label={'类型'}>
            {detail?.type && <AlgorithmType type={detail.type} />}
          </Form.Item>
          <Form.Item label={'版本'}>
            <div className={styled.styled_form_text}>V{detail?.version}</div>
          </Form.Item>
          <Form.Item label={'算法'}>
            <button
              type="button"
              className="custom-text-button"
              onClick={() => setPreviewVisible(true)}
            >
              {'查看算法配置'}
            </button>
          </Form.Item>
          <div className={styled.styled_form_footer}>
            <Space>
              <Button
                className={styled.styled_form_footer_button}
                type="primary"
                htmlType="submit"
                loading={accept.isLoading}
              >
                {'同意并保存'}
              </Button>
              <Button className={styled.styled_form_footer_button} onClick={goBackMyAlgorithmList}>
                {'取消'}
              </Button>
            </Space>
          </div>
        </Form>
      </div>
      <Drawer
        closable
        onCancel={() => setPreviewVisible(false)}
        width={1000}
        visible={previewVisible}
        title={`算法版本 V${detail?.version}`}
      >
        <AlgorithmInfo type="pending_algorithm" detail={detail} />
      </Drawer>
    </SharedPageLayout>
  );

  async function acceptAlgorithm(formValues: any) {
    if (selectedProject.current?.id) {
      accept.mutate({
        projId: selectedProject.current.id,
        id: detail?.id!,
        payload: {
          name: formValues.name as string,
          comment: formValues.comment as string,
        },
      });
    }
  }

  function goBackMyAlgorithmList() {
    history.replace(`/algorithm-management/${AlgorithmManagementTabType.MY}`);
  }
};

export default AlgorithmAcceptance;
