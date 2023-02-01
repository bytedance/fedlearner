import React, { FC, useState, useEffect } from 'react';
import { useHistory } from 'react-router';
import { NewCreateProjectPayload, ProjectTaskType } from 'typings/project';
import { ParticipantType, Participant } from 'typings/participant';
import { useRecoilState } from 'recoil';
import { initialActionRules, projectCreateForm, ProjectCreateForm } from 'stores/project';
import { Button, Form, Popover, Switch, Space } from '@arco-design/web-react';
import { IconInfoCircle, IconQuestionCircle } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import InvitionTable from 'components/InvitionTable';
import BlockRadio from 'components/_base/BlockRadio';
import TitleWithIcon from 'components/TitleWithIcon';

import styles from './index.module.less';

const options = [
  {
    value: ParticipantType.PLATFORM,
    label: '标准合作伙伴',
  },
  {
    value: ParticipantType.LIGHT_CLIENT,
    label: '轻量合作伙伴',
  },
];

const StepThreeAuthorize: FC<{ onSubmit: (payload: NewCreateProjectPayload) => Promise<void> }> = ({
  onSubmit,
}) => {
  const history = useHistory();
  const [form] = Form.useForm();
  const [projectForm, setProjectForm] = useRecoilState<ProjectCreateForm>(projectCreateForm);
  const [isSubmitDisable, setIsSubmitDisable] = useState(true);
  const [supportBlockChain, setSupportBlockChain] = useState(true);
  const [participantsType, setParticipantsType] = useState(ParticipantType.PLATFORM);

  useEffect(() => {
    if (!projectForm.config.abilities || !projectForm.name) {
      history.push('/projects/create/config');
    }
  });
  return (
    <div className={styles.container}>
      <div>
        <Form form={form} initialValues={projectForm} onSubmit={onFinish} layout="vertical">
          <p className={styles.title_content}>邀请合作伙伴</p>
          <Form.Item
            label={
              <span>
                合作伙伴类型
                <Popover
                  title="合作伙伴类型说明"
                  content={
                    <span className={styles.popover_content}>
                      <p>标准合作伙伴：拥有可视化Web平台的合作伙伴；</p>
                      <p>轻量合作伙伴：合作伙伴的客户端形式为容器或可执行文本。</p>
                    </span>
                  }
                >
                  <IconQuestionCircle />
                </Popover>
              </span>
            }
            field="participant_type"
            initialValue={ParticipantType.PLATFORM}
            rules={[{ required: true }]}
          >
            <BlockRadio
              options={options}
              onChange={(value: any) => {
                setParticipantsType(value);
              }}
            />
          </Form.Item>
          <Form.Item label="合作伙伴" field="participant_ids">
            <InvitionTable
              participantsType={participantsType}
              onChange={(selectedParticipants: Participant[]) => {
                setIsSubmitDisable(!selectedParticipants.length);
                const hasNoBlockChain = selectedParticipants.find((item) => {
                  return !item?.support_blockchain;
                });
                setSupportBlockChain(!hasNoBlockChain);
                hasNoBlockChain && form.setFieldValue('config.support_blockchain', false);
              }}
              isSupportCheckbox={[ProjectTaskType.HORIZONTAL, ProjectTaskType.TRUSTED].includes(
                projectForm?.config?.abilities?.[0],
              )}
            />
          </Form.Item>
          <p className={styles.title_content}>区块链存证</p>
          <Space>
            <Form.Item
              className={styles.block_chain_container}
              field="config.support_blockchain"
              initialValue={true}
            >
              {supportBlockChain ? (
                <Switch />
              ) : (
                <TitleWithIcon
                  title="你选择的部分合作伙伴无区块链服务，不可启用区块链存证"
                  isLeftIcon={true}
                  isShowIcon={true}
                  icon={IconInfoCircle}
                />
              )}
            </Form.Item>
            {supportBlockChain && (
              <TitleWithIcon
                title="在工作区创建提交后不可更改此设置"
                isLeftIcon={true}
                isShowIcon={true}
                icon={IconInfoCircle}
              />
            )}
          </Space>

          <Form.Item>
            <GridRow className={styles.btn_container} gap={10} justify="center">
              <Button
                className={styles.btn_content}
                type="primary"
                htmlType="submit"
                disabled={isSubmitDisable}
              >
                提交并发送
              </Button>
              <Button onClick={goToStepTwo}>上一步</Button>
            </GridRow>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
  function onFinish(value: any) {
    onSubmit({
      ...projectForm,
      participant_ids: value.participant_ids.map((item: any) => item.id) || [],
      config: {
        ...projectForm.config,
        ...value.config,
      },
    });
  }
  function goToStepTwo() {
    setProjectForm({
      ...projectForm,
      config: {
        ...projectForm.config,
        action_rules: {
          ...initialActionRules,
          ...projectForm.config.action_rules,
        },
      },
    });
    history.goBack();
  }
};

export default StepThreeAuthorize;
