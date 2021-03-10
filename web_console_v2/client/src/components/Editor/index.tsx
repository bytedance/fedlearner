import React, { FC, useRef, useEffect, useState } from 'react';
import styled from 'styled-components';
import * as monaco from 'monaco-editor';
import { decodeBase64 } from 'shared/base64';

const EditorContainer = styled.div`
  width: 100%;
  height: 100%;
`;
interface EditorProps {
  value: string;
  language: 'json' | 'python';
  onChange: (value: string) => void;
}
const formatJsonValue = (str: string) => {
  try {
    const value = JSON.stringify(JSON.parse(str));
    return value;
  } catch (error) {
    return str;
  }
};

const Editor: FC<EditorProps> = ({ value, language, onChange }) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [_editor, setEditor] = useState<monaco.editor.IStandaloneCodeEditor>();

  useEffect(() => {
    if (editorRef.current) {
      setEditor(monaco.editor.create(editorRef.current, { theme: 'vs-dark', tabSize: 2 }));
    }
  }, []);

  useEffect(() => {
    const model = monaco.editor.createModel(decodeBase64(value), language);

    _editor?.setModel(model);

    model.onDidChangeContent(() => {
      let value;
      if (language === 'json') value = formatJsonValue(model.getValue());
      // TODO: 格式化 python 代码的字符串
      else value = model.getValue();
      onChange(btoa(encodeURIComponent(value)));
    });

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, language, _editor]);

  return <EditorContainer ref={editorRef} />;
};

const TestEditor: FC = () => {
  return (
    <EditorContainer>
      <Editor
        value="ZGRkZGFhYWElRTclOTklOEMlMEElMEE="
        language="json"
        onChange={(val) => {
          console.log(val);
        }}
      />
    </EditorContainer>
  );
};

export default TestEditor;
