import React, { FC, useCallback, useEffect, useState } from 'react';
import {
  Typography,
  RulesProps,
  Message,
  Select,
  Upload,
  Button,
  Space,
  Input,
  Form,
  Tag,
} from '@arco-design/web-react';
import { useParams, useHistory } from 'react-router-dom';
import { IconCodeSquare, IconInfoCircle } from '@arco-design/web-react/icon';
import { useRecoilValue } from 'recoil';
import { useMutation } from 'react-query';
import { useGetAppFlagValue, useUrlState } from 'hooks/index';
import SharedPageLayout, { FormHeader } from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import CodeEditorModal from 'components/CodeEditorModal';
import {
  fetchProjectDetail,
  createProject,
  patchProject,
  postPublishAlgorithm,
} from 'services/algorithm';
import { FlagKey } from 'typings/flag';
import showSendModal from '../AlgorithmSendModal';
import { projectState } from 'stores/project';
import ParamsInput from '../AlgorithmParamsInput';
import AlgorithmType from 'components/AlgorithmType';
import { AlgorithmTypeOptions } from '../shared';
import { AlgorithmProject, EnumAlgorithmProjectType } from 'typings/algorithm';
import { AlgorithmManagementTabType } from 'typings/modelCenter';
import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';
import { UploadItem } from '@arco-design/web-react/es/Upload';
import { useIsFormValueChange } from 'hooks';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import TitleWithIcon from 'components/TitleWithIcon';
import styled from './index.module.less';

enum FormField {
  NAME = 'name',
  COMMENT = 'comment',
  ALGORITHM_TYPE = 'type',
  Files = 'file',
  PARAMETER = 'parameter',
}

const RULES: Record<FormField, RulesProps[]> = {
  [FormField.NAME]: [
    { required: true, message: '算法名称不能为空' },
    {
      match: validNamePattern,
      message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
    },
  ],
  [FormField.ALGORITHM_TYPE]: [{ required: true }],
  [FormField.Files]: [
    {
      required: false,
      validator(fileList: UploadItem[], callback) {
        const file = fileList[0];
        if (!file) {
          callback(undefined);
          return;
        }

        const isOverSize = file.originFile?.size && file.originFile.size > 100 * 1024 * 1024; // 100M
        callback(isOverSize ? '大小超过限制' : undefined);
      },
    },
  ],
  [FormField.COMMENT]: [
    {
      maxLength: MAX_COMMENT_LENGTH,
      message: '最多为 200 个字符',
    },
  ],
  [FormField.PARAMETER]: [{ required: false }],
};

const defaultValue: Record<FormField, any> = {
  [FormField.NAME]: '',
  [FormField.ALGORITHM_TYPE]: EnumAlgorithmProjectType.NN_HORIZONTAL,
  [FormField.Files]: [],
  [FormField.COMMENT]: '',
  [FormField.PARAMETER]: [],
};

type TMutationParams<T, K = AlgorithmProject> = {
  id: ID;
  payload: T;
  project?: K;
  shouldPublish?: boolean;
};

