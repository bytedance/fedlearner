import {
  getOperationRecordList,
  addOperationRecord,
  deleteOperationRecord,
  editOperationRecord,
  renameOperationRecord,
} from './operationRecord';

import { OperationRecord, OperationType } from 'typings/algorithm';

const testNameList = ['main.py', 'folder1', 'folder1/f1.py', 'folder2'];
const testContent = '# coding: utf-8\n';

const addRecordList: OperationRecord[] = [];
const deleteRecordList: OperationRecord[] = [];
const editRecordList: OperationRecord[] = [];
const renameRecordList: OperationRecord[] = [];

testNameList.forEach((name) => {
  const isFolder = name.indexOf('.') === -1;

  addRecordList.push({
    path: name,
    content: '',
    type: OperationType.ADD,
    isFolder,
  });
  deleteRecordList.push({
    path: name,
    content: testContent,
    type: OperationType.DELETE,
    isFolder,
  });
  editRecordList.push({
    path: name,
    content: testContent,
    type: OperationType.EDIT,
    isFolder,
  });
  renameRecordList.push({
    path: name,
    content: '',
    type: OperationType.RENAME,
    isFolder,
    newPath: 'no-main.py',
  });
});

describe('AddOperationRecord', () => {
  it('Empty operation record list', () => {
    expect(addOperationRecord([], addRecordList[0], false)).toEqual([addRecordList[0]]);
    expect(addOperationRecord([], addRecordList[0], true)).toEqual([
      { ...addRecordList[0], type: OperationType.EDIT },
    ]);
  });

  it('Operation record list with same path record that type is OperationType.DELETE', () => {
    expect(addOperationRecord([deleteRecordList[0]], addRecordList[0], false)).toEqual([
      { ...addRecordList[0], type: OperationType.EDIT },
    ]);
    expect(addOperationRecord([deleteRecordList[0]], addRecordList[0], true)).toEqual([
      { ...addRecordList[0], type: OperationType.EDIT },
    ]);
  });

  it('Operation record list with same path record but different isFolder type', () => {
    expect(
      addOperationRecord([{ ...addRecordList[0], isFolder: true }], addRecordList[0], false),
    ).toEqual([{ ...addRecordList[0], isFolder: true }, addRecordList[0]]);

    expect(
      addOperationRecord([{ ...addRecordList[0], isFolder: true }], addRecordList[0], true),
    ).toEqual([
      { ...addRecordList[0], isFolder: true },
      { ...addRecordList[0], type: OperationType.EDIT },
    ]);
  });

  it('Operation record list with no same path record', () => {
    expect(
      addOperationRecord(
        [addRecordList[1], addRecordList[2], addRecordList[3], editRecordList[1]],
        addRecordList[0],
        false,
      ),
    ).toEqual([
      addRecordList[1],
      addRecordList[2],
      addRecordList[3],
      editRecordList[1],
      addRecordList[0],
    ]);
  });

  it('Add existed folder', () => {
    expect(addOperationRecord([], addRecordList[1], true)).toEqual([]);
    expect(addOperationRecord([deleteRecordList[1]], addRecordList[1], true)).toEqual([]);
  });
});

describe('DeleteOperationRecord', () => {
  it('Empty operation record list', () => {
    expect(deleteOperationRecord([], deleteRecordList[0], false)).toEqual([]);
    expect(deleteOperationRecord([], deleteRecordList[0], true)).toEqual([deleteRecordList[0]]);
  });

  it('Operation record list with same path record', () => {
    expect(
      deleteOperationRecord([addRecordList[0], editRecordList[0]], deleteRecordList[0], false),
    ).toEqual([]);
    expect(
      deleteOperationRecord([addRecordList[0], editRecordList[0]], deleteRecordList[0], true),
    ).toEqual([deleteRecordList[0]]);
  });

  it('Delete folder', () => {
    expect(
      deleteOperationRecord([addRecordList[1], addRecordList[2]], deleteRecordList[1], false),
    ).toEqual([]);
    expect(
      deleteOperationRecord([addRecordList[1], addRecordList[2]], deleteRecordList[1], true),
    ).toEqual([deleteRecordList[1]]);
  });
});

