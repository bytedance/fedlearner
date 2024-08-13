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

export const put = (config: AxiosRequestConfig) => {
  const path = config.data.get('path');
  const fileName = config.data.get('filename');
  const content = config.data.get('file');
  const finalFile: FileContent = {
    path: path,
    filename: fileName,
    content: content,
  };

  return {
    data: {
      data: finalFile,
    },
    status: 200,
  };
};

export const post = (config: AxiosRequestConfig) => {
  const path = config.data.get('path');
  const fileName = config.data.get('filename');
  const finalFile: Omit<FileContent, 'content'> = {
    path: path,
    filename: fileName,
  };

  return {
    data: {
      data: finalFile,
    },
    status: 200,
  };
};

export const patch = {
  data: {
    data: null,
  },
  status: 200,
};
export const DELETE = {
  data: {
    data: null,
  },
  status: 200,
};
export default get;
