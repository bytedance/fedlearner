import React, { FC } from 'react';
import Editor, { EditorProps } from '@monaco-editor/react';

export type CodeEditorProps = Omit<EditorProps, 'onChnage' | 'value'> & {
  value?: string;
  onChange?: (value: string) => void;
  language: 'json' | 'python';
};

const formatJsonValue = (str: string) => {
  try {
    const value = JSON.stringify(JSON.parse(str));
    return value;
  } catch (error) {
    return str;
  }
};

export const VS_DARK_COLOR = '#1e1e1e';

const CodeEditor: FC<CodeEditorProps> = ({ value, onChange, language, ...props }) => {
  return (
    <Editor
      height="100%"
      defaultLanguage={language || 'json'}
      defaultValue={value}
      theme="vs-dark"
      options={{
        fontSize: 16,
        lineHeight: 20,
        minimap: {
          enabled: false,
        },
      }}
      onChange={onCodeChange}
      {...props}
    />
  );

  function onCodeChange(val?: string) {
    if (language === 'json') {
      onChange && onChange(formatJsonValue(val || ''));
      return;
    }

    onChange && onChange(val || '');
  }
};

export default CodeEditor;
