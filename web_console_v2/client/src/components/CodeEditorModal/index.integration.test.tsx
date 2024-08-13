import React from 'react';
import { render, fireEvent, waitFor, RenderResult, within } from '@testing-library/react';
import mock from 'xhr-mock';

import { waitForLoadingEnd } from 'shared/testUtils';
import * as api from 'services/algorithm';
import * as helpers from 'shared/helpers';
import { getFileInfoByFilePath } from 'shared/file';

import { BaseCodeEditor } from './index';
import { FileData } from 'components/FileExplorer';

import { FileTreeNode, FileContent } from 'typings/algorithm';

jest.mock('components/CodeEditor');
jest.mock('services/algorithm');

const mockApi = api as jest.Mocked<typeof api>;

const testTreeList: FileTreeNode[] = [
  {
    filename: 'owner.py',
    path: 'owner.py',
    size: 17,
    mtime: 1637141275,
    is_directory: false,
    files: [],
  },
  {
    filename: 't1.yaml',
    path: 't1.yaml',
    size: 17,
    mtime: 1637141275,
    is_directory: false,
    files: [],
  },
  {
    filename: 't2.config',
    path: 't2.config',
    size: 17,
    mtime: 1637141275,
    is_directory: false,
    files: [],
  },
  {
    filename: 't3.json',
    path: 't3.json',
    size: 17,
    mtime: 1637141275,
    is_directory: false,
    files: [],
  },
  {
    filename: 'leader',
    path: 'leader',
    size: 96,
    mtime: 1637141275,
    is_directory: true,
    files: [
      {
        filename: 'main.py',
        path: 'leader/main.py',
        size: 17,
        mtime: 1637141275,
        is_directory: false,
        files: [],
      },

      {
        filename: 'test',
        path: 'leader/test',
        size: 96,
        mtime: 1637141275,
        is_directory: true,
        files: [
          {
            filename: 't1.js',
            path: 'leader/test/t1.js',
            size: 17,
            mtime: 1637141275,
            is_directory: false,
            files: [],
          },
        ],
      },
    ],
  },
];

const testFiledata: FileData = {
  'owner.py': '# coding: utf-8',
  'leader/main.py': 'I am leader/main.py',
  'leader/test/t1.js': 'var a = 1;',
  't1.yaml': `# Get Started with Codebase CI`,
  't2.config': '# coding: utf-8',
  't3.json': '{ "a":1 }',
};

const testFileKey = 'owner.py';
const testFileContent = '# coding: utf-8';

const asyncProps = {
  id: 3,
  isAsyncMode: true,
  getFileTreeList: () => api.fetchAlgorithmProjectFileTreeList(1).then((res) => res.data),
  getFile: (filePath: string) =>
    api
      .fetchAlgorithmProjectFileContentDetail(1, {
        path: filePath,
      })
      .then((res) => res.data.content),
};

function _getFileName(fileKey: string) {
  const { fileName } = getFileInfoByFilePath(fileKey);
  return fileName;
}

