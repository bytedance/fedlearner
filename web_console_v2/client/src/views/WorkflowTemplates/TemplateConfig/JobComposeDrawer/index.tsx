/* eslint-disable react-hooks/exhaustive-deps */
import {
  Button,
  Spin,
  Tooltip,
  Message,
  Grid,
  Switch,
  Popconfirm,
  Drawer,
  Form,
  FormInstance,
} from '@arco-design/web-react';
import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import Modal from 'components/Modal';
import { IconClose, IconLeft, IconDelete, IconSwap } from '@arco-design/web-react/icon';
import { ChartNode } from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import { useSubscribe } from 'hooks';
import jobTypeToMetaDatasMap from 'jobMetaDatas';
import PubSub from 'pubsub-js';
import React, {
  forwardRef,
  ForwardRefRenderFunction,
  useCallback,
  useEffect,
  useImperativeHandle,
  useState,
} from 'react';
import { useToggle } from 'react-use';
import styled from './index.module.less';
import { ValidateErrorEntity } from 'typings/component';
import { JobType } from 'typings/job';
import {
  DEFAULT_JOB,
  definitionsStore,
  editorInfosStore,
  JobDefinitionForm,
  SlotEntries,
  IS_DEFAULT_EASY_MODE,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import DefaultMode, { Perspective } from './DefaultMode';
import ExpertMode from './ExpertMode';
import { FieldError } from '@arco-design/web-react/es/Form/interface';

const Row = Grid.Row;

interface Props extends DrawerProps {
  /** Is workflow global node */
  isGlobal: boolean;
  isCheck?: boolean;
  revisionId?: number;
  uuid?: string;
  prevNode?: ChartNode;
  onClose?: any;
  onSubmit?: any;
  onDelete?: any;
  onBack: () => void;
  toggleVisible?: any;
}

export type ExposedRef = {
  validate(): Promise<boolean>;
  getFormValues(): JobDefinitionForm;
  reset(): any;
  // isValidating: { current: boolean };
  isValidating: boolean;
  isEasyMode: boolean;
};

export const COMPOSE_DRAWER_CHANNELS = {
  broadcast_error: 'broadcast_error',
  validation_passed: 'validation_passed',
  inspect: 'inspect',
  highlight: 'highlight',
};

export type InspectPayload = {
  jobUuid?: string;
  perspective?: Perspective;
} & HighlightPayload;

export type HighlightPayload = {
  varUuid?: string;
  slotName?: string;
};

export const ComposeDrawerContext = React.createContext({
  uuid: undefined as string | undefined,
  formData: undefined as JobDefinitionForm | undefined,
  formInstance: undefined as FormInstance<JobDefinitionForm> | undefined,
  isEasyMode: true as boolean,
});

const JobComposeDrawer: ForwardRefRenderFunction<ExposedRef, Props> = (
  {
    isGlobal,
    isCheck,
    revisionId,
    uuid,
    prevNode,
    visible,
    toggleVisible,
    onClose,
    onSubmit,
    onDelete,
    onBack,
    ...props
  },
  parentRef,
) => {
  const [formData, setFormData] = useState<JobDefinitionForm>(undefined as any);
  const [isEasyMode, toggleEasyMode] = useToggle(IS_DEFAULT_EASY_MODE);
  const [formInstance] = Form.useForm<JobDefinitionForm>();
  const [isValidating, toggleValidating] = useToggle(false);
  const drawerTitle = () => {
    if (isCheck && isGlobal) {
      return '全局变量';
    }
    if (isCheck && !isGlobal) {
      return `${formData?.name || '任务'}`;
    }
    if (!isCheck && isGlobal) {
      return '编辑全局变量';
    }
    if (!isCheck && !isGlobal) {
      return `编辑${formData?.name || '任务'}`;
    }
  };

  // =========== Callbacks =================
  const onFinish = useCallback(
    (values: JobDefinitionForm) => {
      PubSub.publish(COMPOSE_DRAWER_CHANNELS.validation_passed);
      onSubmit && onSubmit(values.variables ? values : formInstance.getFields());
      toggleVisible && toggleVisible(false);
    },

    [onSubmit],
  );
  const onValidationFailed = useCallback((errors: { [key: string]: FieldError }) => {
    const errorFields: { name: string[] }[] = [];
    Object.keys(errors).forEach((key) => {
      errorFields.push({
        name: key.split('.'),
      });
    });
    const errInfo: ValidateErrorEntity<any> = {
      values: undefined,
      errorFields: errorFields,
      outOfDate: false,
    };
    Message.warning('配置有误，请检查');
    PubSub.publish(COMPOSE_DRAWER_CHANNELS.broadcast_error, errInfo);
  }, []);
  const onValuesChange = useCallback((_: any, values: JobDefinitionForm) => {
    setFormData(values);
  }, []);
  const getFormValues = useCallback(() => {
    return formInstance.getFieldsValue() as JobDefinitionForm;
  }, []);
  const reset = useCallback(() => {
    return formInstance.resetFields();
  }, []);
  const validateFields = useCallback(() => {
    return new Promise<boolean>((resolve) => {
      toggleValidating(true);
      setTimeout(() => {
        formInstance
          .validate()
          .then(() => {
            resolve(true);
          })
          .catch(() => {
            resolve(false);
          })
          .finally(() => {
            toggleValidating(false);
          });
      }, 50);
    });
  }, []);
  const onJobTypeChange = useCallback(
    (type: JobType) => {
      const slotEntries: SlotEntries = [];

      const jobMetaData = jobTypeToMetaDatasMap.get(type);

      if (jobMetaData && uuid) {
        slotEntries.push(...Object.entries(jobMetaData.slots));
        editorInfosStore.upsertValue(uuid, { slotEntries, meta_yaml: jobMetaData.metaYamlString });
      }

      const nextFormData = jobMetaData
        ? { ...formData, job_type: type, _slotEntries: slotEntries }
        : { ...formData, job_type: type, _slotEntries: [] };

      setFormData(nextFormData);
      formInstance.setFieldsValue(nextFormData);
    },
    [formData, uuid],
  );

  useImperativeHandle(parentRef, () => {
    return {
      validate: validateFields,
      getFormValues,
      reset,
      isEasyMode,
      isValidating,
    };
  });

  useEffect(() => {
    if (uuid && formInstance && visible) {
      const slotEntries: SlotEntries = [];
      // Get definition and editor info by job uuid
      // if either of them not exist, create a new one
      const definition =
        definitionsStore.getValueById(uuid) ?? definitionsStore.insertNewResource(uuid);
      const editorInfo =
        editorInfosStore.getValueById(uuid) ?? editorInfosStore.insertNewResource(uuid);

      editorInfo && slotEntries.push(...editorInfo.slotEntries);

      const nextFormData = { ...definition, _slotEntries: slotEntries };

      // Legacy templates don't have easy_mode field
      toggleEasyMode(definition.easy_mode ?? IS_DEFAULT_EASY_MODE);
      setFormData(nextFormData);
      formInstance.setFieldsValue(nextFormData);
    }
  }, [uuid, visible]);

  useEffect(() => {
    toggleVisible(false);
  }, [revisionId]);

  useSubscribe(
    COMPOSE_DRAWER_CHANNELS.inspect,
    (_: string, { jobUuid }: InspectPayload) => {
      if (jobUuid) {
        const definition = definitionsStore.getValueById(jobUuid);

        if (definition && !definition.easy_mode && !isEasyMode) {
          Modal.confirm({
            title: '提示',
            content: '任务当前模式为专家模式，不展示插槽，如需查看，请切换至普通模式',
          });
        }
      }
    },
    [isEasyMode],
  );

  return (
    <ComposeDrawerContext.Provider value={{ uuid, formInstance, formData, isEasyMode }}>
      <Drawer
        className={styled.compose_drawer}
        wrapClassName="#app-content"
        visible={visible}
        mask={false}
        width="1200px"
        onCancel={closeDrawer}
        headerStyle={{ display: 'none' }}
        {...props}
        footer={null}
      >
        <Spin loading={isValidating} style={{ width: '100%' }}>
          <Row className={styled.drawer_header} align="center" justify="space-between">
            <GridRow align="center" gap={10}>
              {prevNode && (
                <Tooltip content="返回上一个浏览的任务">
                  <Button icon={<IconLeft />} size="small" onClick={onBack}>
                    返回
                  </Button>
                </Tooltip>
              )}
              <h3 className={styled.drawer_title}>{drawerTitle()}</h3>
            </GridRow>
            <GridRow gap="10">
              <>
                <Button size="small" icon={<IconSwap />} onClick={onModeToggle}>
                  {isEasyMode ? '专家模式' : '普通模式'}
                </Button>

                {!isGlobal && (
                  <Popconfirm
                    disabled={isCheck}
                    title="删除后，该 Job 配置的内容都将丢失"
                    cancelText="取消"
                    okText="确认"
                    onConfirm={onDeleteClick}
                  >
                    <Button
                      disabled={isCheck}
                      size="small"
                      type="primary"
                      icon={<IconDelete />}
                      status="danger"
                    >
                      删除
                    </Button>
                  </Popconfirm>
                )}
              </>

              <Button size="small" icon={<IconClose />} onClick={closeDrawer} />
            </GridRow>
          </Row>

          <Form
            labelCol={{ span: 6 }}
            wrapperCol={{ span: 18 }}
            form={formInstance}
            onSubmit={onFinish}
            onSubmitFailed={onValidationFailed}
            onValuesChange={onValuesChange as any}
            initialValues={{ ...DEFAULT_JOB, easy_mode: isEasyMode }}
          >
            {/* NOTE: easy_mode is also a part of payload,
             * but we are changing the value through the button in header,
             * not by this form item's switch
             */}
            <Form.Item field="easy_mode" hidden triggerPropName="checked">
              <Switch disabled={isCheck} />
            </Form.Item>

            {isEasyMode ? (
              <DefaultMode
                isCheck={isCheck}
                isGlobal={isGlobal}
                onJobTypeChange={onJobTypeChange}
              />
            ) : (
              <ExpertMode isCheck={isCheck} isGlobal={isGlobal} />
            )}

            <Form.Item>
              <GridRow className={styled.button_grid_row} gap={16}>
                <Button disabled={isCheck} type="primary" htmlType="submit" loading={isValidating}>
                  确认
                </Button>
                <Button onClick={closeDrawer}>取消</Button>
              </GridRow>
            </Form.Item>
          </Form>
        </Spin>
      </Drawer>
    </ComposeDrawerContext.Provider>
  );

  function closeDrawer() {
    onClose && onClose();
    toggleVisible && toggleVisible(false);
  }
  function onDeleteClick() {
    onDelete && onDelete();
  }
  function onModeToggle() {
    toggleEasyMode();
    const nextFormData = { ...formData, easy_mode: !isEasyMode };
    setFormData(nextFormData);
    formInstance.setFieldsValue({ easy_mode: !isEasyMode });
  }
};

export function scrollDrawerBodyTo(scrollTo: number) {
  const target = document.querySelector('#app-content .compose-drawer .arco-drawer-content');

  if (target) {
    target.scrollTop = scrollTo;
  }
}

export default forwardRef(JobComposeDrawer);
