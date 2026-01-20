import React, { useEffect } from 'react';
import { useHistory } from 'react-router';
import { useGetCurrentProjectParticipantList } from 'hooks';
import { AlgorithmProject, EnumAlgorithmProjectType } from 'typings/algorithm';
import { ModelJobGroup, ResourceTemplateType, TrainRoleType } from 'typings/modelCenter';
import {
  isNNAlgorithm,
  isTreeAlgorithm,
  nnBaseConfigList,
  treeBaseConfigList,
} from 'views/ModelCenter/shared';
import { Button, Checkbox, Form, Space, Tooltip, Typography } from '@arco-design/web-react';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import ConfigForm, { ItemProps } from 'components/ConfigForm';
import ResourceConfig, { MixedAlgorithmType } from 'components/ResourceConfig';
import AlgorithmProjectSelect from '../../CreateCentralization/AlgorithmProjectSelect';
import AlgorithmVersionSelect from '../AlgorithmVersionSelect';
import { IconQuestionCircle } from '@arco-design/web-react/icon';

type Props = {
  modelGroup?: ModelJobGroup;
  stepOneFormConfigValues?: Record<string, any>;
  formInitialValues?: Record<string, any>;
  isFormValueChanged?: boolean;
  onFormValueChange?: (...args: any[]) => void;
  onSecondStepSubmit?: (value: any) => void;
  saveStepTwoValues?: (formInfo: Record<string, any>) => void;
  treeAdvancedFormItemList?: ItemProps[];
  nnAdvancedFormItemList?: ItemProps[];
  algorithmProjectList?: AlgorithmProject[];
  peerAlgorithmProjectList?: AlgorithmProject[];
  submitLoading?: boolean;
};

