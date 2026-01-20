import React from 'react';
import { generatePath, useHistory, useParams } from 'react-router';
import { ModelJobCreateFormData, ModelJobPatchFormData } from 'typings/modelCenter';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import * as service from 'services/modelCenter';
import CreateForm from '../CreateForm';
import { useRecoilValue } from 'recoil';
import { projectState } from 'stores/project';
import routeMap, {
  ModelEvaluationListParams,
  ModelEvaluationCreateParams,
  ModelEvaluationModuleType,
} from '../../routes';
import { useQuery } from 'react-query';

const Create: React.FC = () => {
  const history = useHistory();
  const params = useParams<ModelEvaluationCreateParams & ModelEvaluationListParams>();
  const selectedProject = useRecoilValue(projectState);
  const project_id = selectedProject.current?.id;
  const { data: job } = useQuery(
    [params.id, params.action],
    () => service.fetchModelJob_new(project_id!, params.id).then((res) => res.data),
    {
      enabled: params.action === 'edit' && Boolean(project_id),
    },
  );

  return (
    <SharedPageLayout
      contentWrapByCard={false}
      title={
        <BackButton
          isShowConfirmModal={true}
          modalClassName="custom-modal"
          title={params.action === 'edit' ? `确认要退出编辑「${job?.name}」？` : '确认要退出？'}
          content={'退出后，当前所填写的信息将被清空。'}
          onClick={() => {
            history.push(
              generatePath(routeMap.ModelEvaluationList, {
                module: params.module,
              }),
            );
          }}
        >
          {params.module === ModelEvaluationModuleType.Evaluation ? '模型评估' : '离线预测'}
        </BackButton>
      }
      centerTitle={`${params.role === 'receiver' ? '授权' : '创建'}${
        params.module === ModelEvaluationModuleType.Evaluation ? '评估' : '预测'
      }`}
    >
      <CreateForm
        job={job}
        jobType={
          params.module === ModelEvaluationModuleType.Evaluation ? 'EVALUATION' : 'PREDICTION'
        }
        createReq={createReqWrapper}
        patchReq={patchReqWrapper}
      />
    </SharedPageLayout>
  );

  function createReqWrapper(config: ModelJobCreateFormData) {
    if (!project_id) {
      return Promise.reject('请选择工作区');
    }
    return service.createModelJob_new(project_id, config);
  }

  function patchReqWrapper(jobId: ID, config: ModelJobPatchFormData) {
    return service.updateModelJob_new(project_id!, jobId, config);
  }
};

export default Create;
