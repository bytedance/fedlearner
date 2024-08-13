import React, { FC, useMemo } from 'react';
import styled from './index.module.less';
import { Button, Input, Card, Spin, Alert, Form } from '@arco-design/web-react';
import { useHistory, useParams } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import GridRow from 'components/_base/GridRow';
import FormLabel from 'components/FormLabel';
import { templateBaseInfoForm, templateForm, defaultBaseInfoForm } from 'stores/template';
import {
  JobSlotReferenceType,
  WorkflowTemplate,
  WorkflowTemplatePayload,
  WorkflowTemplateType,
} from 'typings/workflow';
import { useQuery } from 'react-query';
import { fetchRevisionDetail, fetchTemplateById } from 'services/workflow';
import {
  definitionsStore,
  TPL_GLOBAL_NODE_UUID,
  preprocessVariables,
  editorInfosStore,
  JobDefinitionForm,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { giveWeakRandomKey } from 'shared/helpers';
import { omit } from 'lodash-es';
import { parseComplexDictField } from 'shared/formSchema';
import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import { useIsFormValueChange } from 'hooks';
import { useGetIsCanEditTemplate } from 'views/WorkflowTemplates/shared';

import {
  parseOtherJobRef,
  parseSelfRef,
  parseWorkflowRef,
} from '../../TemplateConfig/JobComposeDrawer/SloEntrytList/helpers';
import { Job } from 'typings/job';
import { Variable } from 'typings/variable';

type Props = {
  isEdit?: boolean;
  isHydrated?: React.MutableRefObject<boolean>;
  onFormValueChange?: () => void;
};

const TemplateStepOneBasic: FC<Props> = ({
  isEdit,
  isHydrated,
  onFormValueChange: onFormValueChangeFromProps,
}) => {
  const history = useHistory();
  const params = useParams<{ id?: string; revision_id?: string }>();

  const [formInstance] = Form.useForm();
  const [baseInfoTemplate, setBaseInfoTemplate] = useRecoilState(templateBaseInfoForm);
  const [template, setTemplateForm] = useRecoilState(templateForm);

  const { isCanEdit, tip } = useGetIsCanEditTemplate(
    template.kind === WorkflowTemplateType.BUILT_IN,
  );
  const isRevision = Boolean(params.revision_id);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);
  // DO fetch only when it's edit-mode

  const tplQ = useQuery(['fetchTemplate', params.id], () => fetchTemplateById(params.id!), {
    enabled: Boolean(isEdit && !isHydrated?.current),
    retry: 1,
    refetchOnWindowFocus: false,
    onSuccess(res) {
      onQuerySuccess(res.data);
    },
  });

  const templateDetail = useMemo(() => {
    if (!tplQ.data?.data) return undefined;
    return tplQ.data.data;
  }, [tplQ.data]);

  const revisionQuery = useQuery(
    ['fetchRevisionDetail', params.revision_id],
    () => fetchRevisionDetail(params.revision_id!),
    {
      retry: 1,
      refetchOnWindowFocus: false,
      enabled: Boolean(templateDetail !== undefined && isRevision && !isHydrated?.current),
      onSuccess(res) {
        const {
          name,
          kind,
          group_alias,
          created_at,
          updated_at,
          creator_username,
        } = (templateDetail as unknown) as WorkflowTemplate<Job, Variable>;
        const { id, is_local, config, editor_info, comment } = parseComplexDictField(res.data);
        const data: WorkflowTemplate<Job, Variable> = {
          name: name!,
          kind: kind!,
          group_alias: group_alias!,
          created_at,
          updated_at,
          creator_username,
          comment,
          id,
          is_local,
          config,
          editor_info,
        };
        onQuerySuccess(data);
      },
    },
  );
  return (
    <Card className={styled.container} bordered={false}>
      <Spin
        loading={!!isEdit && tplQ.isLoading && revisionQuery.isLoading}
        style={{ width: '100%' }}
      >
        <Form
          className={styled.styled_form}
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 18 }}
          colon={true}
          form={formInstance}
          onSubmit={onFinish}
          initialValues={!isEdit && !isHydrated?.current ? defaultBaseInfoForm : baseInfoTemplate}
          onValuesChange={onFormValueChange}
        >
          {!isCanEdit && <Alert className={styled.styled_alert} type="info" banner content={tip} />}
          <Form.Item
            field="name"
            label="模板名称"
            rules={[
              { required: true, message: '请输入模板名！' },
              {
                match: validNamePattern,
                message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
              },
            ]}
          >
            <Input placeholder="请输入模板名称" disabled={!isRevision && (!isCanEdit || isEdit)} />
          </Form.Item>

          <Form.Item
            field="group_alias"
            label={
              <FormLabel
                label="Group"
                tooltip="模板根据该字段进行匹配，启动工作流时双侧必须选择相同 Group 名的两份模板"
              />
            }
            rules={[{ required: true, message: '请输入 Group 名' }]}
          >
            <Input placeholder="请输入 Group 名" disabled={!isCanEdit} />
          </Form.Item>

          <Form.Item
            field="comment"
            label="工作流模板描述"
            rules={[{ max: MAX_COMMENT_LENGTH, message: '最多为 200 个字符' }]}
          >
            <Input.TextArea
              rows={4}
              placeholder={isCanEdit ? '请输入工作流模板描述' : undefined}
              disabled={!isCanEdit}
            />
          </Form.Item>

          <Form.Item wrapperCol={{ offset: 6 }}>
            <GridRow gap={16} top="12">
              <Button type="primary" htmlType="submit">
                下一步
              </Button>

              <ButtonWithModalConfirm
                onClick={backToList}
                isShowConfirmModal={isFormValueChanged || Boolean(template.name)}
              >
                取消
              </ButtonWithModalConfirm>
            </GridRow>
          </Form.Item>
        </Form>
      </Spin>
    </Card>
  );

  function backToList() {
    history.push(`/workflow-center/workflow-templates`);
  }
  function onFormChange(
    _: any,
    values: Pick<WorkflowTemplatePayload, 'comment' | 'group_alias' | 'name'>,
  ) {
    onFormValueChangeFromProps?.();
    setTemplateForm({
      ...template,
      ...values,
    });
    setBaseInfoTemplate({
      ...baseInfoTemplate,
      ...values,
    });
  }
  function onFinish() {
    if (isHydrated) {
      isHydrated.current = true;
    }

    let path = `/workflow-center/workflow-templates/create/jobs`;
    if (isEdit && !isRevision) {
      path = `/workflow-center/workflow-templates/edit/jobs/${params.id}`;
    }
    if (isEdit && isRevision) {
      path = `/workflow-center/workflow-templates/edit/jobs/${params.id}/${params.revision_id}`;
    }
    history.push(path);
  }
  function onQuerySuccess(data: WorkflowTemplate<Job, Variable>) {
    /**
     * Parse the template data from server:
     * 1. basic infos like name, group_alias... write to recoil all the same
     * 2. each job_definition will be tagged with a uuid,
     *    and replace deps souce job name with corresponding uuid,
     *    then the {uuid, dependencies} will save to recoil and real job def values should go ../store.ts
     */
    const {
      name,
      kind,
      group_alias,
      created_at,
      updated_at,
      creator_username,
      comment,
      id,
      is_local,
      config,
      editor_info,
    } = parseComplexDictField(data);

    formInstance.setFieldsValue({ name, comment, group_alias });

    definitionsStore.upsertValue(TPL_GLOBAL_NODE_UUID, {
      variables: config.variables.map(preprocessVariables),
    } as JobDefinitionForm);
    /**
     * 1. Genrate a Map<uuid, job-name>
     * 2. upsert job definition values to store
     *  - need to stringify code type variable's value
     */
    const nameToUuidMap = config.job_definitions.reduce((map, job) => {
      const thisJobUuid = giveWeakRandomKey();
      map[job.name] = thisJobUuid;

      const value = omit(job, 'dependencies') as JobDefinitionForm;
      value.variables = value.variables.map(preprocessVariables);
      // Save job definition values to definitionsStore
      definitionsStore.upsertValue(thisJobUuid, { ...value });

      return map;
    }, {} as Record<string, string>);
    /**
     * Convert job & variable name in reference to
     * job & variable's UUID we assign above
     */
    config.job_definitions.forEach((job) => {
      const jobUuid = nameToUuidMap[job.name];
      const self = definitionsStore.getValueById(jobUuid)!;

      // Save job editor info to editorInfosStore
      const targetEditInfo = editor_info?.yaml_editor_infos[job.name];
      if (targetEditInfo) {
        editorInfosStore.upsertValue(jobUuid, {
          slotEntries: Object.entries(targetEditInfo.slots)
            .sort()
            .map(([slotName, slot]) => {
              if (slot.reference_type === JobSlotReferenceType.OTHER_JOB) {
                const [jobName, varName] = parseOtherJobRef(slot.reference);
                const targetJobUuid = nameToUuidMap[jobName];
                const target = definitionsStore.getValueById(targetJobUuid);

                if (target) {
                  slot.reference = slot.reference
                    .replace(jobName, targetJobUuid)
                    .replace(
                      varName,
                      target.variables.find((item) => item.name === varName)?._uuid!,
                    );
                }
              }

              if (slot.reference_type === JobSlotReferenceType.JOB_PROPERTY) {
                const [jobName] = parseOtherJobRef(slot.reference);
                const targetJobUuid = nameToUuidMap[jobName];
                const target = definitionsStore.getValueById(targetJobUuid);

                if (target) {
                  slot.reference = slot.reference.replace(jobName, targetJobUuid);
                }
              }

              if (slot.reference_type === JobSlotReferenceType.SELF) {
                const varName = parseSelfRef(slot.reference);

                slot.reference = slot.reference.replace(
                  varName,
                  self.variables.find((item) => item.name === varName)?._uuid!,
                );
              }

              if (slot.reference_type === JobSlotReferenceType.WORKFLOW) {
                const varName = parseWorkflowRef(slot.reference);
                const globalDef = definitionsStore.getValueById(TPL_GLOBAL_NODE_UUID)!;

                slot.reference = slot.reference.replace(
                  varName,
                  globalDef.variables.find((item) => item.name === varName)?._uuid!,
                );
              }

              return [slotName, slot];
            }),
          meta_yaml: targetEditInfo.meta_yaml,
        });
      } else {
        editorInfosStore.insertNewResource(jobUuid);
      }
    });
    const jobNodeSlimRawDataList = config.job_definitions.map((job) => {
      const uuid = nameToUuidMap[job.name];

      return {
        uuid,
        dependencies: job.dependencies.map((dep) => ({ source: nameToUuidMap[dep.source] })),
      };
    });

    setTemplateForm({
      id,
      name,
      comment,
      is_local,
      group_alias,
      config: {
        variables: [],
        job_definitions: jobNodeSlimRawDataList,
      },
      kind,
      created_at,
      updated_at,
      creator_username,
    });

    if (isHydrated) {
      isHydrated.current = true;
    }
  }
};

export default TemplateStepOneBasic;