export default function StepTwoParticipant({
  modelGroup,
  formInitialValues,
  isFormValueChanged,
  onFormValueChange,
  onSecondStepSubmit,
  saveStepTwoValues,
  stepOneFormConfigValues,
  nnAdvancedFormItemList,
  treeAdvancedFormItemList,
  algorithmProjectList,
  peerAlgorithmProjectList,
  submitLoading,
}: Props) {
  const history = useHistory();
  const [formInstance] = Form.useForm();
  const participantList = useGetCurrentProjectParticipantList();

  useEffect(() => {
    if (!stepOneFormConfigValues) {
      history.goBack();
    }
  }, [stepOneFormConfigValues, history]);

  useEffect(() => {
    if (!formInitialValues) {
      return;
    }
    participantList.forEach((participant) => {
      formInstance.setFieldValue(
        resetFiled(participant.pure_domain_name, 'algorithmProjectUuid'),
        formInitialValues?.[participant.pure_domain_name].algorithmProjectUuid,
      );
      formInstance.setFieldValue(
        resetFiled(participant.pure_domain_name, 'nn_config'),
        formInitialValues?.[participant.pure_domain_name].nn_config,
      );
      formInstance.setFieldValue(
        resetFiled(participant.pure_domain_name, 'tree_config'),
        formInitialValues?.[participant.pure_domain_name].tree_config,
      );
    });
  }, [formInitialValues, formInstance, participantList]);
  useEffect(() => {
    if (!formInitialValues) {
      return;
    }
    participantList.forEach((participant) => {
      if (formInitialValues?.[participant.pure_domain_name].resource_config) {
        formInstance.setFieldValue(
          resetFiled(participant.pure_domain_name, 'resource_config'),
          formInitialValues?.[participant.pure_domain_name].resource_config,
        );
      }
    });
  }, [formInitialValues, formInstance, participantList]);
  return (
    <Form
      className="form-content"
      form={formInstance}
      scrollToFirstError={true}
      initialValues={formInitialValues}
      onValuesChange={onFormValueChange}
      onSubmit={onSecondStepSubmit}
    >
      {modelGroup?.algorithm_type === EnumAlgorithmProjectType.NN_HORIZONTAL ? (
        <>
          {participantList.map((participant) => {
            return (
              <section key={participant.id} className="form-section">
                <h3>{participant.pure_domain_name}配置</h3>
                <Form.Item
                  label={'算法'}
                  field={resetFiled(participant.pure_domain_name, 'algorithmProjectUuid')}
                >
                  <AlgorithmProjectSelect
                    algorithmType={[modelGroup?.algorithm_type as EnumAlgorithmProjectType]}
                    supportEdit={false}
                  />
                </Form.Item>
                <Form.Item
                  label={'算法版本'}
                  field={`${participant.pure_domain_name}.algorithm`}
                  rules={[{ required: true, message: '必填项' }]}
                >
                  <AlgorithmVersionSelect
                    algorithmProjectList={algorithmProjectList || []}
                    peerAlgorithmProjectList={peerAlgorithmProjectList || []}
                    algorithmProjectUuid={formInstance.getFieldValue(
                      resetFiled(participant.pure_domain_name, 'algorithmProjectUuid'),
                    )}
                  />
                </Form.Item>
                <Form.Item
                  field={resetFiled(participant.pure_domain_name, 'nn_config')}
                  label={'参数配置'}
                  rules={[{ required: true, message: '必填项' }]}
                >
                  <ConfigForm
                    cols={2}
                    formItemList={nnBaseConfigList}
                    collapseFormItemList={nnAdvancedFormItemList}
                    isResetOnFormItemListChange={true}
                  />
                </Form.Item>
                <Form.Item
                  field={resetFiled(participant.pure_domain_name, 'resource_config')}
                  label={'资源模版'}
                  rules={[{ required: true, message: '必填项' }]}
                >
                  <ResourceConfig
                    algorithmType={modelGroup?.algorithm_type as MixedAlgorithmType}
                    defaultResourceType={ResourceTemplateType.CUSTOM}
                    isIgnoreFirstRender={false}
                    localDisabledList={['master.replicas']}
                    collapsedOpen={false}
                  />
                </Form.Item>
              </section>
            );
          })}
        </>
      ) : (
        <>
          {participantList.map((participant) => {
            return (
              <div key={participant.id}>
                <section className="form-section">
                  <h3>{participant.name}训练配置</h3>

                  {isTreeAlgorithm(modelGroup?.algorithm_type as EnumAlgorithmProjectType) && (
                    <>
                      <Form.Item label={'损失函数类型'}>
                        <Typography.Text bold={true}>
                          {stepOneFormConfigValues?.loss_type}
                        </Typography.Text>
                      </Form.Item>

                      <Form.Item
                        field={resetFiled(participant.pure_domain_name, 'tree_config')}
                        label={'参数配置'}
                        rules={[{ required: true, message: '必须填写参数配置' }]}
                      >
                        <ConfigForm
                          cols={2}
                          isResetOnFormItemListChange={true}
                          formItemList={treeBaseConfigList}
                          collapseFormItemList={treeAdvancedFormItemList}
                          formProps={{
                            style: {
                              marginTop: 7,
                            },
                          }}
                        />
                      </Form.Item>
                    </>
                  )}
                  {isNNAlgorithm(modelGroup?.algorithm_type as EnumAlgorithmProjectType) && (
                    <>
                      <Form.Item
                        label={'算法'}
                        field={resetFiled(participant.pure_domain_name, 'algorithmProjectUuid')}
                      >
                        <AlgorithmProjectSelect
                          algorithmType={[modelGroup?.algorithm_type as EnumAlgorithmProjectType]}
                          supportEdit={false}
                        />
                      </Form.Item>
                      <Form.Item
                        label={'算法版本'}
                        field={`${participant.pure_domain_name}.algorithm`}
                        rules={[{ required: true, message: '必填项' }]}
                      >
                        <AlgorithmVersionSelect
                          algorithmProjectList={algorithmProjectList || []}
                          peerAlgorithmProjectList={peerAlgorithmProjectList || []}
                          algorithmProjectUuid={formInstance.getFieldValue(
                            resetFiled(participant.pure_domain_name, 'algorithmProjectUuid'),
                          )}
                        />
                      </Form.Item>

                      <Form.Item
                        field={resetFiled(participant.pure_domain_name, 'nn_config')}
                        label={'参数配置'}
                        rules={[{ required: true, message: '必填项' }]}
                      >
                        <ConfigForm
                          cols={2}
                          formItemList={nnBaseConfigList}
                          collapseFormItemList={nnAdvancedFormItemList}
                          isResetOnFormItemListChange={true}
                        />
                      </Form.Item>
                    </>
                  )}
                  <Form.Item label={'训练角色'}>
                    <Typography.Text bold={true}>
                      {stepOneFormConfigValues?.role === TrainRoleType.LABEL ? '特征方' : '标签方'}
                    </Typography.Text>
                  </Form.Item>
                </section>
                <section className="form-section">
                  <h3>{participant.name}资源配置</h3>
                  <Form.Item
                    field={resetFiled(participant.pure_domain_name, 'resource_config')}
                    label={'资源模版'}
                    rules={[{ required: true, message: '必填项' }]}
                  >
                    <ResourceConfig
                      algorithmType={modelGroup?.algorithm_type as MixedAlgorithmType}
                      defaultResourceType={ResourceTemplateType.CUSTOM}
                      isIgnoreFirstRender={false}
                      localDisabledList={['master.replicas']}
                    />
                  </Form.Item>
                </section>
              </div>
            );
          })}
        </>
      )}
      <Space align="center">
        <Button loading={submitLoading} type="primary" htmlType="submit">
          提交
        </Button>
        <ButtonWithModalConfirm
          isShowConfirmModal={false}
          onClick={() => {
            saveStepTwoValues?.(formInstance.getFields());
            history.goBack();
          }}
        >
          上一步
        </ButtonWithModalConfirm>
        <Form.Item field="metric_is_public" triggerPropName="checked" style={{ marginBottom: 0 }}>
          <Checkbox style={{ width: 200, fontSize: 12 }}>
            共享训练指标
            <Tooltip content="共享后，合作伙伴能够查看本方训练指标">
              <IconQuestionCircle />
            </Tooltip>
          </Checkbox>
        </Form.Item>
      </Space>
    </Form>
  );

  function resetFiled(participantName: string, filedName: string) {
    return `${participantName}.${filedName}`;
  }
}
