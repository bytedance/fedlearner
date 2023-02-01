/* istanbul ignore file */
import {
  fetchAlgorithmProjectFileTreeList,
  fetchAlgorithmProjectFileContentDetail,
  fetchAlgorithmFileTreeList,
  fetchAlgorithmFileContentDetail,
  fetchPendingAlgorithmFileTreeList,
  fetchPendingAlgorithmFileContentDetail,
  fetchPeerAlgorithmFileTreeList,
  fetchPeerAlgorithmProjectFileContentDetail,
} from 'services/algorithm';

export function getAlgorithmProjectProps(props: { id: ID }) {
  const { id } = props;

  return {
    id: id,
    isAsyncMode: true,
    getFileTreeList: () => fetchAlgorithmProjectFileTreeList(id!).then((res) => res.data || []),
    getFile: (filePath: string) =>
      fetchAlgorithmProjectFileContentDetail(id!, {
        path: filePath,
      }).then((res) => res.data.content),
  };
}
export function getAlgorithmProps(props: { id: ID }) {
  const { id } = props;

  return {
    id: id,
    isAsyncMode: true,
    getFileTreeList: () => fetchAlgorithmFileTreeList(id!).then((res) => res.data || []),
    getFile: (filePath: string) =>
      fetchAlgorithmFileContentDetail(id!, {
        path: filePath,
      }).then((res) => res.data.content),
  };
}

export function getPendingAlgorithmProps(props: { projId: ID; id: ID }) {
  const { id, projId } = props;
  return {
    id,
    isAsyncMode: true,
    getFileTreeList: () =>
      fetchPendingAlgorithmFileTreeList(projId!, id!).then((res) => res.data || []),
    getFile: (filePath: string) =>
      fetchPendingAlgorithmFileContentDetail(projId!, id!, { path: filePath }).then(
        (res) => res.data.content,
      ),
  };
}

export function getPeerAlgorithmProps(props: { projId: ID; participantId: ID; id: ID; uuid: ID }) {
  const { id, participantId, projId, uuid } = props;
  return {
    id,
    isAsyncMode: true,
    getFileTreeList: () =>
      fetchPeerAlgorithmFileTreeList(projId!, participantId, uuid!).then((res) => res.data || []),
    getFile: (filePath: string) =>
      fetchPeerAlgorithmProjectFileContentDetail(projId!, participantId, uuid!, {
        path: filePath,
      }).then((res) => res.data.content),
  };
}
