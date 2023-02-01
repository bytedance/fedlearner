import React, { ReactElement, CSSProperties } from 'react';
import { Progress } from '@arco-design/web-react';
import {
  ParticiPantMap,
  RoleType,
  ProjectTicketStatus,
  ProjectStateType,
  ProjectAbilityType,
  ProjectActionType,
} from 'typings/project';
import { Participant, ParticipantType } from 'typings/participant';
import { FilterOp } from 'typings/filter';

import styles from './index.module.less';

export function getCoordinateName(participantsMap?: Record<string, ParticiPantMap>) {
  if (!participantsMap) {
    return undefined;
  }
  const keyList = Object.keys(participantsMap);
  const coordinate = keyList.find((item) => {
    return participantsMap?.[item].role === RoleType.COORDINATOR;
  });
  return coordinate ? participantsMap?.[coordinate].name : undefined;
}

export function getParticipantsName(participantsMap?: Record<string, ParticiPantMap>) {
  if (!participantsMap) {
    return [];
  }
  const resultParticipantsName: string[] = [];
  const keyList = Object.keys(participantsMap);
  keyList.forEach((item) => {
    if (participantsMap?.[item].role === RoleType.PARTICIPANT) {
      resultParticipantsName.push(participantsMap?.[item].name);
    }
  });

  return resultParticipantsName;
}

export const TICKET_STATUS_MAPPER: Record<ProjectTicketStatus, any> = {
  APPROVED: { status: 'default', percent: 100, name: '待授权' },
  PENDING: {
    status: 'default',
    percent: 50,
    name: '待审批',
  },
  DECLINED: {
    status: 'warning',
    percent: 50,
    name: '审批拒绝',
  },
  FAILED: {
    status: 'warning',
    percent: 100,
    name: '失败',
  },
};

export const PARTICIPANT_STATE_MAPPER: Record<ProjectStateType, any> = {
  PENDING: {
    color: 'arcoblue',
    value: '待授权',
  },
  ACCEPTED: {
    color: 'green',
    value: '已授权',
  },
  FAILED: {
    color: 'orange',
    value: '失败',
  },
  CLOSED: {
    color: 'red',
    value: '已拒绝',
  },
};

export const PARTICIPANT_TYPE_TAG_MAPPER: Record<ParticipantType, any> = {
  [ParticipantType.LIGHT_CLIENT]: {
    color: 'purple',
    label: '轻量级',
  },
  [ParticipantType.PLATFORM]: {
    color: 'arcoblue',
    label: '标准',
  },
};

export const PROJECT_TASK_LABEL_MAPPER = {
  [ProjectActionType.ID_ALIGNMENT]: 'ID对齐任务',
  [ProjectActionType.DATA_ALIGNMENT]: '横向数据对齐任务',
  [ProjectActionType.HORIZONTAL_TRAIN]: '横向联邦模型训练',
  [ProjectActionType.VERTICAL_TRAIN]: '纵向联邦模型训练',
  [ProjectActionType.VERTICAL_EVAL]: '纵向联邦模型评估',
  [ProjectActionType.VERTICAL_PRED]: '纵向联邦模型离线预测',
  [ProjectActionType.VERTICAL_SERVING]: '纵向联邦模型在线服务',
  [ProjectActionType.WORKFLOW]: '工作流任务',
  [ProjectActionType.TEE_SERVICE]: '可信分析服务',
  [ProjectActionType.TEE_RESULT_EXPORT]: '可信分析服务结果导出',
};
export const PROJECT_ABILITY_LABEL_MAPPER = {
  [ProjectAbilityType.ALWAYS_ALLOW]: '始终允许',
  [ProjectAbilityType.ONCE]: '允许一次',
  [ProjectAbilityType.MANUAL]: '发起时询问',
  [ProjectAbilityType.ALWAYS_REFUSE]: '拒绝',
};

export const PENDING_PROJECT_FILTER_MAPPER = {
  state: FilterOp.IN,
  ticket_status: FilterOp.EQUAL,
};

interface Props {
  ticketStatus: ProjectTicketStatus;
  style?: CSSProperties;
  className?: string;
}
export function ProjectProgress({ ticketStatus, style, className }: Props): ReactElement {
  const progress = TICKET_STATUS_MAPPER?.[ticketStatus];
  return (
    <div className={`${styles.progress_container} ${className}`} style={style}>
      <span className={styles.progress_name}>{progress?.name ?? '成功'}</span>
      <Progress
        percent={progress?.percent ?? 100}
        status={progress?.status ?? 'success'}
        showText={false}
        trailColor="var(--color-primary-light-1)"
      />
    </div>
  );
}

export function resetParticipantsInfo(
  participantMap: Record<string, ParticiPantMap>,
  participantList: Participant[],
  myPureDomainName: string,
) {
  const keyList = Object.keys(participantMap);
  const resultList: any[] = [];
  keyList.forEach((key: string) => {
    const participantDetail = participantList.find((item) => item.pure_domain_name === key) ?? {};
    const completeParticipant = {
      ...participantMap?.[key],
      ...participantDetail,
      pure_domain_name: key,
    };
    key !== myPureDomainName && resultList.push(completeParticipant);
  });
  const participantsList = resultList.sort((a: any, b: any) => {
    return a.name > b.name ? 1 : -1;
  });
  participantMap?.[myPureDomainName] &&
    participantsList.unshift({
      ...participantMap?.[myPureDomainName],
      pure_domain_name: myPureDomainName,
      state: ProjectStateType.ACCEPTED,
    });
  return participantsList;
}

export function resetAbilitiesTableData(
  actionRules?: Record<ProjectActionType, ProjectAbilityType>,
) {
  if (!actionRules) {
    return [];
  }
  //保证顺序不变
  const keyList = [
    ProjectActionType.ID_ALIGNMENT,
    ProjectActionType.DATA_ALIGNMENT,
    ProjectActionType.HORIZONTAL_TRAIN,
    ProjectActionType.VERTICAL_TRAIN,
    ProjectActionType.VERTICAL_EVAL,
    ProjectActionType.VERTICAL_PRED,
    ProjectActionType.VERTICAL_SERVING,
    ProjectActionType.WORKFLOW,
    ProjectActionType.TEE_SERVICE,
    ProjectActionType.TEE_RESULT_EXPORT,
  ];
  const actionRulesList: any[] = [];
  keyList.forEach((item: ProjectActionType) => {
    actionRules?.[item] && actionRulesList.push({ ability: item, rule: actionRules?.[item] });
  });
  return actionRulesList;
}
