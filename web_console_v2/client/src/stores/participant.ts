import { Message } from '@arco-design/web-react';
import { atom, selector, atomFamily } from 'recoil';
import { fetchParticipants } from 'services/participant';
import { ConnectionStatus, ConnectionStatusType } from 'typings/participant';

export const forceReloadParticipantList = atom({
  key: 'ForceReloadParticipantList',
  default: 0,
});

export const participantListQuery = selector({
  key: 'FetchParticipantList',
  get: async ({ get }) => {
    get(forceReloadParticipantList);

    try {
      const res = await fetchParticipants();

      return res.data;
    } catch (error: any) {
      Message.info(error.message);
    }
  },
});

export const participantConnectionState = atomFamily<ConnectionStatus, ID>({
  key: 'ParticipantConnectionState',
  default: { success: ConnectionStatusType.Fail, message: '', application_version: {} },
});