describe('EditOperationRecord', () => {
  it('Empty operation record list', () => {
    expect(editOperationRecord([], editRecordList[0], false)).toEqual([
      { ...editRecordList[0], type: OperationType.ADD },
    ]);
    expect(editOperationRecord([], editRecordList[0], true)).toEqual([editRecordList[0]]);
  });

  it('Operation record list with same path record that type is OperationType.ADD', () => {
    expect(editOperationRecord([addRecordList[0]], editRecordList[0], false)).toEqual([
      { ...editRecordList[0], type: OperationType.ADD },
    ]);
    expect(editOperationRecord([addRecordList[0]], editRecordList[0], true)).toEqual([
      editRecordList[0],
    ]);
  });

  it('Operation record list with no same path record', () => {
    expect(
      editOperationRecord(
        [addRecordList[1], addRecordList[2], addRecordList[3], editRecordList[3]],
        editRecordList[0],
        false,
      ),
    ).toEqual([
      addRecordList[1],
      addRecordList[2],
      addRecordList[3],
      editRecordList[3],
      { ...editRecordList[0], type: OperationType.ADD },
    ]);

    expect(
      editOperationRecord(
        [addRecordList[1], addRecordList[2], addRecordList[3], editRecordList[3]],
        editRecordList[0],
        true,
      ),
    ).toEqual([
      addRecordList[1],
      addRecordList[2],
      addRecordList[3],
      editRecordList[3],
      editRecordList[0],
    ]);
  });

  it('Edit folder', () => {
    expect(editOperationRecord([], editRecordList[1], false)).toEqual([]);
    expect(editOperationRecord([], editRecordList[1], true)).toEqual([]);
    expect(editOperationRecord([addRecordList[1]], editRecordList[1], false)).toEqual([
      addRecordList[1],
    ]);
    expect(editOperationRecord([addRecordList[1]], editRecordList[1], true)).toEqual([
      addRecordList[1],
    ]);
  });
});

describe('RenameOperationRecord', () => {
  it('Empty operation record list', () => {
    try {
      renameOperationRecord([], renameRecordList[0], false);
    } catch (error) {
      expect(error.message).toMatch(
        'Required type === OperationType.ADD record in prev operation record list',
      );
    }
    expect(renameOperationRecord([], renameRecordList[0], true)).toEqual([renameRecordList[0]]);
  });

  it('Rename existed node in Back-end', () => {
    expect(renameOperationRecord([], renameRecordList[0], true)).toEqual([renameRecordList[0]]);
    expect(renameOperationRecord([], renameRecordList[1], true)).toEqual([renameRecordList[1]]);
    expect(renameOperationRecord([editRecordList[0]], renameRecordList[0], true)).toEqual([
      editRecordList[0],
      renameRecordList[0],
    ]);
    expect(
      renameOperationRecord(
        [addRecordList[1], addRecordList[2], addRecordList[3], editRecordList[3]],
        renameRecordList[0],
        true,
      ),
    ).toEqual([
      addRecordList[1],
      addRecordList[2],
      addRecordList[3],
      editRecordList[3],
      renameRecordList[0],
    ]);
  });

  it('Rename file when isExistedNode = false', () => {
    expect(renameOperationRecord([addRecordList[0]], renameRecordList[0], false)).toEqual([
      {
        ...addRecordList[0],
        path: renameRecordList[0].newPath,
        type: OperationType.ADD,
      },
    ]);
  });
  it('Rename folder when isExistedNode = false', () => {
    expect(
      renameOperationRecord([addRecordList[1], addRecordList[2]], renameRecordList[1], false),
    ).toEqual(
      [addRecordList[1], addRecordList[2]].map((item) => {
        const oldPathReg = new RegExp(`^${renameRecordList[1].path}`);
        return {
          ...item,
          path: item.path.replace(oldPathReg, renameRecordList[1].newPath!),
        };
      }),
    );
  });
});

