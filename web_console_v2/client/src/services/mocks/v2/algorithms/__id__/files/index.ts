import { AxiosRequestConfig } from 'axios';
import { FileContent } from 'typings/algorithm';
import { getFileInfoByFilePath } from 'shared/file';

import { leaderPythonFile, followerPythonFile } from 'services/mocks/v2/algorithms/examples';

const get = (config: AxiosRequestConfig) => {
  const { parentPath, fileName } = getFileInfoByFilePath(config.params.path);
  let finalFile: FileContent = {
    path: parentPath,
    filename: fileName,
    content: `I am ${config.params.path}`,
  };
  switch (config.params.path) {
    case 'leader/main.py':
      finalFile = leaderPythonFile;
      break;
    case 'follower/main.py':
      finalFile = followerPythonFile;
      break;
    default:
      break;
  }

  return {
    data: {
      data: finalFile,
    },
    status: 200,
  };
};

export default get;