describe('<BaseCodeEditor />', () => {
  let wrapper: RenderResult;
  let $createRootFileBtn: HTMLElement;
  let $createRootFolderBtn: HTMLElement;
  let $editBtn: HTMLElement;
  let $input: HTMLInputElement;
  let $codeEditorInput: HTMLInputElement;
  let $tabList: HTMLElement;
  let $treeContainer: HTMLElement;
  let $moreActionBtn: HTMLElement;
  let $deleteBtn: HTMLElement;
  let $fileInput: HTMLElement;

  let giveWeakRandomKeySpy: jest.SpyInstance;
  const tempRandomKey = 'tempFile';
  let tempNodeKey = '';

  async function _createFile(fileKey: string, isAsyncMode = false, isAPISuccess = true) {
    return _createNode(fileKey, true, isAsyncMode, isAPISuccess);
  }
  async function _createFolder(folderKey: string, isAsyncMode = false, isAPISuccess = true) {
    return _createNode(folderKey, false, isAsyncMode, isAPISuccess);
  }
  async function _createNode(
    nodeKey: string,
    isFile = true,
    isAsyncMode = false,
    isAPISuccess = true,
  ) {
    let $createFileBtn: HTMLElement | null;
    let $createFolderBtn: HTMLElement | null;

    const { parentPath, fileName } = getFileInfoByFilePath(nodeKey);

    //  Get existed button of creating through parent nodes
    if (isFile) {
      $createFileBtn = parentPath
        ? wrapper.getByTestId(`btn-create-file-${parentPath}`)
        : $createRootFileBtn;
      $createFolderBtn = parentPath
        ? wrapper.getByTestId(`btn-create-folder-${parentPath}`)
        : $createRootFolderBtn;
    } else {
      $createFileBtn = wrapper.queryByTestId(`btn-create-file-${parentPath}`);
      $createFolderBtn = wrapper.queryByTestId(`btn-create-folder-${parentPath}`);

      while (!$createFileBtn || !$createFolderBtn) {
        const { parentPath: innerParentPath } = getFileInfoByFilePath(parentPath);

        if (!innerParentPath) {
          $createFileBtn = $createRootFileBtn;
          $createFolderBtn = $createRootFolderBtn;
        } else {
          $createFileBtn = wrapper.queryByTestId(`btn-create-file-${innerParentPath}`);
          $createFolderBtn = wrapper.queryByTestId(`btn-create-folder-${innerParentPath}`);
        }
      }
    }

    // Click create button to enter focus mode
    fireEvent.click(isFile ? $createFileBtn! : $createFolderBtn!);

    await waitFor(() => {
      $input = wrapper.queryByTestId(
        `input-${parentPath ? `${parentPath}/` : ''}${tempNodeKey}`,
      ) as HTMLInputElement;
      expect($input).toBeInTheDocument();
    });

    // Only 1 input dom should be rendered
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    // Default value is empty string
    expect($input.value).toBe('');

    // Trigger blur event to save the value
    fireEvent.blur($input, { target: { value: fileName } });

    expect($input.value).toBe(fileName);

    if (isAsyncMode) {
      await waitForLoadingEnd(wrapper);
    }

    await waitFor(() => {
      expect(
        wrapper.queryByTestId(`input-${parentPath ? `${parentPath}/` : ''}${tempNodeKey}`),
      ).not.toBeInTheDocument();
      if (!isAsyncMode || isAPISuccess) {
        expect(wrapper.queryByTestId(nodeKey)).toBeInTheDocument();
      }
    });

    if (isFile && (!isAsyncMode || isAPISuccess)) {
      expect(wrapper.container.querySelectorAll('.arco-tree-node-selected').length).toBe(1);
    }
  }
  async function _selectNode(nodeKey: string, isAsyncMode = false) {
    const $fileNode = wrapper.getByTestId(nodeKey);
    fireEvent.click(within($fileNode).getByText(_getFileName(nodeKey)));

    try {
      if (isAsyncMode) {
        await waitForLoadingEnd(wrapper);
      }
    } catch (error) {
      // If there is no loading, do nothing
    }

    expect(wrapper.container.querySelectorAll('.arco-tree-node-selected').length).toBe(1);
  }
  async function _renameNode(
    nodeKey: string,
    newNodeName: string,
    isAsyncMode = false,
    isAPISuccess = true,
  ) {
    $editBtn = wrapper.getByTestId(`btn-edit-${nodeKey}`);
    $input = wrapper.queryByTestId(`input-${nodeKey}`) as HTMLInputElement;

    const { fileName } = getFileInfoByFilePath(nodeKey);

    // Input should not be rendered
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(0);
    expect($input).not.toBeInTheDocument();

    // Click edit button to enter focus mode
    fireEvent.click($editBtn);

    await waitFor(() => {
      $input = wrapper.queryByTestId(`input-${nodeKey}`) as HTMLInputElement;
      expect($input).toBeInTheDocument();
    });

    // Only 1 input dom should be rendered
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    // Default value is file name
    expect($input.value).toBe(fileName);

    // Rename fileName to newNodeName
    fireEvent.change($input, { target: { value: newNodeName } });
    expect($input.value).toBe(newNodeName);

    // Trigger blur event
    fireEvent.blur($input, { target: { value: newNodeName } });

    if (isAsyncMode) {
      await waitForLoadingEnd(wrapper);
    }

    await waitFor(() => {
      expect(wrapper.queryByTestId(`input-${nodeKey}`)).not.toBeInTheDocument();
    });

    if (!isAsyncMode || isAPISuccess) {
      await waitFor(() => {
        expect(within($treeContainer).queryByText(newNodeName)).toBeInTheDocument();
      });
      expect(within($treeContainer).queryByText(fileName)).not.toBeInTheDocument();
    } else {
      await waitFor(() => {
        expect(within($treeContainer).queryByText(fileName)).toBeInTheDocument();
      });
      expect(within($treeContainer).queryByText(newNodeName)).not.toBeInTheDocument();
    }
  }
  async function _deleteNode(fileKey: string, isAsyncMode = false, isAPISuccess = true) {
    const $fileNode = wrapper.getByTestId(fileKey);

    $moreActionBtn = within($fileNode).getByTestId(`btn-more-actions`);

    if (!wrapper.queryByTestId(`btn-more-acitons-delete-${fileKey}`)) {
      // Click more action button to show delete button
      fireEvent.click($moreActionBtn);
    }

    // Wait for delete button to be visible
    await waitFor(() =>
      expect(wrapper.getByTestId(`btn-more-acitons-delete-${fileKey}`)).toBeVisible(),
    );

    // Find delete button
    $deleteBtn = wrapper.getByTestId(`btn-more-acitons-delete-${fileKey}`)!;

    // Click delete button
    fireEvent.click($deleteBtn);

    if (isAsyncMode) {
      await waitForLoadingEnd(wrapper);
    }

    if (!isAsyncMode || isAPISuccess) {
      await waitFor(() => {
        expect(wrapper.queryByTestId(`tab-${fileKey}`)).not.toBeInTheDocument();
        expect(wrapper.queryByTestId(fileKey)).not.toBeInTheDocument();
      });
    } else {
      await waitFor(() => {
        expect(wrapper.queryByTestId(`tab-${fileKey}`)).toBeInTheDocument();
        expect(wrapper.queryByTestId(fileKey)).toBeInTheDocument();
      });
    }
  }
  async function _uploadFile(
    fileKey: string,
    fileContent: string,
    isAsyncMode = false,
    isAPISuccess = true,
  ) {
    const { fileName } = getFileInfoByFilePath(fileKey);
    const mockFile = new File([fileContent], fileName, { type: 'text/plain' });

    fireEvent.change($fileInput, { target: { files: [mockFile] } });

    try {
      if (isAsyncMode) {
        await waitForLoadingEnd(wrapper);
      }
    } catch (error) {
      // If there is no loading, do nothing
    }

    if (!isAsyncMode || isAPISuccess) {
      await waitFor(() => {
        expect(wrapper.queryByTestId(fileKey)).toBeInTheDocument();
      });
    } else {
      await waitFor(() => {
        expect(wrapper.queryByTestId(fileKey)).not.toBeInTheDocument();
      });
    }
  }

  async function _closeTab(fileKey: string) {
    fireEvent.click(wrapper.getByTestId(`tab-btn-close-${fileKey}`));

    await _waitForTabHidden(fileKey);
  }

  async function _editCodeEditorValue(fileKey: string, newValue: string) {
    fireEvent.change($codeEditorInput, { target: { value: newValue, fileKey }, fileKey });
    await waitFor(() => {
      expect($codeEditorInput.value).toBe(newValue);
    });
  }
  async function _waitForTabShow(fileKey: string, isActive: boolean = true) {
    await waitFor(() => wrapper.getByTestId(`tab-${fileKey}`));
    expect(wrapper.getByTestId(`tab-${fileKey}`)).toHaveAttribute(
      'data-is-active',
      isActive ? 'true' : 'false',
    );
  }
  async function _waitForTabHidden(fileKey: string) {
    await waitFor(() => {
      expect(wrapper.queryByTestId(`tab-${fileKey}`)).not.toBeInTheDocument();
    });
  }
  describe('isAsyncMode = false', () => {
    beforeEach(async () => {
      giveWeakRandomKeySpy = jest.spyOn(helpers, 'giveWeakRandomKey').mockImplementation(() => {
        return tempRandomKey;
      });
      tempNodeKey = `${tempRandomKey}`;

      wrapper = render(
        <BaseCodeEditor
          initialFileData={testFiledata}
          isAsyncMode={false}
          title="I am title"
          isReadOnly={false}
        />,
      );
      expect(wrapper.getByText('I am title')).toBeInTheDocument();

      $createRootFileBtn = wrapper.getByTestId('btn-create-file-on-root');
      $createRootFolderBtn = wrapper.getByTestId('btn-create-folder-on-root');
      $tabList = wrapper.getByTestId('tab-list');
      $fileInput = wrapper.container.querySelector('input[type="file"]')!;

      expect($createRootFileBtn).toBeInTheDocument();
      expect($createRootFolderBtn).toBeInTheDocument();

      await waitFor(() => wrapper.getAllByText(testFileKey)[0]); // file node
      $treeContainer = wrapper.container.querySelector('.arco-tree')!;

      const nodeList = wrapper.container.querySelectorAll('.arco-tree .arco-tree-node');
      expect(nodeList.length).toBe(8);

      await waitFor(() => wrapper.getByTestId(`tab-${testFileKey}`));

      expect(wrapper.getByTestId(`tab-${testFileKey}`)).toHaveAttribute('data-is-active', 'true');

      $codeEditorInput = wrapper.getByTestId('input-code-editor') as HTMLInputElement;
      expect($codeEditorInput.value).toBe(testFileContent);
    });

    afterEach(() => {
      giveWeakRandomKeySpy.mockRestore();
    });

    it(`
      1. create new file(newFile.js) on root
      2. edit the new file(newFile.js) content
      3. select the other file(t1.yaml) to trigger tab change, and save the value that belong to the new file
      4. edit the other file(t1.yaml) content
      5. select new file(newFile.js) again to trigger tab change, and save the value that belong to the other file
      6. select first file(owner.py) again to trigger tab change, and save the value that belong to the first file
    `, async () => {
      await _createFile('newFile.js');
      await _waitForTabShow('newFile.js');
      await _editCodeEditorValue('newFile.js', 'I am newFile.js');
      await _selectNode('t1.yaml');
      await _waitForTabShow('t1.yaml');
      expect($codeEditorInput.value).toBe('# Get Started with Codebase CI');
      await _editCodeEditorValue('t1.yaml', 'I am t1.yaml');
      await _selectNode('newFile.js');
      await _waitForTabShow('newFile.js');
      expect($codeEditorInput.value).toBe('I am newFile.js');
      await _selectNode(testFileKey);
      await _waitForTabShow(testFileKey);
      expect($codeEditorInput.value).toBe(testFileContent);
    });

    it(`
      1. select file(t1.yaml)
      2. select file(t2.config)
      3. select file(t3.json)
      4. select file(t2.config)
      5. close file tab(t3.json)
      6. close file tab(t2.config)
      6. close file tab(t1.yaml)
      7. close file tab(owner.py)
    `, async () => {
      expect($tabList.children.length).toBe(1);
      await _selectNode('t1.yaml');
      await _waitForTabShow('t1.yaml');
      expect($codeEditorInput.value).toBe('# Get Started with Codebase CI');
      expect($tabList.children.length).toBe(2);
      await _selectNode('t2.config');
      await _waitForTabShow('t2.config');
      expect($codeEditorInput.value).toBe('# coding: utf-8');
      expect($tabList.children.length).toBe(3);
      await _selectNode('t3.json');
      await _waitForTabShow('t3.json');
      expect($codeEditorInput.value).toBe('{ "a":1 }');
      expect($tabList.children.length).toBe(4);
      await _selectNode('t2.config');
      await _waitForTabShow('t2.config');
      expect($tabList.children.length).toBe(4);
      expect($codeEditorInput.value).toBe('# coding: utf-8');
      await _closeTab('t3.json');
      expect($tabList.children.length).toBe(3);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-t2.config`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe('# coding: utf-8');
      await _closeTab('t2.config');
      expect($tabList.children.length).toBe(2);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-owner.py`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe(testFileContent);
      await _closeTab('t1.yaml');
      expect($tabList.children.length).toBe(1);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-owner.py`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe(testFileContent);
      expect($codeEditorInput).not.toBeDisabled();
      await _closeTab(testFileKey);
      expect($tabList.children.length).toBe(0);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(0);
      expect($codeEditorInput.value).toBe('');
      expect($codeEditorInput).toBeDisabled();
    });

    describe('Handle folder', () => {
      beforeEach(async () => {
        await _selectNode('leader/main.py');
        await _waitForTabShow('leader/main.py');
        // There are 3 nodes(1 folder + 2 file) in this folder before create
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(3);

        await _createFile('leader/newFile.js');
        await _waitForTabShow('leader/newFile.js');
        await _editCodeEditorValue('leader/newFile.js', 'I am leader/newFile.js');
        // There are 4 nodes(1 folder + 3 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(4);

        await _createFolder('leader/newFolder');
        // There are 5 nodes(2 folder + 3 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(5);

        await _selectNode('leader/newFolder');
        await _createFile('leader/newFolder/newFile2.js');
        await _waitForTabShow('leader/newFolder/newFile2.js');
        await _editCodeEditorValue(
          'leader/newFolder/newFile2.js',
          'I am leader/newFolder/newFile2.js',
        );
        // There are 6 nodes(2 folder + 4 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);

        // There are 4 tab(owner.py, leader/main.py, leader/newFile.js, leader/newFolder/newFile2.js)
        expect($tabList.children.length).toBe(4);
        expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
        expect($codeEditorInput.value).toBe('I am leader/newFolder/newFile2.js');
      });

      it(`
      1. select file(leader/main.py)
      2. create new file(leader/newFile.js)
      3. create new folder(leader/newFolder)
      4. select folder(leader/newFolder)
      5. create new file(leader/newFolder/newFile2.js)
      6. select leader/newFile.js
      7. select leader/main.py
      8. select owner.py
    `, async () => {
        await _selectNode('leader/newFile.js');
        await _waitForTabShow('leader/newFile.js');
        expect($codeEditorInput.value).toBe('I am leader/newFile.js');
        expect($tabList.children.length).toBe(4);

        await _selectNode('leader/main.py');
        await _waitForTabShow('leader/main.py');
        expect($codeEditorInput.value).toBe('I am leader/main.py');
        expect($tabList.children.length).toBe(4);

        await _selectNode(testFileKey);
        await _waitForTabShow(testFileKey);
        expect($codeEditorInput.value).toBe(testFileContent);
        expect($tabList.children.length).toBe(4);
      });

      it(`
      1. select file(leader/main.py)
      2. create new file(leader/newFile.js)
      3. create new folder(leader/newFolder)
      4. select folder(leader/newFolder)
      5. create new file(leader/newFolder/newFile2.js)
      6. rename file(leader/newFile.js) => file(leader/renameNewFile.js)
      7. rename file(leader/newFolder/newFile2.js) => file(leader/newFolder/renameNewFile2.js)
      8. select file(leader/newFolder/renameNewFile2.js)
      9. rename folder(leader/newFolder) => folder(leader/renameNewFolder)
    `, async () => {
        // There are 6 nodes(2 folder + 4 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
        expect($tabList.children.length).toBe(4);

        await _renameNode('leader/newFile.js', 'renameNewFile.js');
        await waitFor(() => {
          expect(wrapper.queryByTestId(`tab-leader/newFile.js`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`leader/renameNewFile.js`)).toBeInTheDocument();
        });
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
        expect($tabList.children.length).toBe(3);

        await _renameNode('leader/newFolder/newFile2.js', 'renameNewFile2.js');
        await waitFor(() => {
          expect(wrapper.queryByTestId(`tab-leader/newFolder/newFile2.js`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`leader/newFolder/renameNewFile2.js`)).toBeInTheDocument();
        });
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
        expect($tabList.children.length).toBe(2);

        await _selectNode('leader/newFolder/renameNewFile2.js');
        await _waitForTabShow('leader/newFolder/renameNewFile2.js');
        expect($tabList.children.length).toBe(3);
        expect($codeEditorInput.value).toBe('I am leader/newFolder/newFile2.js');

        await _renameNode('leader/newFolder', 'renameNewFolder');
        expect($tabList.children.length).toBe(2);

        await waitFor(() => {
          expect(wrapper.queryByTestId(`leader/newFolder`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`leader/renameNewFolder`)).toBeInTheDocument();
        });
        await _selectNode('leader/renameNewFolder'); // select folder to expand folder

        await waitFor(() =>
          expect(
            wrapper.queryByTestId(`leader/renameNewFolder/renameNewFile2.js`),
          ).toBeInTheDocument(),
        );
        // There are 6 nodes(2 folder + 4 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
      });
    });
  });

  describe('isAsyncMode = true', () => {
    beforeEach(async () => {
      mockApi.fetchAlgorithmProjectFileTreeList.mockResolvedValue({
        data: testTreeList,
      });
      mockApi.fetchAlgorithmProjectFileContentDetail.mockImplementation((id, { path }) => {
        const { parentPath, fileName } = getFileInfoByFilePath(path);
        return Promise.resolve({
          data: {
            path: parentPath,
            filename: fileName,
            content: `I am ${path}`,
          } as FileContent,
        });
      });
      mockApi.createOrUpdateAlgorithmProjectFileContent.mockImplementation(
        (id, { path, filename, is_directory, file }) =>
          Promise.resolve({
            data: {
              path,
              filename,
              content: file,
            } as FileContent,
          }),
      );
      mockApi.renameAlgorithmProjectFileContent.mockImplementation((id, { path, dest }) =>
        Promise.resolve(null),
      );
      mockApi.deleteAlgorithmProjectFileContent.mockImplementation((id, { path }) =>
        Promise.resolve(null),
      );

      giveWeakRandomKeySpy = jest.spyOn(helpers, 'giveWeakRandomKey').mockImplementation(() => {
        return tempRandomKey;
      });
      tempNodeKey = `${tempRandomKey}`;

      wrapper = render(
        <BaseCodeEditor
          initialFileData={{}}
          title="I am title"
          isReadOnly={false}
          {...asyncProps}
        />,
      );
      expect(wrapper.getByText('I am title')).toBeInTheDocument();

      $createRootFileBtn = wrapper.getByTestId('btn-create-file-on-root');
      $createRootFolderBtn = wrapper.getByTestId('btn-create-folder-on-root');
      $tabList = wrapper.getByTestId('tab-list');
      $fileInput = wrapper.container.querySelector('input[type="file"]')!;

      expect($createRootFileBtn).toBeInTheDocument();
      expect($createRootFolderBtn).toBeInTheDocument();

      await waitForLoadingEnd(wrapper);

      await waitFor(() => wrapper.getAllByText(testFileKey)[0]); // file node
      $treeContainer = wrapper.container.querySelector('.arco-tree')!;

      const nodeList = wrapper.container.querySelectorAll('.arco-tree .arco-tree-node');
      expect(nodeList.length).toBe(8);

      await waitFor(() => wrapper.getByTestId(`tab-${testFileKey}`));

      expect(wrapper.getByTestId(`tab-${testFileKey}`)).toHaveAttribute('data-is-active', 'true');

      $codeEditorInput = wrapper.getByTestId('input-code-editor') as HTMLInputElement;
      expect($codeEditorInput.value).toBe(`I am ${testFileKey}`);
    });

    afterEach(() => {
      giveWeakRandomKeySpy.mockRestore();
    });

    it(`
      1. create new file(newFile.js) on root
      2. edit the new file(newFile.js) content
      3. select the other file(t1.yaml) to trigger tab change, and save the value that belong to the new file
      4. edit the other file(t1.yaml) content
      5. select new file(newFile.js) again to trigger tab change, and save the value that belong to the other file
      6. select first file(owner.py) again to trigger tab change, and save the value that belong to the first file
    `, async () => {
      await _createFile('newFile.js', true);
      await _waitForTabShow('newFile.js');
      await _editCodeEditorValue('newFile.js', 'Edit: I am newFile.js');
      await _selectNode('t1.yaml', true);
      await _waitForTabShow('t1.yaml');
      expect($codeEditorInput.value).toBe('I am t1.yaml');
      await _editCodeEditorValue('t1.yaml', 'Edit: I am t1.yaml');
      await _selectNode('newFile.js', true);
      await _waitForTabShow('newFile.js');
      expect($codeEditorInput.value).toBe('Edit: I am newFile.js');
      await _selectNode(testFileKey, true);
      await _waitForTabShow(testFileKey);
      expect($codeEditorInput.value).toBe(`I am ${testFileKey}`);
    });

    it(`
      1. select file(t1.yaml)
      2. select file(t2.config)
      3. select file(t3.json)
      4. select file(t2.config)
      5. close file tab(t3.json)
      6. close file tab(t2.config)
      6. close file tab(t1.yaml)
      7. close file tab(owner.py)
    `, async () => {
      expect($tabList.children.length).toBe(1);
      await _selectNode('t1.yaml', true);
      await _waitForTabShow('t1.yaml');
      expect($codeEditorInput.value).toBe('I am t1.yaml');
      expect($tabList.children.length).toBe(2);
      await _selectNode('t2.config', true);
      await _waitForTabShow('t2.config');
      expect($codeEditorInput.value).toBe('I am t2.config');
      expect($tabList.children.length).toBe(3);
      await _selectNode('t3.json', true);
      await _waitForTabShow('t3.json');
      expect($codeEditorInput.value).toBe('I am t3.json');
      expect($tabList.children.length).toBe(4);
      await _selectNode('t2.config', true);
      await _waitForTabShow('t2.config');
      expect($tabList.children.length).toBe(4);
      expect($codeEditorInput.value).toBe('I am t2.config');
      await _closeTab('t3.json');
      expect($tabList.children.length).toBe(3);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-t2.config`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe('I am t2.config');
      await _closeTab('t2.config');
      expect($tabList.children.length).toBe(2);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-owner.py`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe('I am owner.py');
      await _closeTab('t1.yaml');
      expect($tabList.children.length).toBe(1);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-owner.py`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe('I am owner.py');
      expect($codeEditorInput).not.toBeDisabled();
      await _closeTab(testFileKey);
      expect($tabList.children.length).toBe(0);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(0);
      expect($codeEditorInput.value).toBe('');
      expect($codeEditorInput).toBeDisabled();
    });

    it(`
      1. upload file(uploadFile.js)
      2. select file(uploadFile.js)
      3. close file tab(uploadFile.js)
    `, async () => {
      expect($tabList.children.length).toBe(1);
      expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
        8,
      );

      mock.setup();
      mock.post('/api/v2/algorithm_projects/3/files', {
        status: 200,
        reason: 'ok',
        body: JSON.stringify({
          data: {
            path: '',
            filename: 'uploadFile.js',
          },
        }),
      });

      await _uploadFile('uploadFile.js', 'I am uploadFile.js', true, true);
      expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
        9,
      );
      expect($tabList.children.length).toBe(1);
      await _selectNode('uploadFile.js');
      await _waitForTabShow('uploadFile.js');
      expect($tabList.children.length).toBe(2);
      expect($codeEditorInput.value).toBe('I am uploadFile.js');
      await _closeTab('uploadFile.js');
      expect($tabList.children.length).toBe(1);
      expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
      expect(wrapper.getByTestId(`tab-owner.py`)).toHaveAttribute('data-is-active', 'true');
      expect($codeEditorInput.value).toBe('I am owner.py');

      mock.teardown();
    });

    describe('Handle folder', () => {
      beforeEach(async () => {
        await _selectNode('leader/main.py', true);
        await _waitForTabShow('leader/main.py');
        // There are 3 nodes(1 folder + 2 file) in this folder before create
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(3);

        await _createFile('leader/newFile.js', true);
        await _waitForTabShow('leader/newFile.js');
        await _editCodeEditorValue('leader/newFile.js', 'I am leader/newFile.js');
        // There are 4 nodes(1 folder + 3 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(4);

        await _createFolder('leader/newFolder', true);
        // There are 5 nodes(2 folder + 3 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(5);

        await _selectNode('leader/newFolder');
        await _createFile('leader/newFolder/newFile2.js', true);
        await _waitForTabShow('leader/newFolder/newFile2.js');
        await _editCodeEditorValue(
          'leader/newFolder/newFile2.js',
          'I am leader/newFolder/newFile2.js',
        );
        // There are 6 nodes(2 folder + 4 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);

        // There are 4 tab(owner.py, leader/main.py, leader/newFile.js, leader/newFolder/newFile2.js)
        expect($tabList.children.length).toBe(4);
        expect($tabList.querySelectorAll('div[data-is-active="true"]').length).toBe(1);
        expect($codeEditorInput.value).toBe('I am leader/newFolder/newFile2.js');
      });

      it(`
      1. select file(leader/main.py)
      2. create new file(leader/newFile.js)
      3. create new folder(leader/newFolder)
      4. select folder(leader/newFolder)
      5. create new file(leader/newFolder/newFile2.js)
      6. select leader/newFile.js
      7. select leader/main.py
      8. select owner.py
    `, async () => {
        await _selectNode('leader/newFile.js', true);
        await _waitForTabShow('leader/newFile.js');
        expect($codeEditorInput.value).toBe('I am leader/newFile.js');
        expect($tabList.children.length).toBe(4);

        await _selectNode('leader/main.py', true);
        await _waitForTabShow('leader/main.py');
        expect($codeEditorInput.value).toBe('I am leader/main.py');
        expect($tabList.children.length).toBe(4);

        await _selectNode(testFileKey, true);
        await _waitForTabShow(testFileKey);
        expect($codeEditorInput.value).toBe(`I am ${testFileKey}`);
        expect($tabList.children.length).toBe(4);
      });

      it(`
      1. select file(leader/main.py)
      2. create new file(leader/newFile.js)
      3. create new folder(leader/newFolder)
      4. select folder(leader/newFolder)
      5. create new file(leader/newFolder/newFile2.js)
      6. rename file(leader/newFile.js) => file(leader/renameNewFile.js)
      7. rename file(leader/newFolder/newFile2.js) => file(leader/newFolder/renameNewFile2.js)
      8. select file(leader/newFolder/renameNewFile2.js)
      9. rename folder(leader/newFolder) => folder(leader/renameNewFolder)
    `, async () => {
        // There are 6 nodes(2 folder + 4 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
        expect($tabList.children.length).toBe(4);

        await _renameNode('leader/newFile.js', 'renameNewFile.js');
        await waitFor(() => {
          expect(wrapper.queryByTestId(`tab-leader/newFile.js`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`leader/renameNewFile.js`)).toBeInTheDocument();
        });
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
        expect($tabList.children.length).toBe(3);

        await _renameNode('leader/newFolder/newFile2.js', 'renameNewFile2.js');
        await waitFor(() => {
          expect(wrapper.queryByTestId(`tab-leader/newFolder/newFile2.js`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`leader/newFolder/renameNewFile2.js`)).toBeInTheDocument();
        });
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
        expect($tabList.children.length).toBe(2);

        await _selectNode('leader/newFolder/renameNewFile2.js', true);
        await _waitForTabShow('leader/newFolder/renameNewFile2.js');
        expect($tabList.children.length).toBe(3);
        expect($codeEditorInput.value).toBe('I am leader/newFolder/newFile2.js');

        await _renameNode('leader/newFolder', 'renameNewFolder');
        expect($tabList.children.length).toBe(2);

        await waitFor(() => {
          expect(wrapper.queryByTestId(`leader/newFolder`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`leader/renameNewFolder`)).toBeInTheDocument();
        });
        await _selectNode('leader/renameNewFolder'); // select folder to expand folder

        await waitFor(() =>
          expect(
            wrapper.queryByTestId(`leader/renameNewFolder/renameNewFile2.js`),
          ).toBeInTheDocument(),
        );
        // There are 6 nodes(2 folder + 4 file) in this folder
        expect(wrapper.getAllByTestId(new RegExp(`^leader/`)).length).toBe(6);
      });
    });

    describe('Handle API response error', () => {
      it(`
      1. create new file(newFile.js) on root but API response error
      2. create new file(newFile.js) on root
      3. rename file(newFile.js) => file(renameNewFile.js) but API response error
      4. rename file(newFile.js) => file(renameNewFile.js)
      5. select file(renameNewFile.js)
      6. delete file(renameNewFile.js) but API response error
      7. delete file(renameNewFile.js)
      8. upload file(uploadFile.js) on root but API response error
    `, async () => {
        mockApi.createOrUpdateAlgorithmProjectFileContent.mockImplementationOnce(
          (id, { path, filename, is_directory, file }) =>
            Promise.reject({
              data: null,
            }),
        );
        expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
          8,
        );
        await _createFile('newFile.js', true, false);
        expect(wrapper.queryByTestId(`tab-newFile.js`)).not.toBeInTheDocument();
        expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
          8,
        );
        await _createFile('newFile.js', true, true);
        await _waitForTabShow('newFile.js');
        expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
          9,
        );
        await _editCodeEditorValue('newFile.js', 'Edit: I am newFile.js');

        mockApi.renameAlgorithmProjectFileContent.mockImplementationOnce((id, { path, dest }) =>
          Promise.reject({
            data: null,
          }),
        );
        await _renameNode('newFile.js', 'renameNewFile.js', true, false);
        await waitFor(() => {
          expect(wrapper.queryByTestId(`tab-newFile.js`)).toBeInTheDocument();
          expect(wrapper.queryByTestId(`renameNewFile.js`)).not.toBeInTheDocument();
        });
        expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
          9,
        );
        expect($tabList.children.length).toBe(2);

        await _renameNode('newFile.js', 'renameNewFile.js', true, true);
        await waitFor(() => {
          expect(wrapper.queryByTestId(`tab-newFile.js`)).not.toBeInTheDocument();
          expect(wrapper.queryByTestId(`renameNewFile.js`)).toBeInTheDocument();
        });
        expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
          9,
        );
        expect($tabList.children.length).toBe(1);

        await _selectNode('renameNewFile.js');
        await _waitForTabShow('renameNewFile.js');
        expect($codeEditorInput.value).toBe('Edit: I am newFile.js');
        expect($tabList.children.length).toBe(2);

        mockApi.deleteAlgorithmProjectFileContent.mockImplementationOnce((id, { path }) =>
          Promise.reject({
            data: null,
          }),
        );
        mock.setup();
        mock.post('/api/v2/algorithm_projects/3/files', {
          status: 400,
          reason: 'Bad request',
          body: '',
        });

        await _uploadFile('uploadFile.js', 'I am uploadFile.js', true, false);
        expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(
          9,
        );
        expect($tabList.children.length).toBe(2);

        // TODO: mock upload API success

        mock.teardown();
      });
    });
  });

  it('should only show one input when focus mode = true', async () => {
    wrapper = render(
      <BaseCodeEditor
        initialFileData={testFiledata}
        isAsyncMode={false}
        title="I am title"
        isReadOnly={false}
      />,
    );

    await waitFor(() => wrapper.getAllByText(testFileKey)[0]); // file node

    $createRootFileBtn = wrapper.getByTestId('btn-create-file-on-root');
    $createRootFolderBtn = wrapper.getByTestId('btn-create-folder-on-root');

    expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(8);
    // Only 0 input dom should be rendered
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(0);
    fireEvent.click($createRootFileBtn);

    // Only 1 input dom should be rendered
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(9);
    fireEvent.click($createRootFileBtn);
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(9);
    fireEvent.click($createRootFileBtn);
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(9);
    fireEvent.click($createRootFolderBtn);
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(9);
    fireEvent.click($createRootFolderBtn);
    expect(wrapper.container.querySelectorAll('.arco-tree input').length).toBe(1);
    expect(wrapper.container.querySelectorAll('.arco-tree .arco-tree-node').length).toBe(9);
  });
});
