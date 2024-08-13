import React, { FC, useState } from 'react';
import { useHistory, useParams } from 'react-router';
import { Avatar, Button, Card, Form, Input, Message, Space, Spin } from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { useToggle } from 'react-use';
import { useQuery } from 'react-query';
import { LabelStrong } from 'styles/elements';
import { getResourceConfigInitialValues, defaultTrustedJobGroup } from '../shared';
import { to } from 'shared/helpers';

import BackButton from 'components/BackButton';
import DatasetSelect from 'components/DatasetSelect';
import SharedPageLayout from 'components/SharedPageLayout';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import ResourceConfig, { Value as ResourceConfigValue } from 'components/ResourceConfig';
import TitleWithIcon from 'components/TitleWithIcon';
import { useTranslation } from 'react-i18next';
import routeMaps from '../routes';
import './index.less';

import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useGetCurrentProjectParticipantName,
  useIsFormValueChange,
} from 'hooks';
import {
  ResourceTemplateType,
  TrustedJobGroupPayload,
  ParticipantDataset,
  AuthStatus,
  TrustedJobGroup,
  TrustedJobGroupStatus,
} from 'typings/trustedCenter';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { Dataset, DatasetDataType, DatasetKindBackEndType } from 'typings/dataset';
import {
  createTrustedJobGroup,
  fetchTrustedJobGroupById,
  launchTrustedJobGroup,
  updateTrustedJobGroup,
} from 'services/trustedCenter';
import AlgorithmSelect, { AlgorithmSelectValue } from 'components/AlgorithmSelect';

type FormData = TrustedJobGroupPayload & {
  resource_config: ResourceConfigValue;
  algorithm_type: EnumAlgorithmProjectType;
  algorithm_info?: AlgorithmSelectValue;
  self_dataset_info: Dataset;
  participant: any;
};

