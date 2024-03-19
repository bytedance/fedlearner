import React from 'react';
import { isNil } from 'lodash-es';
import store from 'store2';

import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';

import {
  Python,
  Javascript,
  Default,
  Config,
  Yaml,
  Json,
  GitIgnore,
  Markdown,
} from 'components/IconPark';
import { FileData, FileDataNode } from 'components/FileExplorer';

import { ValueType } from 'typings/settings';
import { FileTreeNode } from 'typings/algorithm';

/**
 * @param time time in ms
 */
export function sleep(time: number): Promise<null> {
  return new Promise((resolve) => {
    setTimeout(resolve, time);
  });
}

/**
 * Run callback at next event loop,
 */
export function nextTick(cb: Function) {
  return setTimeout(() => {
    cb();
  }, 0);
}

/**
 * Convert value to css acceptable stuffs
 * @param val e.g. 10, '10%', '1.2em'
 * @param unit e.g. px, %, em...
 */
export function convertToUnit(val: any, unit = 'px'): string {
  if (isNil(val) || val === '') {
    return '0';
  } else if (isNaN(val)) {
    return String(val);
  } else {
    return `${Number(val)}${unit}`;
  }
}

/**
 * Resolve promise inline
 */
export async function to<T, E = Error>(promise: Promise<T>): Promise<[T, E]> {
  try {
    const ret = await promise;
    return [ret, (null as unknown) as E];
  } catch (e) {
    return [(null as unknown) as T, e];
  }
}

export const weakRandomKeyCache = new Map<Symbol, string>();
/**
 * Give a random string base on Math.random,
 * cache mechanism will be involved if a symbol is provided
 */
export function giveWeakRandomKey(symbol?: Symbol): string {
  if (symbol) {
    if (weakRandomKeyCache.has(symbol)) {
      return weakRandomKeyCache.get(symbol)!;
    }

    const ret = giveWeakRandomKey();
    weakRandomKeyCache.set(symbol, ret);
    return ret;
  }

  return Math.random().toString(16).slice(2);
}

type ScriptStatus = 'loading' | 'idle' | 'ready' | 'error';
/* istanbul ignore next */
export function loadScript(src: string): Promise<{ status: ScriptStatus; error?: Error }> {
  return new Promise((resolve, reject) => {
    if (!src) {
      resolve({ status: 'idle' });
      return;
    }

    // Fetch existing script element by src
    // It may have been added by another intance of this util
    let script = document.querySelector(`script[src="${src}"]`) as HTMLScriptElement;

    if (!script) {
      // Create script
      script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.setAttribute('data-status', 'loading');
      // Add script to document body
      document.body.appendChild(script);

      // Store status in attribute on script
      // This can be read by other instances of this hook
      const setAttributeFromEvent = (event: Event) => {
        const status = event.type === 'load' ? 'ready' : 'error';
        script.setAttribute('data-status', status);
      };

      script.addEventListener('load', setAttributeFromEvent);
      script.addEventListener('error', setAttributeFromEvent);
    } else {
      // Grab existing script status from attribute and set to state.
      resolve({ status: script.getAttribute('data-status') as any });
    }

    // Script event handler to update status in state
    // Note: Even if the script already exists we still need to add
    // event handlers to update the state for *this* hook instance.
    const setStateFromEvent = (event: Event) => {
      const status = event.type === 'load' ? 'ready' : 'error';
      if (event.type === 'load') {
        resolve({ status });
      } else {
        reject({ status, error: event });
      }
    };

    // Add event listeners
    script.addEventListener('load', setStateFromEvent);
    script.addEventListener('error', setStateFromEvent);
  });
}

/**
 * Copy to the clipboard (only for PC, no mobile adaptation processing has been done yet) \nstr \nThe string to be copied\nIs the copy successful?
 *
 * @param {String} str need copied
 * @return {Boolean} is success?
 */