describe('GetOperationRecordList', () => {
  it('When isExistedNode = false', () => {
    let prevOperationRecordList: OperationRecord[] = [];
    let resultOperationRecordList: OperationRecord[] = [];

    // Add file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      addRecordList[0],
      false,
    );
    resultOperationRecordList = [addRecordList[0]];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Then add empty folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      addRecordList[1],
      false,
    );
    resultOperationRecordList = [resultOperationRecordList[0], addRecordList[1]];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Then add file in the folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      addRecordList[2],
      false,
    );
    resultOperationRecordList = [
      resultOperationRecordList[0],
      resultOperationRecordList[1],
      addRecordList[2],
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Edit first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      editRecordList[0],
      false,
    );
    resultOperationRecordList = [
      { ...editRecordList[0], type: OperationType.ADD },
      resultOperationRecordList[1],
      resultOperationRecordList[2],
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Edit second file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      editRecordList[2],
      false,
    );
    resultOperationRecordList = [
      resultOperationRecordList[0],
      resultOperationRecordList[1],
      { ...editRecordList[2], type: OperationType.ADD },
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Rename first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      renameRecordList[0],
      false,
    );
    resultOperationRecordList = [
      {
        ...renameRecordList[0],
        type: OperationType.ADD,
        path: renameRecordList[0].newPath!,
        content: editRecordList[0].content,
        newPath: undefined,
      },
      resultOperationRecordList[1],
      resultOperationRecordList[2],
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Edit first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        path: renameRecordList[0].newPath!,
        content: '#123',
        type: OperationType.EDIT,
        isFolder: false,
      },
      false,
    );
    resultOperationRecordList = [
      {
        path: renameRecordList[0].newPath!,
        content: '#123',
        type: OperationType.ADD,
        isFolder: false,
      },
      resultOperationRecordList[1],
      resultOperationRecordList[2],
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Delete first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        path: renameRecordList[0].newPath!,
        content: '',
        type: OperationType.DELETE,
        isFolder: false,
      },
      false,
    );
    resultOperationRecordList = [resultOperationRecordList[1], resultOperationRecordList[2]];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Rename folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        ...renameRecordList[1],
        newPath: 'newFolderName',
      },
      false,
    );
    const oldPathReg = new RegExp(`^${renameRecordList[1].path}`);
    resultOperationRecordList = [
      { ...resultOperationRecordList[0], path: 'newFolderName' },
      {
        ...resultOperationRecordList[1],
        path: editRecordList[2].path.replace(oldPathReg, 'newFolderName'),
      },
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Delete folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        ...deleteRecordList[1],
        path: 'newFolderName',
      },
      false,
    );
    resultOperationRecordList = [];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);
  });

  it('When isExistedNode = true', () => {
    let prevOperationRecordList: OperationRecord[] = [];
    let resultOperationRecordList: OperationRecord[] = [];

    // Add file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      addRecordList[0],
      true,
    );
    resultOperationRecordList = [{ ...addRecordList[0], type: OperationType.EDIT }];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Then add empty folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      addRecordList[1],
      true,
    );
    expect(prevOperationRecordList).toEqual(resultOperationRecordList); // If it is existed same folder node in Back-end, don't add record

    // Then add file in the folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      addRecordList[2],
      true,
    );
    resultOperationRecordList = [
      resultOperationRecordList[0],
      { ...addRecordList[2], type: OperationType.EDIT },
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Edit first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      editRecordList[0],
      true,
    );
    resultOperationRecordList = [resultOperationRecordList[1], editRecordList[0]];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Edit second file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      editRecordList[2],
      true,
    );
    resultOperationRecordList = [resultOperationRecordList[1], editRecordList[2]];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Rename first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      renameRecordList[0],
      true,
    );
    resultOperationRecordList = [
      resultOperationRecordList[0],
      resultOperationRecordList[1],
      renameRecordList[0],
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Edit first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        path: renameRecordList[0].newPath!,
        content: '#123',
        type: OperationType.EDIT,
        isFolder: false,
      },
      true,
    );
    resultOperationRecordList.push({
      path: renameRecordList[0].newPath!,
      content: '#123',
      type: OperationType.EDIT,
      isFolder: false,
    });
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Delete first file
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        path: renameRecordList[0].newPath!,
        content: '',
        type: OperationType.DELETE,
        isFolder: false,
      },
      true,
    );
    resultOperationRecordList = [
      resultOperationRecordList[0],
      resultOperationRecordList[1],
      resultOperationRecordList[2],
      {
        path: renameRecordList[0].newPath!,
        content: '',
        type: OperationType.DELETE,
        isFolder: false,
      },
    ];
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Rename folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        ...renameRecordList[1],
        newPath: 'newFolderName',
      },
      true,
    );
    resultOperationRecordList.push({
      ...renameRecordList[1],
      newPath: 'newFolderName',
    });

    expect(prevOperationRecordList).toEqual(resultOperationRecordList);

    // Delete folder
    prevOperationRecordList = getOperationRecordList(
      prevOperationRecordList,
      {
        ...deleteRecordList[1],
        path: 'newFolderName',
      },
      true,
    );
    resultOperationRecordList.push({
      ...deleteRecordList[1],
      path: 'newFolderName',
    });
    expect(prevOperationRecordList).toEqual(resultOperationRecordList);
  });
});
