import React, { FC } from 'react';
import styled from './SlotLinkAnchor.module.less';
import {
  definitionsStore,
  editorInfosStore,
  JobDefinitionForm,
  TPL_GLOBAL_NODE_UUID,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { JobSlotReferenceType } from 'typings/workflow';
import { Tag } from '@arco-design/web-react';
import PubSub from 'pubsub-js';
import { COMPOSE_DRAWER_CHANNELS, InspectPayload } from '../../index';
import { AnchorIcon } from '../../elements';

export enum SlotLinkType {
  Self,
  OtherJob,
}

export type SlotLink = {
  type: SlotLinkType;
  jobUuid: string;
  slotName: string;
};

type Props = {
  link: SlotLink;
};

export function collectSlotLinks(
  currNodeUuid?: string,
  varUuid?: string,
  context?: { formData?: JobDefinitionForm },
) {
  if (!varUuid || !currNodeUuid) return [];

  const refSourceList: SlotLink[] = [];

  editorInfosStore.entries.forEach(([nodeUuid, editInfo]) => {
    if (!editInfo) return;

    const { slotEntries } = editInfo;

    /** If current node is workflow global variables */
    if (currNodeUuid === TPL_GLOBAL_NODE_UUID) {
      slotEntries.forEach(([slotName, slot]) => {
        if (slot.reference_type === JobSlotReferenceType.WORKFLOW) {
          if (_isVarMatched(slot.reference, varUuid)) {
            refSourceList.push({
              type: SlotLinkType.OtherJob,
              jobUuid: nodeUuid,
              slotName,
            });
          }
        }
      });
      return;
    }

    /** If current editorInfo belongs to current node */
    if (currNodeUuid === nodeUuid) {
      context?.formData?._slotEntries?.forEach(([slotName, slot]) => {
        if (slot.reference_type === JobSlotReferenceType.SELF) {
          if (_isVarMatched(slot.reference, varUuid)) {
            refSourceList.push({
              type: SlotLinkType.Self,
              jobUuid: nodeUuid,
              slotName,
            });
          }
        }
      });
      return;
    }

    slotEntries.forEach(([slotName, slot]) => {
      if (slot.reference_type === JobSlotReferenceType.OTHER_JOB) {
        if (_isVarMatched(slot.reference, varUuid) && _isJobMatched(slot.reference, currNodeUuid)) {
          refSourceList.push({
            type: SlotLinkType.OtherJob,
            jobUuid: nodeUuid,
            slotName,
          });
        }
      }
    });
  });

  return refSourceList;
}

const SlotLinkAnchor: FC<Props> = ({ link }) => {
  const isOtherJob = link.type === SlotLinkType.OtherJob;

  return (
    <div className={styled.container} onClick={onLinkClick}>
      <div>
        {link.type === SlotLinkType.Self && <Tag>本任务</Tag>}
        {isOtherJob && (
          <Tag color="magenta">{definitionsStore.getValueById(link.jobUuid)?.name}</Tag>
        )}
        {link.slotName}
      </div>
      <AnchorIcon />
    </div>
  );

  function onLinkClick() {
    PubSub.publish(COMPOSE_DRAWER_CHANNELS.inspect, {
      jobUuid: link.jobUuid,
      slotName: link.slotName,
    } as InspectPayload);
  }
};

function _isVarMatched(ref: string, varUuid: string) {
  if (!ref) return false;
  return ref.endsWith(`.${varUuid}`);
}

function _isJobMatched(ref: string, uuid: string) {
  if (!ref) return false;

  const fragments = ref.split('.');
  if (fragments.length !== 5) return false;

  const [, , jobUuid] = fragments;
  return jobUuid === uuid;
}

export default SlotLinkAnchor;