/* istanbul ignore next */
export async function copyToClipboard(str: string) {
  str = str.toString();

  const inputEl = document.createElement('textArea') as HTMLTextAreaElement;
  let copyOk = false;

  inputEl.value = str;
  document.body.append(inputEl);
  inputEl.select();

  try {
    copyOk = document.execCommand('Copy');
  } catch (e) {
    return Promise.reject(e);
  }

  document.body.removeChild(inputEl);
  return Promise.resolve(copyOk);
}

/* istanbul ignore next */
export async function newCopyToClipboard(str: string) {
  if (!navigator.clipboard) {
    return await copyToClipboard(str);
  }
  return navigator.clipboard.writeText(str);
}

export function saveBlob(blob: Blob, fileName: string) {
  const a = document.createElement('a');
  a.href = window.URL.createObjectURL(blob);
  a.download = fileName;
  a.dispatchEvent(new MouseEvent('click'));
}

/**
 * Replace special characters in regular expressions, preceded by \
 */
export const transformRegexSpecChar = (str: string) => {
  const specCharList = ['\\', '*', '.', '?', '+', '$', '^', '[', ']', '(', ')', '{', '}', '|', '/'];
  let resultString = str;
  specCharList.forEach((char) => {
    resultString = resultString.replace(char, `\\${char}`);
  });
  return resultString;
};

/**
 * Format object to array, support custom order
 * @example
 * from
 * {
 *    'key1': 1,
 *    'key2': 2,
 * }
 *
 * to
 * [
 *  {
 *   label: 'key1',
 *   value: 1,
 *  }
 *  {
 *   label: 'key2',
 *   value: 2,
 *  }
 * ]
 */
export function formatObjectToArray<T = any>(
  map: {
    [key: string]: T;
  },
  orderKeyList?: string[],
): Array<{
  label: string;
  value: T | null;
}> {
  const tempMap = { ...map };

  const result: {
    label: string;
    value: T | null;
  }[] = [];

  if (orderKeyList && orderKeyList.length > 0) {
    orderKeyList.forEach((key) => {
      if (!Object.prototype.hasOwnProperty.call(tempMap, key)) return;
      const value = tempMap[key];
      delete tempMap[key];
      result.push({
        label: key,
        value,
      });
    });
  }

  Object.keys(tempMap).forEach((key) => {
    const value = map[key];
    result.push({
      label: key,
      value,
    });
  });

  return result;
}

/**
 * Format object string to JSON with space
 */
export function formatJSONValue(str: string, space: string | number | undefined = 2) {
  try {
    const value = JSON.stringify(JSON.parse(str), null, space);
    return value;
  } catch (error) {
    return str;
  }
}

/**
 * Format value to string
 */
export const formatValueToString = (value: any, valueType?: ValueType) => {
  if (isNil(value)) {
    return '';
  }

  if (valueType === 'OBJECT' || valueType === 'LIST') {
    if (value) {
      return JSON.stringify(value);
    }
  }

  return String(value);
};

/**
 * Parse value from string
 */
export const parseValueFromString = (value: string, valueType?: ValueType) => {
  if (valueType === 'OBJECT' || valueType === 'LIST' || valueType === 'CODE') {
    try {
      let tempValue = value;
      // Parse twice-JSON-stringified string, e.g. <FeatureSelect /> 's value
      while (typeof tempValue === 'string') {
        tempValue = JSON.parse(tempValue);
      }
      return tempValue;
    } catch (error) {
      throw error;
    }
  }

  if (valueType === 'INT' || valueType === 'NUMBER') {
    if (value === '') {
      return null;
    }
    const res = Number(value);
    if (isNaN(res)) {
      throw new Error('数字格式不正确');
    }
    return res;
  }

  if (valueType === 'BOOL' || valueType === 'BOOLEAN') {
    if (['True', 'true', '1'].includes(value)) {
      return true;
    }
    if (['False', 'false', '0'].includes(value)) {
      return false;
    }
    throw new Error('BOOL格式不正确');
  }

  return value;
};

/**
 * Get a random integer between min and max
 */
