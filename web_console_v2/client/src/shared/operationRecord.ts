import { OperationRecord, OperationType } from 'typings/algorithm';

function _removePrevNode(arr: OperationRecord[], obj: OperationRecord) {
  return arr.filter((item) => {
    return item.path !== obj.path || item.isFolder !== obj.isFolder;
  });
}

function _removeSubNode(arr: OperationRecord[], obj: OperationRecord) {
  const pathReg = new RegExp(`^${obj.path}/`);
  return arr.filter((item) => {
    return !pathReg.test(item.path);
  });
}

export function getOperationRecordList(
  prev: OperationRecord[],
  cur: OperationRecord,
  isExistedNode = false,
): OperationRecord[] {
  let finalOperationRecordList: OperationRecord[] = [];

  switch (cur.type) {
    case OperationType.ADD:
      finalOperationRecordList = addOperationRecord(prev, cur, isExistedNode);
      break;
    case OperationType.DELETE:
      finalOperationRecordList = deleteOperationRecord(prev, cur, isExistedNode);
      break;
    case OperationType.EDIT:
      finalOperationRecordList = editOperationRecord(prev, cur, isExistedNode);
      break;
    case OperationType.RENAME:
      finalOperationRecordList = renameOperationRecord(prev, cur, isExistedNode);
      break;
    default:
      break;
  }

  return finalOperationRecordList;
}

export function addOperationRecord(
  prev: OperationRecord[],
  cur: OperationRecord,
  isExistedNode = false,
): OperationRecord[] {
  // If it is existed same folder node in Back-end, don't add record
  if (isExistedNode && cur.isFolder) {
    return _removePrevNode(prev, cur);
  }

  const prevDeleteFileRecord = prev.find(
    (item) =>
      item.path === cur.path &&
      item.type === OperationType.DELETE &&
      item.isFolder === cur.isFolder &&
      !item.isFolder, // file node
  );

  /**
   * Note: change type to OperationType.EDIT
   *
   * case 1:
   *  1. delete one file
   *  2. add same name file
   *
   * case2:
   *  If it is existed same file node in Back-end
   */
  if (prevDeleteFileRecord || (isExistedNode && !cur.isFolder)) {
    return _removePrevNode(prev, cur).concat([
      {
        ...cur,
        type: OperationType.EDIT,
        content: '', // clear file content
      },
    ]);
  }

  // Just insert new record
  return [...prev, cur];
}

export function deleteOperationRecord(
  prev: OperationRecord[],
  cur: OperationRecord,
  isExistedNode = false,
): OperationRecord[] {
  // TODO: How to handle rename node?

  if (cur.isFolder) {
    // Delete all record in the folder and delete all same path record, and insert new one record if it is existed node in Back-end
    return _removeSubNode(_removePrevNode(prev, cur), cur).concat(isExistedNode ? [cur] : []);
  }

  // Delete all same path record, and insert new one record if it is existed node in Back-end
  return _removePrevNode(prev, cur).concat(isExistedNode ? [cur] : []);
}

export function editOperationRecord(
  prev: OperationRecord[],
  cur: OperationRecord,
  isExistedNode = false,
): OperationRecord[] {
  // Can't edit folder content
  if (cur.isFolder) {
    return prev;
  }

  const prevAddRecordIndex = prev.findIndex(
    (item) =>
      item.path === cur.path && item.type === OperationType.ADD && item.isFolder === cur.isFolder,
  );

  /**
   * Note: change type to OperationType.ADD
   * 1. add one file
   * 2. re-edit this file many times
   */
  if (prevAddRecordIndex > -1) {
    return [
      ...prev.slice(0, prevAddRecordIndex),
      {
        ...prev[prevAddRecordIndex],
        content: cur.content, // change content = cur.content
        type: isExistedNode ? OperationType.EDIT : OperationType.ADD,
      },
      ...prev.slice(prevAddRecordIndex + 1),
    ];
  }

  // TODO: It is necessary to call _removePrevNode?
  return _removePrevNode(prev, cur).concat([
    { ...cur, type: isExistedNode ? OperationType.EDIT : OperationType.ADD },
  ]);
}
export function renameOperationRecord(
  prev: OperationRecord[],
  cur: OperationRecord,
  isExistedNode = false,
): OperationRecord[] {
  if (isExistedNode) {
    // Just insert new record
    return [...prev, cur];
  }

  if (!Object.prototype.hasOwnProperty.call(cur, 'newPath')) {
    throw new Error('Required newPath!!!');
  }

  if (cur.isFolder) {
    const oldPathReg = new RegExp(`^${cur.path}`);

    // Replace all old path to new path in the folder
    return prev.map((item) => {
      return { ...item, path: item.path.replace(oldPathReg, cur.newPath!) };
    });
  }

  const prevAddRecordIndex = prev.findIndex(
    (item) =>
      item.path === cur.path &&
      item.type === OperationType.ADD &&
      item.isFolder === cur.isFolder &&
      !cur.isFolder,
  );

  if (prevAddRecordIndex === -1) {
    throw new Error('Required type === OperationType.ADD record in prev operation record list!!!');
  }

  return [
    ...prev.slice(0, prevAddRecordIndex),
    {
      ...prev[prevAddRecordIndex],
      path: cur.newPath!, // change old path to new path
      type: OperationType.ADD,
    },
    ...prev.slice(prevAddRecordIndex + 1),
  ];
}
