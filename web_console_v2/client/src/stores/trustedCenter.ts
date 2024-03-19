import { atom } from 'recoil';
import { ParticipantDataset } from 'typings/dataset';
import { AuthStatus, TrustedJobResource } from 'typings/trustedCenter';

export type TrustedJbGroupForm = {
  name: string;
  comment: string;
  algorithm_id?: ID;
  dataset_id?: ID;
  participant_datasets?: ParticipantDataset[];
  auth_status?: AuthStatus;
  resource?: TrustedJobResource;
};

export const trustedJobGroupForm = atom<TrustedJbGroupForm>({
  key: 'TrustedJbGroupForm',
  default: {
    name: '',
    comment: '',
    algorithm_id: undefined,
    dataset_id: undefined,
    participant_datasets: undefined,
    auth_status: undefined,
    resource: undefined,
  },
});
