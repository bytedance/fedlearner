import { Input, Grid, Switch, Tabs, Form } from '@arco-design/web-react';
import Modal from 'components/Modal';
import errorIcon from 'assets/icons/workflow-error.svg';
import BlockRadio from 'components/_base/BlockRadio';
import { useSubscribe } from 'hooks';
import { omit } from 'lodash-es';
import PubSub from 'pubsub-js';
import React, { FC, useContext, useEffect, useState } from 'react';
import { nextTick } from 'shared/helpers';
import { isValidJobName } from 'shared/validator';
import styled from './index.module.less';
import { ValidateErrorEntity } from 'typings/component';
import { JobType } from 'typings/job';
import { definitionsStore } from 'views/WorkflowTemplates/TemplateForm/stores';
import {
  ComposeDrawerContext,
  COMPOSE_DRAWER_CHANNELS,
  HighlightPayload,
  InspectPayload,
} from '..';
import SlotEntryList from '../SloEntrytList';
import VariableList from '../VariableList';

const Row = Grid.Row;

type Props = {
  isGlobal: boolean;
  isCheck?: boolean;
  onJobTypeChange: (type: JobType) => void;
};

const jobTypeOptions = Object.values(omit(JobType, 'UNSPECIFIED')).map((item) => ({
  value: item,
  label: item,
}));

export enum Perspective {
  Slots = 'slots',
  Variables = 'variables',
}

const DefaultMode: FC<Props> = ({ isGlobal, isCheck, onJobTypeChange }) => {
  const [perspective, setPerspective] = useState<Perspective>(
    isGlobal ? Perspective.Variables : Perspective.Slots,
  );
  const [errorTabs, setErrorTabs] = useState({
    slots: false,
    variables: false,
  });

  const context = useContext(ComposeDrawerContext);

  const jobNameRules = [
    { required: true, message: '请输入 Job 名' },
    {
      validator(value: any, callback: (error?: string) => void) {
        if (!isValidJobName(value)) {
          callback('只支持小写字母，数字开头或结尾，可包含“-”，不超过 24 个字符');
        }
      },
    },
    {
      validator(value: any, callback: (error?: string) => void) {
        if (
          definitionsStore.entries
            .filter(([uuid]) => uuid !== context.uuid)
            .some(([_, jobDef]) => jobDef.name && jobDef.name === value.trim())
        ) {
          callback('检测到任务重名');
        }
      },
    },
  ];
  // ============ Subscribers ================
  useSubscribe(COMPOSE_DRAWER_CHANNELS.broadcast_error, (_: any, errInfo: ValidateErrorEntity) => {
    const errors = {
      slots: false,
      variables: false,
    };
    errors.slots = errInfo.errorFields.some((field) => /_slotEntries/.test(field.name[0]));
    errors.variables = errInfo.errorFields.some((field) => /variables/.test(field.name[0]));
    setErrorTabs(errors);
  });
  useSubscribe(COMPOSE_DRAWER_CHANNELS.validation_passed, () =>
    setErrorTabs({ slots: false, variables: false }),
  );
  useSubscribe(
    COMPOSE_DRAWER_CHANNELS.inspect,
    (_: string, { perspective, slotName, varUuid }: InspectPayload) => {
      if (perspective) {
        setPerspective(perspective);
      }

      if (slotName || varUuid) {
        if (slotName) {
          setPerspective(Perspective.Slots);
        } else {
          setPerspective(Perspective.Variables);
        }
        nextTick(() => {
          PubSub.publish(COMPOSE_DRAWER_CHANNELS.highlight, {
            slotName,
            varUuid,
          } as HighlightPayload);
        });
      }
    },
  );
  // ============ Subscribers ================

  useEffect(() => {
    setErrorTabs({ slots: false, variables: false });
  }, [context.uuid]);

  useEffect(() => {
    if (isGlobal) {
      setPerspective(Perspective.Variables);
    }
  }, [isGlobal]);

  return (
    <>
      {!isGlobal && (
        <section className={styled.form_section} style={{ width: 620 }}>
          <h4 className={styled.section_heading}>基础配置</h4>

          <Form.Item field="name" label="Job 名称" rules={jobNameRules}>
            <Input disabled={isCheck} placeholder="请输入 Job 名" />
          </Form.Item>

          <Form.Item field="is_federated" label="是否联邦" triggerPropName="checked">
            <Switch disabled={isCheck} />
          </Form.Item>

          <h4 className={styled.section_heading}>任务类型</h4>
          <Form.Item
            labelCol={{ span: 0 }}
            field="job_type"
            label="任务类型"
            rules={[{ required: true, message: '请输入 Job 名' }]}
          >
            <BlockRadio
              disabled={isCheck}
              gap={10}
              flexGrow={0}
              options={jobTypeOptions}
              beforeChange={beforeTypeChange}
              onChange={onJobTypeChange}
            />
          </Form.Item>
        </section>
      )}

      <section className={styled.form_section} data-fill-width>
        {!isGlobal && (
          <>
            <Row className={styled.section_heading} justify="space-between">
              <Tabs activeTab={perspective} onChange={onPerspectiveChange}>
                <Tabs.TabPane
                  key={Perspective.Slots}
                  title={
                    <div className={styled.perspective_tab} data-has-error={errorTabs.slots}>
                      <img className={styled.has_error_icon} src={errorIcon} alt="error-icon" />
                      插槽赋值
                    </div>
                  }
                />

                <Tabs.TabPane
                  key={Perspective.Variables}
                  title={
                    <div className={styled.perspective_tab} data-has-error={errorTabs.variables}>
                      <img className={styled.has_error_icon} src={errorIcon} alt="error-icon" />
                      自定义变量
                    </div>
                  }
                />
              </Tabs>
            </Row>
          </>
        )}
        <div
          className={styled.perspective_container}
          data-hidden={perspective !== Perspective.Variables}
        >
          <VariableList isCheck={isCheck} />
        </div>

        <div
          className={styled.perspective_container}
          data-hidden={perspective !== Perspective.Slots}
        >
          <SlotEntryList isCheck={isCheck} />
        </div>
      </section>
    </>
  );

  function onPerspectiveChange(val: string) {
    setPerspective(val as Perspective);
  }
  function beforeTypeChange(): Promise<boolean> {
    return new Promise((resolve) => {
      Modal.confirm({
        title: '确认变更任务类型',
        content: '更改任务类型将会使当前配置的插槽值将会丢失，确认这样做吗？',
        onOk() {
          resolve(true);
        },
        onCancel() {
          resolve(false);
        },
      });
    });
  }
};

export default DefaultMode;
