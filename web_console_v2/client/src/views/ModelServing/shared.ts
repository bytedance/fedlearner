/* istanbul ignore file */

import { Message } from '@arco-design/web-react';
import { updateModelServing_new } from 'services/modelServing';

import { ModelDirectionType, ModelServing, ModelServingState } from 'typings/modelServing';
import { handleScaleEdit } from './ServiceInstanceScaleDrawer';
import { ActionItem, StateTypes } from 'components/StateIndicator';
import { editService } from './ServiceEditModal';
import { FilterOp } from 'typings/filter';

export const modelDirectionTypeToTextMap = {
  [ModelDirectionType.HORIZONTAL]: '横向联邦',
  [ModelDirectionType.VERTICAL]: '纵向联邦',
};

export const modelServingStateToTextMap = {
  [ModelServingState.AVAILABLE]: '运行中',
  [ModelServingState.LOADING]: '部署中',
  [ModelServingState.UNLOADING]: '删除中',
  [ModelServingState.UNKNOWN]: '异常',
  [ModelServingState.PENDING_ACCEPT]: '待合作伙伴配置',
  [ModelServingState.WAITING_CONFIG]: '待合作伙伴配置',
  [ModelServingState.DELETED]: '异常',
};

// 打开修改服务实例数的 drawer，并处理 UI 和业务逻辑
export async function updateServiceInstanceNum(service: ModelServing, onUpdate: () => void) {
  handleScaleEdit(service, async (instanceNum: number) => {
    try {
      await updateModelServing_new(service.project_id, service.id, {
        model_type: undefined, // 后端暂时不支持 model_type 字段
        resource: {
          ...service.resource,
          replicas: instanceNum,
        },
      });
      onUpdate();
    } catch (e) {
      Message.error(e.message);
      throw e;
    }
  });
}

export function getDotState(
  modelServing: ModelServing,
): { type: StateTypes; text: string; tip?: string; actionList?: ActionItem[] } {
  const text = modelServingStateToTextMap[modelServing.status] || '异常';

  if (modelServing.status === ModelServingState.AVAILABLE) {
    return {
      text,
      type: 'success',
    };
  }
  if (modelServing.status === ModelServingState.LOADING) {
    return {
      text,
      type: 'processing',
    };
  }

  if (modelServing.status === ModelServingState.UNLOADING) {
    return {
      text,
      type: 'gold',
    };
  }

  if (modelServing.status === ModelServingState.UNKNOWN) {
    return {
      text,
      type: 'error',
    };
  }

  if (modelServing.status === ModelServingState.PENDING_ACCEPT) {
    return {
      text,
      type: 'pending_accept',
    };
  }

  if (modelServing.status === ModelServingState.WAITING_CONFIG) {
    return {
      text,
      type: 'pending_accept',
    };
  }

  if (modelServing.status === ModelServingState.DELETED) {
    return {
      text,
      type: 'deleted',
      tip: '对侧已经删除',
    };
  }

  return {
    text,
    type: 'error',
  };
}

export function handleServiceEdit(record: ModelServing) {
  return new Promise((resolve, reject) => {
    editService(record, async (params: any) => {
      try {
        await updateModelServing_new(record.project_id, record.id, params);
        Message.success('修改成功');
        resolve(params);
      } catch (error) {
        Message.error(error.message);
        reject(error);
      }
    });
  });
}

export function getTableFilterValue(val: string): string[] {
  if (typeof val === 'undefined') {
    return [];
  }
  return [val];
}

export function cpuIsCpuM(cpu: string): boolean {
  const regx = new RegExp('[0-9]+m$');
  return regx.test(cpu);
}

export function memoryIsMemoryGi(memory: string): boolean {
  const regx = new RegExp('[0-9]+Gi$');
  return regx.test(memory);
}

export const FILTER_SERVING_OPERATOR_MAPPER = {
  name: FilterOp.EQUAL,
  keyword: FilterOp.CONTAIN,
};