const TrustedJobGroupForm: FC<{ isEdit?: boolean }> = ({ isEdit }) => {
  const [formInstance] = Form.useForm<FormData>();
  const history = useHistory();
  const { t } = useTranslation();
  const projectId = useGetCurrentProjectId();
  const participantList = useGetCurrentProjectParticipantList();
  const participantName = useGetCurrentProjectParticipantName();
  const params = useParams<{ id: string; role: 'sender' | 'receiver' }>();

  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);
  const [trustedJobGroup, setTrustedJobGroup] = useState<TrustedJobGroup>(defaultTrustedJobGroup);
  const [formData, setFormData] = useState<Partial<FormData>>();
  const [algorithmOwner, setAlgorithmOwner] = useState<string>('');
  const [isLaunch, toggleIsLaunch] = useToggle(false);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const trustedJobGroupQuery = useQuery(
    ['fetchTrustedJobGroupById', params.id],
    () => {
      return fetchTrustedJobGroupById(projectId!, params.id);
    },
    {
      enabled: Boolean(isEdit),
      retry: 1,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        const data = res.data;
        setTrustedJobGroup(data);
        setAlgorithmOwner(data.algorithm_participant_id === 0 ? 'self' : 'peer');
        const participant_datasets: any[] = [];
        data.participant_datasets.items.forEach((item) => {
          participant_datasets[item.participant_id as number] = {
            dataset_info: {
              participant_id: item.participant_id,
              uuid: item.uuid,
              name: item.name,
            },
          };
        });
        formInstance.setFieldsValue({
          name: data.name,
          comment: data.comment,
          algorithm_id: data.algorithm_id,
          algorithm_info: {
            //可信计算暂时不需要配置算法超参数
            algorithmId: data.algorithm_id,
            algorithmProjectUuid: data.algorithm_project_uuid,
            algorithmUuid: data.algorithm_uuid,
            participantId: data.algorithm_participant_id,
          },

          self_dataset_info: {
            id: data.dataset_id,
          },
          participant: participant_datasets,
          resource_config: data?.resource
            ? getResourceConfigInitialValues(data.resource!)
            : undefined,
        });
      },
    },
  );

  const isReceiver = params.role === 'receiver';
  const isPeerUnauthorized = isReceiver && !trustedJobGroup?.resource;
  const algorithmType = EnumAlgorithmProjectType.TRUSTED_COMPUTING;

  return (
    <SharedPageLayout
      title={
        <BackButton onClick={goBackToListPage}>
          {t('trusted_center.label_trusted_center')}
        </BackButton>
      }
      contentWrapByCard={false}
      centerTitle={isEdit ? (isPeerUnauthorized ? '授权可信计算' : '编辑可信计算') : '创建可信计算'}
    >
      <Spin loading={trustedJobGroupQuery.isLoading}>
        <div className="group-form-container">
          {isPeerUnauthorized ? renderReceiverLayout() : renderSenderLayout()}
        </div>
      </Spin>
    </SharedPageLayout>
  );

  function renderReceiverLayout() {
    return (
      <>
        {isEdit && renderBannerCard()}
        {renderContentCard()}
      </>
    );
  }
  function renderSenderLayout() {
    return <>{renderContentCard()}</>;
  }
  function renderBannerCard() {
    const title = t('trusted_center.title_authorization_request', {
      peerName: participantName,
      name: trustedJobGroupQuery.data?.data?.name ?? '',
    });
    return (
      <Card className="card" bordered={false} style={{ marginBottom: 20 }}>
        <Space size="medium">
          <Avatar />
          <>
            <LabelStrong fontSize={16}>{title ?? '....'}</LabelStrong>
            <TitleWithIcon
              title={t('trusted_center.tip_agree_authorization')}
              isLeftIcon={true}
              isShowIcon={true}
              icon={IconInfoCircle}
            />
          </>
        </Space>
      </Card>
    );
  }
  function renderContentCard() {
    return (
      <Card className="card" bordered={false}>
        <Form
          className="form"
          form={formInstance}
          initialValues={formData}
          onSubmit={onSubmit}
          onValuesChange={onFormValueChange}
          scrollToFirstError
        >
          {renderBaseInfoConfig()}
          {renderComputingConfig()}
          {renderResourceConfig()}
          {renderFooterButton()}
        </Form>
      </Card>
    );
  }

  function renderBaseInfoConfig() {
    return (
      <section className="form-section">
        <h3>{t('trusted_center.title_base_info')}</h3>
        <Form.Item
          field="name"
          label={t('trusted_center.label_computing_name')}
          rules={[{ required: true, message: t('trusted_center.msg_required') }]}
          disabled={isEdit}
        >
          <Input placeholder={t('trusted_center.placeholder_input')} />
        </Form.Item>
        <Form.Item field="comment" label={t('trusted_center.label_description')}>
          <Input.TextArea placeholder={t('trusted_center.placeholder_input_comment')} />
        </Form.Item>
      </section>
    );
  }

  function renderComputingConfig() {
    return (
      <section className="form-section">
        <h3>{t('trusted_center.title_computing_config')}</h3>
        <Form.Item
          field="algorithm_info"
          label={t('trusted_center.label_algorithm_select')}
          rules={[{ required: true, message: t('trusted_center.msg_required') }]}
        >
          <AlgorithmSelect
            algorithmType={[algorithmType]}
            algorithmOwnerType={algorithmOwner}
            onAlgorithmOwnerChange={(value: any) => setAlgorithmOwner(value)}
            leftDisabled={isEdit || isReceiver}
            rightDisabled={isReceiver}
            showHyperParameters={false}
            filterReleasedAlgo={true}
          />
        </Form.Item>
        <Form.Item
          field="self_dataset_info"
          label={t('trusted_center.label_our_dataset')}
          disabled={isEdit}
        >
          <DatasetSelect
            lazyLoad={{
              enable: true,
              page_size: 10,
            }}
            isParticipant={false}
            isCreateVisible={!isPeerUnauthorized}
            filterOptions={{
              dataset_format: [DatasetDataType.NONE_STRUCTURED],
              dataset_kind: [DatasetKindBackEndType.RAW],
            }}
            placeholder={t('trusted_center.placeholder_select')}
          />
        </Form.Item>
        {participantList.map((item, index) => {
          return (
            <Form.Item
              field={`participant.${item.id}.dataset_info`}
              label={item.name}
              disabled={isEdit}
            >
              <DatasetSelect
                queryParams={{
                  //TODO Temporarily obtain full data and will be removed soon
                  page_size: 0,
                }}
                isParticipant={true}
                isCreateVisible={!isPeerUnauthorized}
                filterOptions={{
                  dataset_format: [DatasetDataType.NONE_STRUCTURED],
                  dataset_kind: [DatasetKindBackEndType.RAW],
                  participant_id: item.id,
                }}
                placeholder={t('trusted_center.placeholder_select_dataset')}
              />
            </Form.Item>
          );
        })}
      </section>
    );
  }

  function renderResourceConfig() {
    return (
      <section className="form-section">
        <h3>{t('trusted_center.title_resource_config')}</h3>
        <Form.Item
          field="resource_config"
          label={t('model_center.label_resource_template')}
          rules={[{ required: true, message: t('model_center.msg_required') }]}
        >
          <ResourceConfig
            isTrustedCenter={true}
            defaultResourceType={ResourceTemplateType.CUSTOM}
            isIgnoreFirstRender={isReceiver}
          />
        </Form.Item>
      </section>
    );
  }

  function renderFooterButton() {
    let submitText = '提交并申请';
    if (isPeerUnauthorized) {
      submitText = '确认授权';
    } else if (isEdit) {
      submitText = '保存并执行';
    }

    return (
      <>
        {!isReceiver && !isEdit && (
          <TitleWithIcon
            title={t('trusted_center.msg_trusted_computing_create')}
            isLeftIcon={true}
            isShowIcon={true}
            icon={IconInfoCircle}
          />
        )}
        <Space>
          {isPeerUnauthorized || !isEdit ? (
            <></>
          ) : (
            <Button type="primary" onClick={() => formInstance.submit()}>
              保存
            </Button>
          )}
          <Button
            type="primary"
            disabled={
              isEdit &&
              !isPeerUnauthorized &&
              (trustedJobGroup?.status !== TrustedJobGroupStatus.SUCCEEDED ||
                trustedJobGroup?.auth_status !== AuthStatus.AUTHORIZED ||
                trustedJobGroup?.unauth_participant_ids?.length !== 0)
            }
            onClick={() => {
              if (isEdit && !isPeerUnauthorized) {
                toggleIsLaunch();
              }
              formInstance.submit();
            }}
          >
            {submitText}
          </Button>
          <ButtonWithModalConfirm
            isShowConfirmModal={isFormValueChanged}
            onClick={goBackToListPage}
          >
            {t('cancel')}
          </ButtonWithModalConfirm>
        </Space>
      </>
    );
  }

  async function onSubmit() {
    if (!projectId) {
      return Message.error(t('select_project_notice'));
    }
    // validate params
    const self_dataset_info = formInstance.getFieldValue('self_dataset_info');
    const participant_datasets: ParticipantDataset[] = [];
    const participantParams: any = formInstance.getFieldValue('participant');
    // self and participants dataset empty
    if (!self_dataset_info && !participantParams) {
      Message.warning('我方数据集及合作伙伴数据集不能全为空！');
      return;
    }
    participantList.forEach((item) => {
      const dataset_info = participantParams?.[item.id]?.dataset_info || {};
      if (Object.keys(dataset_info).length === 0) {
        return;
      }
      participant_datasets.push({
        participant_id: item.id,
        name: dataset_info.name,
        uuid: dataset_info.uuid,
      });
    });
    const resource = formInstance.getFieldValue('resource_config') as ResourceConfigValue;

    if (isEdit) {
      // edit
      const payload = {
        comment: formInstance.getFieldValue('comment'),
        algorithm_uuid: isReceiver
          ? undefined
          : (formInstance.getFieldValue('algorithm_info') as AlgorithmSelectValue).algorithmUuid,
        resource: {
          cpu: parseInt(resource.worker_cpu?.replace('m', '') || ''),
          memory: parseInt(resource.worker_mem?.replace('Gi', '') || ''),
          replicas: parseInt(resource.worker_replicas || ''),
        },
        auth_status: isReceiver ? AuthStatus.AUTHORIZED : undefined,
      } as TrustedJobGroupPayload;

      const [res, error] = await to(updateTrustedJobGroup(projectId, params.id, payload));
      if (error) {
        Message.error(error.message);
        return;
      }
      if (res.data) {
        if (isPeerUnauthorized) {
          Message.success('授权成功');
        } else {
          Message.success('编辑成功');
        }
        // launch trusted computing group
        if (isLaunch) {
          launchTrustedJobGroup(projectId, params.id, { comment: '' }).catch((error) => {
            Message.error(error.message);
          });
        }
        history.push('/trusted-center/list');
        return;
      }
    } else {
      // create
      const payload = {
        name: formInstance.getFieldValue('name'),
        comment: formInstance.getFieldValue('comment'),
        algorithm_uuid: (formInstance.getFieldValue('algorithm_info') as AlgorithmSelectValue)
          .algorithmUuid,
        dataset_id: self_dataset_info ? self_dataset_info.id : undefined,
        participant_datasets: participant_datasets,
        resource: {
          cpu: parseInt(resource.worker_cpu?.replace('m', '') || ''),
          memory: parseInt(resource.worker_mem?.replace('Gi', '') || ''),
          replicas: parseInt(resource.worker_replicas || ''),
        },
      } as TrustedJobGroupPayload;

      const [res, error] = await to(createTrustedJobGroup(projectId, payload));
      if (error) {
        Message.error(error.message);
        return;
      }
      if (res.data) {
        Message.success(t('trusted_center.msg_create_success'));
        history.push('/trusted-center/list');
        return;
      }
    }
  }

  function goBackToListPage() {
    history.push(routeMaps.TrustedJobGroupList);
  }

  function onFormChange(_: Partial<TrustedJobGroupPayload>, values: TrustedJobGroupPayload) {
    setFormData(values);
  }
};

export default TrustedJobGroupForm;
