import React, { useEffect, useMemo, useState } from 'react';

import { useHistory, useParams } from 'react-router';
import { useQuery } from 'react-query';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useGetCurrentPureDomainName,
  useIsFormValueChange,
} from 'hooks';
import {
  createModeJobGroupV2,
  fetchModelJobGroupDetail,
  updateModelJobGroup,
} from 'services/modelCenter';
import { fetchDatasetDetail } from 'services/dataset';
import { MAX_COMMENT_LENGTH } from 'shared/validator';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { DataJobBackEndType, DatasetKindLabel } from 'typings/dataset';
import routes from 'views/ModelCenter/routes';
import { ALGORITHM_TYPE_LABEL_MAPPER } from 'views/ModelCenter/shared';

import {
  Avatar,
  Button,
  Card,
  Form,
  Input,
  Message,
  Space,
  Tag,
  Typography,
} from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import BackButton from 'components/BackButton';
import SharedPageLayout from 'components/SharedPageLayout';
import BlockRadio from 'components/_base/BlockRadio';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import TitleWithIcon from 'components/TitleWithIcon';
import DatasetSelect from 'components/NewDatasetSelect';
import AlgorithmProjectSelect from './AlgorithmProjectSelect';
import { LabelStrong } from 'styles/elements';

const federalTypeOptions = [
  {
    value: EnumAlgorithmProjectType.TREE_VERTICAL,
    label: ALGORITHM_TYPE_LABEL_MAPPER[EnumAlgorithmProjectType.TREE_VERTICAL],
  },
  {
    value: EnumAlgorithmProjectType.NN_VERTICAL,
    label: ALGORITHM_TYPE_LABEL_MAPPER[EnumAlgorithmProjectType.NN_VERTICAL],
  },
  {
    value: EnumAlgorithmProjectType.NN_HORIZONTAL,
    label: ALGORITHM_TYPE_LABEL_MAPPER[EnumAlgorithmProjectType.NN_HORIZONTAL],
  },
];

const defaultRules = [{ required: true, message: '必选项' }];