const AlgorithmForm: FC = () => {
  const [form] = Form.useForm();
  const history = useHistory();
  const [urlState] = useUrlState();
  const { action } = useParams<{ action: 'edit' | 'create' }>();
  const [project, setProject] = useState<AlgorithmProject>();
  const [codeEditorVisible, setCodeEditorVisible] = useState<boolean>(false);
  const [codeEditorTouched, setCodeEditorTouched] = useState<boolean>(false);
  const selectedProject = useRecoilValue(projectState);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();
  const trusted_computing_enabled = useGetAppFlagValue(FlagKey.TRUSTED_COMPUTING_ENABLED);

  const isEdit = action === 'edit';
  if (trusted_computing_enabled) {
    AlgorithmTypeOptions.push({
      label: '可信计算',
      value: EnumAlgorithmProjectType.TRUSTED_COMPUTING,
    });
  }

  const createProjectMutation = useMutation(
    async ({ id, payload, project, shouldPublish }: TMutationParams<FormData>) => {
      if (shouldPublish) {
        await publishAlgorithmWrap(project!, () =>
          createProject(id, payload as FormData).then((res) => res.data),
        );
        Message.success('创建并发版成功');
      } else {
        await createProject(id, payload as FormData);
        Message.success('创建成功');
      }
      return project;
    },
    {
      onSuccess: () => {
        goBackProjectList();
      },
      onError(e: any) {
        if (e.code === 409) {
          Message.error('算法名称已存在');
        } else {
          Message.error(e.message);
        }
      },
    },
  );
  const updateProjectMutation = useMutation(
    async (params: TMutationParams<Partial<AlgorithmProject>>) => {
      const { id, payload, shouldPublish } = params;
      const action = () =>
        patchProject(id, {
          comment: payload.comment,
          parameter: payload.parameter,
        } as Partial<AlgorithmProject>).then((res) => res.data);

      if (shouldPublish) {
        await publishAlgorithmWrap(project!, action);
        Message.success('编辑并发版成功');
      } else {
        await action();
        Message.success('编辑成功');
      }
      return { ...project, ...payload };
    },
    {
      onSuccess: () => {
        goBackProjectList();
      },
    },
  );
  const goBackProjectList = useCallback(
    (replace = false) => {
      const url = `/algorithm-management/${AlgorithmManagementTabType.MY}`;
      return replace ? history.replace(url) : history.push(url);
    },
    [history],
  );

  useEffect(() => {
    if (!isEdit) {
      form.setFieldsValue(defaultValue);
      return;
    }
    if (!urlState.id) {
      goBackProjectList(true);
      return;
    }
    fetchProjectDetail(urlState.id)
      .then(({ data }) => {
        setProject(data);
        form.setFieldsValue({
          [FormField.NAME]: data.name,
          [FormField.ALGORITHM_TYPE]: data.type,
          [FormField.COMMENT]: data.comment,
          [FormField.PARAMETER]:
            (data.parameter?.variables ?? []).length > 0
              ? data.parameter!.variables
              : defaultValue[FormField.PARAMETER],
        });
      })
      .catch(() => {});
  }, [form, goBackProjectList, isEdit, urlState.id]);

  // if the code editor is visible, try to prevent user from closing the page
  useEffect(() => {
    const handler = (e: Event) => {
      const msg = 'Are you sure to leave?';
      e.preventDefault();
      // @ts-ignore
      e.returnValue = msg;
      return msg;
    };
    if (codeEditorVisible) {
      window.addEventListener('beforeunload', handler);
    }

    return () => {
      window.removeEventListener('beforeunload', handler);
    };
  }, [codeEditorVisible]);

  return (
    <SharedPageLayout
      title={
        <BackButton
          onClick={goBackProjectList}
          isShowConfirmModal={isFormValueChanged || codeEditorTouched}
        >
          {'算法仓库'}
        </BackButton>
      }
    >
      <FormHeader>{isEdit ? '编辑算法' : '创建算法'}</FormHeader>
      <Form form={form} layout="vertical" onChange={onFormValueChange}>
        <Typography.Text className={styled.styled_big_text} bold>
          {'基本信息'}
        </Typography.Text>
        <Form.Item
          className={styled.styled_form_item}
          field={FormField.NAME}
          label={'算法名称'}
          rules={RULES[FormField.NAME]}
        >
          {isEdit ? (
            <Typography.Text>{project?.name}</Typography.Text>
          ) : (
            <Input readOnly={isEdit} placeholder={'请输入算法名称'} />
          )}
        </Form.Item>
        <Form.Item
          className={styled.styled_form_item}
          field={FormField.COMMENT}
          label={'算法描述'}
          rules={RULES[FormField.COMMENT]}
        >
          <Input.TextArea rows={2} placeholder={'最多为 200 个字符'} />
        </Form.Item>
        <Form.Item
          className={styled.styled_form_item}
          field={FormField.ALGORITHM_TYPE}
          label={'算法类型'}
          rules={RULES[FormField.ALGORITHM_TYPE]}
        >
          {isEdit && project?.type ? (
            <AlgorithmType type={project.type} />
          ) : (
            <Select options={AlgorithmTypeOptions} />
          )}
        </Form.Item>
        <TitleWithIcon
          title="选择纵向联邦-NN模型时，代码层级的首层必须为leader和follower两个文件夹"
          isLeftIcon={true}
          isShowIcon={true}
          icon={IconInfoCircle}
          className={styled.title_with_icon}
        />
        {!isEdit ? (
          <Form.Item
            className={styled.styled_form_item}
            field={FormField.Files}
            label={'算法文件'}
            rules={RULES[FormField.Files]}
          >
            <Upload
              drag
              multiple={false}
              limit={1}
              accept=".gz,.tar"
              tip={'仅支持上传1个 .tar 或 .gz 格式文件，大小不超过 100 MiB'}
            />
          </Form.Item>
        ) : (
          <Form.Item className={styled.styled_form_item} label={'算法文件'}>
            <div
              className={styled.styled_code_editor_entry}
              onClick={() => {
                setCodeEditorVisible(true);
              }}
            >
              <div>
                <IconCodeSquare className={styled.styled_icon_code_square} />
                <br />
                <Typography.Text bold>{'代码编辑器'}</Typography.Text>
              </div>
              <div className={styled.styled_status_row}>
                <Tag
                  className={
                    codeEditorTouched ? styled.styled_unsaved_tag : styled.styled_saved_tag
                  }
                >
                  {codeEditorTouched ? '已保存' : '未编辑'}
                </Tag>
                {'点击进入代码编辑器'}
              </div>
            </div>
          </Form.Item>
        )}
        <Typography.Text className={styled.styled_big_text} bold>
          {'超参数'}
        </Typography.Text>
        <Form.Item
          className={styled.styled_form_item}
          field={FormField.PARAMETER}
          style={{ marginLeft: 12, width: '80%', minWidth: 800 }}
        >
          <ParamsInput />
        </Form.Item>

        <Form.Item className={styled.styled_form_item} label="">
          <Space className={styled.styled_footer_space}>
            <Button
              loading={createProjectMutation.isLoading || updateProjectMutation.isLoading}
              onClick={() => submitForm()}
              type="primary"
            >
              {'提交'}
            </Button>
            <Button
              loading={createProjectMutation.isLoading || updateProjectMutation.isLoading}
              onClick={() => submitForm(true)}
              type="primary"
            >
              {'提交并发版'}
            </Button>
            <ButtonWithModalConfirm
              onClick={goBackProjectList}
              isShowConfirmModal={isFormValueChanged || codeEditorTouched}
            >
              {'取消'}
            </ButtonWithModalConfirm>
          </Space>
        </Form.Item>
      </Form>
      {project ? (
        <CodeEditorModal.AlgorithmProject
          isAsyncMode={true}
          id={project.id}
          visible={codeEditorVisible}
          title={project.name}
          onClose={() => {
            setCodeEditorVisible(false);
            setCodeEditorTouched(true);
          }}
        />
      ) : null}
    </SharedPageLayout>
  );

  async function submitForm(shouldPublish = false) {
    const projectId = urlState.id;
    await form.validate();
    const values = form.getFieldsValue();
    const parameter = {
      variables: values[FormField.PARAMETER].filter((item: any) => item.name),
    };

    if (isEdit) {
      updateProjectMutation.mutate({
        id: projectId,
        shouldPublish,
        payload: {
          ...values,
          [FormField.PARAMETER]: parameter,
        } as any,
      });
    } else {
      if (!selectedProject.current?.id) {
        Message.info('请选择工作区');
        return;
      }
      const file = values[FormField.Files]?.[0]?.originFile;
      const formData = new FormData();
      formData.append(FormField.NAME, values[FormField.NAME]);
      if (file) {
        formData.append(FormField.Files, file);
      }
      formData.append(FormField.ALGORITHM_TYPE, values[FormField.ALGORITHM_TYPE]);
      formData.append(FormField.PARAMETER, JSON.stringify(parameter));
      formData.append(FormField.COMMENT, values[FormField.COMMENT]);

      await createProjectMutation.mutate({
        id: selectedProject.current?.id,
        shouldPublish,
        project: values as AlgorithmProject,
        payload: formData,
      });
    }
  }

  function publishAlgorithmWrap(
    algorithm: AlgorithmProject,
    beforePublish: () => Promise<AlgorithmProject>,
  ) {
    return new Promise((resolve, reject) => {
      showSendModal(
        algorithm,
        async (comment: string) => {
          try {
            const res = await beforePublish();
            await postPublishAlgorithm(res.id, comment);
            resolve('');
          } catch (e) {
            reject(e);
          }
        },
        () => {
          reject(null);
        },
        true,
      );
    });
  }
};

export default AlgorithmForm;
