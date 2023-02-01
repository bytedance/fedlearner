import React, { useState } from 'react';
import { Form, Grid, Popover, Select, Typography } from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import TitleWithIcon from 'components/TitleWithIcon';
import { ProjectAbilityType, ProjectActionType, ProjectTaskType } from 'typings/project';

import styles from './index.module.less';

const { Row, Col } = Grid;
const { Option } = Select;

const options = [
  {
    value: ProjectAbilityType.ALWAYS_ALLOW,
    label: '始终允许',
  },
  {
    value: ProjectAbilityType.ONCE,
    label: '允许一次',
  },
  {
    value: ProjectAbilityType.MANUAL,
    label: '发起时询问',
  },
  {
    value: ProjectAbilityType.ALWAYS_REFUSE,
    label: '拒绝',
  },
];

interface Props {
  taskType: ProjectTaskType;
  value?: any;
}
function ActionRules({ taskType, value }: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <div className={styles.title_container}>
        <p className={styles.title_content}>本方授权策略</p>
        <TitleWithIcon
          title={
            <>
              <span>配置任务时修改其授权策略，此初始授权策略将不再对任务生效。 </span>
              <Popover
                title="选项说明"
                popupVisible={visible}
                onVisibleChange={setVisible}
                content={
                  <span className={styles.popover_content}>
                    <p>1.始终允许：同类任务始终允许自动授权通过；</p>

                    <p>
                      2.允许一次：同类任务允许一次自动授权通过；一次执行后，具体任务的权限更新为发起时询问；
                    </p>
                    <p>3.发起时询问：同类任务发起时需要询问是否授权通过；</p>
                    <p>4.拒绝授权：同类任务始终授权拒绝。</p>
                  </span>
                }
              >
                <Typography.Text type="primary">选项说明</Typography.Text>
              </Popover>
            </>
          }
          isLeftIcon={true}
          isShowIcon={true}
          icon={IconInfoCircle}
        />
      </div>
      {renderFormItem(taskType)}
    </>
  );
}

function resetFiled(filedValue: string) {
  return `config.action_rules.${filedValue}`;
}
function renderFormItem(taskType: ProjectTaskType) {
  let formItem;
  switch (taskType) {
    case ProjectTaskType.ALIGN:
      formItem = renderAlignTask();
      break;
    case ProjectTaskType.HORIZONTAL:
      formItem = renderHorizontalTask();
      break;
    case ProjectTaskType.VERTICAL:
      formItem = renderVerticalTask();
      break;
    case ProjectTaskType.TRUSTED:
      formItem = renderTrustedTask();
      break;
    default:
      formItem = renderAlignTask();
      break;
  }
  return formItem;
}
function renderAlignTask() {
  return (
    <Form.Item
      field={resetFiled(ProjectActionType.ID_ALIGNMENT)}
      label="ID对齐任务"
      rules={[{ required: true }]}
    >
      {taskAuthorization()}
    </Form.Item>
  );
}
function renderHorizontalTask() {
  return (
    <>
      <Row gutter={24}>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.DATA_ALIGNMENT)}
            label="横向数据对齐任务"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.HORIZONTAL_TRAIN)}
            label="横向联邦模型训练"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={24}>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.WORKFLOW)}
            label="工作流任务"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
      </Row>
    </>
  );
}
function renderVerticalTask() {
  return (
    <>
      <Row gutter={24}>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.ID_ALIGNMENT)}
            label="ID对齐任务"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.VERTICAL_TRAIN)}
            label="纵向联邦模型训练"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={24}>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.VERTICAL_EVAL)}
            label="纵向联邦模型评估"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.VERTICAL_PRED)}
            label="纵向联邦模型离线预测"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={24}>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.VERTICAL_SERVING)}
            label="纵向联邦模型在线服务"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            field={resetFiled(ProjectActionType.WORKFLOW)}
            label="工作流任务"
            rules={[{ required: true }]}
          >
            {taskAuthorization()}
          </Form.Item>
        </Col>
      </Row>
    </>
  );
}
function renderTrustedTask() {
  return (
    <Row gutter={24}>
      <Col span={12}>
        <Form.Item
          field={resetFiled(ProjectActionType.TEE_SERVICE)}
          label="可信分析服务"
          rules={[{ required: true }]}
        >
          {taskAuthorization()}
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item
          field={resetFiled(ProjectActionType.TEE_RESULT_EXPORT)}
          label="可信分析服务结果导出"
          rules={[{ required: true }]}
        >
          {taskAuthorization()}
        </Form.Item>
      </Col>
    </Row>
  );
}
function taskAuthorization() {
  return (
    <Select options={options}>
      {options.map((option) => (
        <Option value={option.value} key={option.value}>
          {option.label}
        </Option>
      ))}
    </Select>
  );
}
export default ActionRules;
