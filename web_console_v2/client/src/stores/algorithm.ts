import { atom } from 'recoil';
import {
  AlgorithmProject,
  AlgorithmReleaseStatus,
  AlgorithmStatus,
  EnumAlgorithmProjectSource,
  EnumAlgorithmProjectType,
} from 'typings/algorithm';

export const AlgorithmProjectDetail = atom<AlgorithmProject>({
  key: 'AlgorithmProjectDetail',
  default: {
    id: '',
    name: '',
    project_id: '',
    type: EnumAlgorithmProjectType.NN_LOCAL,
    source: EnumAlgorithmProjectSource.PRESET,
    creator_id: null,
    username: '',
    participant_id: null,
    path: '',
    publish_status: AlgorithmStatus.PUBLISHED,
    release_status: AlgorithmReleaseStatus.RELEASED,
    parameter: null,
    comment: null,
    latest_version: 1,
    created_at: Date.now(),
    updated_at: Date.now(),
    deleted_at: Date.now(),
  },
});