export default function CreateCentralization() {
  const history = useHistory();
  const { role, id: modelJobGroupId } = useParams<{ role: string; id: string }>();
  const isReceiver = role === 'receiver';

  const [formInstance] = Form.useForm();
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();

  const [selectedAlgorithmType, setSelectedAlgorithmType] = useState<EnumAlgorithmProjectType>(
    EnumAlgorithmProjectType.TREE_VERTICAL,
  );
  const projectId = useGetCurrentProjectId();
  const myPureDomain = useGetCurrentPureDomainName();
  const participantList = useGetCurrentProjectParticipantList();

  const modelJobGroupDetailQuery = useQuery(
    ['fetchModelJobGroupDetail', projectId, modelJobGroupId],
    () => fetchModelJobGroupDetail(projectId!, modelJobGroupId),
    {
      enabled: !!projectId && !!modelJobGroupId,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const datasetDetailQuery = useQuery(
    ['fetchDatasetDetail', modelJobGroupDetailQuery.data?.data.dataset_id],
    () => fetchDatasetDetail(modelJobGroupDetailQuery.data?.data.dataset_id),
    {
      enabled: !!modelJobGroupDetailQuery.data?.data.dataset_id,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const modelJobGroupDetail = useMemo(() => {
    return modelJobGroupDetailQuery.data?.data;
  }, [modelJobGroupDetailQuery.data?.data]);
  const datasetDetail = useMemo(() => {
    return datasetDetailQuery.data?.data;
  }, [datasetDetailQuery.data?.data]);

  const coordinatorName = useMemo(() => {
    return (
      participantList.find((participant) => participant.id === modelJobGroupDetail?.coordinator_id)
        ?.name ?? '未知合作伙伴'
    );
  }, [modelJobGroupDetail?.coordinator_id, participantList]);

  useEffect(() => {
    if (!modelJobGroupDetail) {
      return;
    }
    formInstance.setFieldsValue({
      ...modelJobGroupDetail,
      algorithm_project_list: {
        algorithmProjects: modelJobGroupDetail.algorithm_project_uuid_list?.algorithm_projects,
      },
    });
  }, [formInstance, modelJobGroupDetail]);

  useEffect(() => {
    if (!modelJobGroupDetail) {
      return;
    }
    setSelectedAlgorithmType(modelJobGroupDetail.algorithm_type as EnumAlgorithmProjectType);
  }, [modelJobGroupDetail]);
  return (
    <SharedPageLayout
      title={
        <BackButton isShowConfirmModal={isFormValueChanged} onClick={goBackToListPage}>
          模型训练
        </BackButton>
      }
      contentWrapByCard={false}
      centerTitle={'创建模型训练'}
    >
      {isReceiver && (
        <Card className="card" bordered={false} style={{ marginBottom: 20 }}>
          <Space size="medium">
            <Avatar />
            <>
              <LabelStrong
                fontSize={16}
              >{`${coordinatorName}向您发起「${modelJobGroupDetail?.name}」的模型训练作业`}</LabelStrong>
              <TitleWithIcon
                title={'所有合作伙伴授权完成后，任意合作方均可发起模型训练任务。'}
                isLeftIcon={true}
                isShowIcon={true}
                icon={IconInfoCircle}
              />
            </>
          </Space>
        </Card>
      )}
      <Card className="card" bordered={false} style={{ height: '100%' }}>
        <Form
          className="form-content"
          form={formInstance}
          onChange={onFormValueChange}
          onSubmit={handelSubmit}
        >
          <section className="form-section">
            <h3>基本信息</h3>
            <Form.Item
              field="name"
              label="模型训练名称"
              rules={[{ required: true, message: '必填项' }]}
            >
              {isReceiver ? (
                <Typography.Text bold={true}>{modelJobGroupDetail?.name}</Typography.Text>
              ) : (
                <Input placeholder="请输入模型训练名称" />
              )}
            </Form.Item>
            <Form.Item
              field={'comment'}
              label={'描述'}
              rules={[
                {
                  maxLength: MAX_COMMENT_LENGTH,
                  message: '最多为 200 个字符',
                },
              ]}
            >
              <Input.TextArea placeholder={'最多为 200 个字符'} />
            </Form.Item>
          </section>
          <section className="form-section">
            <h3>训练配置</h3>
            <Form.Item
              field={'algorithm_type'}
              label={'联邦类型'}
              rules={[{ required: true, message: '必选项' }]}
              initialValue={selectedAlgorithmType}
            >
              {isReceiver ? (
                <Typography.Text bold={true}>
                  {
                    ALGORITHM_TYPE_LABEL_MAPPER[
                      modelJobGroupDetail?.algorithm_type || EnumAlgorithmProjectType.TREE_VERTICAL
                    ]
                  }
                </Typography.Text>
              ) : (
                <BlockRadio
                  options={federalTypeOptions}
                  isCenter={true}
                  onChange={(value) => {
                    setSelectedAlgorithmType(value);
                    formInstance.setFieldValue('dataset_id', undefined);
                  }}
                />
              )}
            </Form.Item>
            <Form.Item
              label={'数据集'}
              field={'dataset_id'}
              rules={defaultRules}
              shouldUpdate={true}
            >
              {isReceiver ? (
                <Space>
                  <Typography.Text bold={true}>{datasetDetail?.name}</Typography.Text>
                  <Tag color="arcoblue">结果</Tag>
                </Space>
              ) : (
                <DatasetSelect
                  lazyLoad={{
                    enable: true,
                    page_size: 10,
                  }}
                  kind={DatasetKindLabel.PROCESSED}
                  datasetJobKind={
                    selectedAlgorithmType === EnumAlgorithmProjectType.NN_HORIZONTAL
                      ? DataJobBackEndType.DATA_ALIGNMENT
                      : undefined
                  }
                />
              )}
            </Form.Item>
            {[
              EnumAlgorithmProjectType.NN_HORIZONTAL,
              EnumAlgorithmProjectType.NN_VERTICAL,
            ].includes(selectedAlgorithmType) && (
              <>
                <Form.Item
                  field={resetField(myPureDomain, 'algorithm_project_list.algorithmProjects')}
                  label="我方算法"
                  rules={defaultRules}
                >
                  <AlgorithmProjectSelect
                    algorithmType={[selectedAlgorithmType]}
                    supportEdit={!isReceiver}
                  />
                </Form.Item>
                {participantList.map((participant) => {
                  return (
                    <Form.Item
                      key={participant.id}
                      field={resetField(
                        participant.pure_domain_name,
                        'algorithm_project_list.algorithmProjects',
                      )}
                      label={`${participant.name}算法`}
                      rules={defaultRules}
                    >
                      <AlgorithmProjectSelect
                        algorithmType={[selectedAlgorithmType]}
                        supportEdit={!isReceiver}
                      />
                    </Form.Item>
                  );
                })}
              </>
            )}
          </section>
          <Space>
            <Button type="primary" htmlType="submit">
              {isReceiver ? '授权' : '提交并发送'}
            </Button>

            <ButtonWithModalConfirm
              isShowConfirmModal={isFormValueChanged}
              onClick={goBackToListPage}
            >
              取消
            </ButtonWithModalConfirm>
            <TitleWithIcon
              title={'所有合作伙伴授权完成后，任意合作方均可发起模型训练任务。'}
              isLeftIcon={true}
              isShowIcon={true}
              icon={IconInfoCircle}
            />
          </Space>
        </Form>
      </Card>
    </SharedPageLayout>
  );
  function resetField(participantName: string, fieldName: string) {
    return `${fieldName}.${participantName}`;
  }
  function goBackToListPage() {
    history.push(routes.ModelTrainList);
  }

  async function handelSubmit(value: any) {
    if (!projectId) {
      Message.info('请选择工作区！');
      return;
    }
    if (!isReceiver) {
      try {
        await createModeJobGroupV2(projectId, value);
        Message.info('创建成功');
        history.push(routes.ModelTrainList);
      } catch (error: any) {
        Message.error(error.message);
      }
    } else {
      try {
        await updateModelJobGroup(projectId, modelJobGroupDetail?.id!, {
          authorized: true,
          comment: value?.comment,
        });
        Message.info('授权成功');
        history.push(routes.ModelTrainList);
      } catch (error: any) {
        Message.error(error.message);
      }
    }
  }
}