export function getRandomInt(min = 1, max = 10) {
  if (min > max) {
    throw new Error('Min is not allowed to be greater than max!!!');
  }

  min = Math.ceil(min);
  max = Math.floor(max);
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Is string is can be parse
 */
export const isStringCanBeParsed = (value: string) => {
  try {
    JSON.parse(value);
    return true;
  } catch (error) {
    return false;
  }
};
/**
 * Flatten array
 * @param {array} array
 */
export function flatten<T extends Array<any>>(array: T): T {
  return array.reduce(
    (acc, cur) => (Array.isArray(cur) ? [...acc, ...flatten(cur)] : [...acc, cur]),
    [],
  );
}

/**
 * Depth First Search
 * @param {object} node node
 * @param {function} filter filter function
 * @param {string} childFieldName children field name
 */
export function dfs<
  T extends {
    [key: string]: any;
  }
>(
  node: T,
  filter = (node: T, currentLevel: number) => true,
  childFieldName = 'children',
  currentLevel = 1,
): T[] {
  let resultList = [];

  if (node[childFieldName] && node[childFieldName].length > 0) {
    resultList = node[childFieldName].map((item: any) =>
      dfs(item, filter, childFieldName, currentLevel + 1),
    );
  }

  if (filter(node, currentLevel)) {
    resultList.unshift(node);
  }

  return flatten(resultList);
}

export const fileExtToIconMap: {
  [ext: string]: React.ReactNode;
} = {
  py: <Python />,
  python: <Python />,
  js: <Javascript />,
  javascript: <Javascript />,
  default: <Default />,
  yml: <Yaml />,
  yaml: <Yaml />,
  json: <Json />,
  config: <Config />,
  md: <Markdown />,
  gitignore: <GitIgnore />,
};

/**
 * Format non-nested style to nested tree style
 * @example
 * from
 * {
 *    'main.py':'code...',
 *    'leader/main.py':'code...',
 *    'leader/test.py':'code...'
 * }
 *
 * to
 * [
 *  {
 *   title:'main.py',
 *   key:'main.py',
 *   parentKey: '',
 *   isLeaf:true,
 *   code:'code...',
 *   icon:<Python />,
 *   fileExt:'py',
 *   children:[],
 *   isFolder:false
 *  }
 *  {
 *   title:'leader',
 *   key:'leader/',
 *   isFolder:true
 *   children:[
 *    {
 *      title:'main.py',
 *      key:'leader/main.py',
 *      parentKey:'leader',
 *      isLeaf:true,
 *      code:'code...',
 *      icon:<Python />,
 *      fileExt:'py',
 *      children:[],
 *      isFolder:false
 *    },
 *    ...
 *   ]
 *  }
 * ]
 */
export function formatTreeData(filePathToCodeMap: FileData): FileDataNode[] {
  const result: any = [];
  const level = { result };

  Object.keys(filePathToCodeMap).forEach((filePath) => {
    const code = filePathToCodeMap[filePath];
    const filePathList = filePath.split('/');

    let tempKey = '';
    filePathList.reduce((sum: any, fileNameOrFolderName: string, index: number) => {
      const parentKey = tempKey;
      tempKey += `${fileNameOrFolderName}/`;
      if (!sum[fileNameOrFolderName]) {
        sum[fileNameOrFolderName] = { result: [] };
        const isLastIndex = index === filePathList.length - 1;
        const tempData: FileDataNode = {
          title: fileNameOrFolderName,
          key: tempKey.slice(0, -1),
          children: sum[fileNameOrFolderName].result,
          parentKey: parentKey.slice(0, -1),
          isFolder: true,
          isLeaf: isLastIndex
            ? !Object.keys(filePathToCodeMap).some((innerPath) => {
                // Case: filePathToCodeMap = { main: null, 'main/test.py': '1' }
                // Because it is a file under 'main' folder, so 'main' folder isn't leaf node
                return innerPath.startsWith(tempKey);
              })
            : false,
        };

        // If code !== null, it will be treated as file
        if (isLastIndex && code !== null) {
          const extList =
            fileNameOrFolderName.indexOf('.') > -1 ? fileNameOrFolderName.split('.') : [];
          const fileExt = extList && extList.length > 0 ? extList[extList.length - 1] : '';
          tempData.icon = fileExtToIconMap[fileExt] || fileExtToIconMap['default'];
          tempData.code = code;
          tempData.isLeaf = true;
          tempData.fileExt = fileExt;
          tempData.isFolder = false;
        }
        sum.result.push(tempData);
      }

      return sum[fileNameOrFolderName];
    }, level);

    tempKey = '';
  });
  return result;
}

/**
 * Get first file node,it will ignore folder
 * @param {FileDataNode[]} formattedTreeData
 */
export function getFirstFileNode(formattedTreeData: FileDataNode[]): FileDataNode | null {
  let node = null;

  for (let index = 0; index < formattedTreeData.length; index++) {
    const currentNode = formattedTreeData[index];

    if (!currentNode.isFolder) {
      node = currentNode;
      break;
    }

    // Recursion, children
    node = getFirstFileNode(currentNode.children ?? []);

    // If find target node,then stop recursion
    if (node) {
      break;
    }
  }

  return node;
}

/**
 * Format file tree node(Back-end format in algorithms api) to file data node(Front-end format in <FileExplorer/>)
 * @example
 * from
 * {
    filename: 'main.py',
    path: 'main.py',
    size: 96,
    mtime: 1637141275,
    is_directory: false,
    files: []
 * }
 *
 * to
 * {
    title: 'main.py',
    key: 'main.py',
    parentKey: '',
    isLeaf: true,
    code: '',
    icon: fileExtToIconMap['py'],
    fileExt: 'py',
    children: [],
    isFolder: false
 * }
 */
export function formatFileTreeNodeToFileDataNode(fileTreeNode: FileTreeNode): FileDataNode {
  const pathList = fileTreeNode.path.split('/').filter((item) => item);
  const extList = fileTreeNode.filename.indexOf('.') > -1 ? fileTreeNode.filename.split('.') : [];
  const fileExt = extList.length > 0 ? extList[extList.length - 1] : '';

  return {
    title: fileTreeNode.filename,
    key: fileTreeNode.path,
    parentKey: pathList.length > 1 ? pathList.slice(0, -1).join('/') : '',
    isFolder: fileTreeNode.is_directory,
    isLeaf: fileTreeNode.files.length === 0,
    code: fileTreeNode.is_directory ? null : '',
    fileExt,
    icon: fileExtToIconMap[fileExt] || fileExtToIconMap['default'],
    children: fileTreeNode.files.map((item) => formatFileTreeNodeToFileDataNode(item)),
  };
}
export function formatFileTreeNodeListToFileDataNodeList(
  fileTreeNodeList: FileTreeNode[],
): FileDataNode[] {
  return fileTreeNodeList.map((item) => formatFileTreeNodeToFileDataNode(item));
}

/**
 * Format file tree node(Back-end format in algorithms api) to file data (Front-end format in <FileExplorer/>)
 * @example
 * from
 * {
    title: 'follower',
    key: 'follower',
    parentKey: '',
    isFolder: true,
    isLeaf: false,
    code: null,
    icon: fileExtToIconMap['default'],
    fileExt: '',
    children: [
      {
        title: 'main.py',
        key: 'follower/main.py',
        parentKey: 'follower',
        isLeaf: true,
        code: '',
        icon: fileExtToIconMap['py'],
        fileExt: 'py',
        children: [],
        isFolder: false,
      },
      {
        title: 'subfolder',
        key: 'follower/subfolder',
        parentKey: 'follower',
        isLeaf: false,
        code: null,
        icon: fileExtToIconMap['default'],
        fileExt: '',
        isFolder: true,
        children: [
          {
            title: 'test.js',
            key: 'follower/subfolder/test.js',
            parentKey: 'follower/subfolder',
            isLeaf: true,
            code: '',
            icon: fileExtToIconMap['js'],
            fileExt: 'js',
            children: [],
            isFolder: false,
          },
        ],
      },
    ],
 * }
 *
 * to
 * {
    'follower/main.py': '',
    'follower/subfolder/test.js': '',
 * }
 */
export function formatFileTreeNodeToFileData(fileTreeNode: FileTreeNode): FileData {
  const finalFileData: FileData = {};
  dfs(
    fileTreeNode,
    (node) => {
      if (node.files.length === 0) {
        finalFileData[node.path] = node.is_directory ? null : '';
      }
      return false;
    },
    'files',
  );
  return finalFileData;
}
export function formatFileTreeNodeListToFileData(fileTreeNodeList: FileTreeNode[]): FileData {
  const finalFileData: FileData = {};
  fileTreeNodeList.forEach((fileTreeNode) => {
    dfs(
      fileTreeNode,
      (node) => {
        // 将所有的pathKey都进行储存，防止一次性删除多层级空目录的情况
        // if (node.files.length === 0) {
        //   finalFileData[node.path] = node.is_directory ? null : '';
        // }
        finalFileData[node.path] = node.is_directory ? null : '';
        return false;
      },
      'files',
    );
  });

  return finalFileData;
}

/**
 * Format file ext to full language that Monaco Editor will be receive
 * @param language
 * @returns formatted language
 */
export function formatLanguage(language: string) {
  if (language === 'py') {
    return 'python';
  }
  if (language === 'js') {
    return 'javascript';
  }
  if (language === 'yml') {
    return 'yaml';
  }

  if (language === 'sh') {
    return 'shell';
  }

  return language;
}

/**
 * Get jwt headers
 * @returns {object} headers { 'Authorization': string, 'x-pc-auth': string }
 */
export function getJWTHeaders() {
  const accessToken = store.get(LOCAL_STORAGE_KEYS.current_user)?.access_token;
  const tempAccessToken = store.get(LOCAL_STORAGE_KEYS.temp_access_token);
  const { ssoName, ssoType } = store.get(LOCAL_STORAGE_KEYS.sso_info) ?? {};

  let finalAccessToken = accessToken;

  // 1. If tempAccessToken is existed, then override accessToken
  // 2. tempAccessToken will be assigned in views/TokenCallback/index.tsx
  if (tempAccessToken) {
    finalAccessToken = tempAccessToken;
  }

  const headers: {
    Authorization?: string;
    'x-pc-auth'?: string;
  } = {};

  if (finalAccessToken) {
    headers.Authorization = `Bearer ${finalAccessToken}`;
  }

  if (ssoName && ssoType && finalAccessToken) {
    // Custom HTTP header, format like x-pc-auth: <sso_name> <type> <credentials>
    headers['x-pc-auth'] = `${ssoName} ${ssoType} ${finalAccessToken}`;
  }
  return headers;
}

/**
 * Convert CPU unit, Core to M
 * @example convertCpuCoreToM(1, false) => 1000, convertCpuCoreToM("2Core", true) => "2000m"
 */
export function convertCpuCoreToM(core: number | string, withUnit: true): string;
export function convertCpuCoreToM(core: number | string, withUnit?: false): number;
export function convertCpuCoreToM(core: number | string, withUnit = false): number | string {
  let numberCore = 0;

  if (typeof core === 'number') {
    numberCore = core;
  }
  if (typeof core === 'string') {
    numberCore = parseFloat(core);
  }

  const result = numberCore * 1000;

  return withUnit ? result + 'm' : result;
}

/**
 * Convert CPU unit, M to Core
 * @example convertCpuCoreToM(1000, false) => 1, convertCpuCoreToM("2000m", true) => "2Core"
 */
export function convertCpuMToCore(core: number | string, withUnit: true): string;
export function convertCpuMToCore(core: number | string, withUnit?: false): number;
export function convertCpuMToCore(core: number | string, withUnit = false): number | string {
  let number = 0;

  if (typeof core === 'number') {
    number = core;
  }
  if (typeof core === 'string') {
    number = parseFloat(core);
  }

  const result = number / 1000;

  return withUnit ? result + 'Core' : result;
}
