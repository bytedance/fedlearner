/* istanbul ignore file */

import React, { FC, useRef } from 'react';
import Editor, { EditorProps, loader, Monaco } from '@monaco-editor/react';
import { Message } from '@arco-design/web-react';
import styled from 'styled-components';

import { formatJSONValue } from 'shared/helpers';
import type * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import PubSub from 'pubsub-js';

export type CodeEditorProps = Omit<EditorProps, 'onChange' | 'value' | 'language'> & {
  /** Code text */
  value?: string;
  onChange?: (value: string) => void;
  language?: 'json' | 'python' | 'javascript' | 'java' | 'go' | 'shell';
  isReadOnly?: boolean;
  /** Get editor/monaco instance on mount */
  getInstance?: (editor: monaco.editor.IStandaloneCodeEditor, monaco: Monaco) => void;
};

async function monacoInit() {
  // If current env isn't dumi, use local monaco file. otherwise, monaco files are being downloaded from CDN.
  // https://github.com/suren-atoyan/monaco-react#loader-config
  if (!process.env.IS_DUMI_ENV) {
    const monaco = await import('monaco-editor/esm/vs/editor/editor.api.js');
    loader.config({ monaco });
  }
  const monacoInstance = await loader.init();
  monacoInstance.editor.defineTheme('grey', {
    base: 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#F6F7FB',
    },
  });
}

monacoInit();

export const VS_DARK_COLOR = '#1e1e1e';

export enum Action {
  Save = 'code_editor_action_save',
}

const StyledCodeEditor = styled(Editor)<{
  isReadOnly?: boolean;
}>`
  .monaco-editor .cursors-layer > .cursor {
    ${(props) => props.options?.readOnly && `display: none !important`};
  }
  .monaco-editor .overflowingContentWidgets {
    ${(props) => props.options?.readOnly && `display: none !important`};
  }
`;
const CodeEditor: FC<CodeEditorProps> = ({
  value,
  onChange,
  language,
  isReadOnly = false,
  getInstance,
  ...props
}) => {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  return (
    <StyledCodeEditor
      height="100%"
      defaultLanguage={language || 'json'}
      // defaultValue, defaultLanguage, and defaultPath are being considered only during a new model creation
      // value, language, and path are being tracked the whole time
      value={value}
      theme="vs-dark"
      options={{
        padding: {
          top: 16,
          bottom: 16,
        },
        fontSize: 12,
        lineHeight: 20,
        minimap: {
          enabled: false,
        },
        readOnly: isReadOnly,
        renderLineHighlight: isReadOnly ? 'none' : 'all',
      }}
      onChange={onCodeChange}
      onMount={onEditorDidMount}
      isReadOnly={isReadOnly}
      {...props}
    />
  );

  function onCodeChange(val?: string) {
    if (language === 'json') {
      onChange && onChange(formatJSONValue(val || ''));
      return;
    }

    onChange && onChange(val || '');
  }

  function onEditorDidMount(editor: any, monaco: any) {
    if (!isReadOnly) {
      editorRef.current = editor;

      const KM = monaco.KeyMod;
      const KC = monaco.KeyCode;

      editorRef.current?.addCommand(KM.CtrlCmd | KC.KEY_S, () => {
        PubSub.publish(Action.Save);
        Message.success('已保存');
      });
    }
    if (getInstance) {
      getInstance(editor, monaco);
    }
  }
};

export default CodeEditor;
