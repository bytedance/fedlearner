import React, { FC, useEffect, useRef, useState } from 'react';
import { noop } from 'lodash-es';

import { EditorProps, Monaco } from '@monaco-editor/react';
import type * as monaco from 'monaco-editor/esm/vs/editor/editor.api';

export const VS_DARK_COLOR = '#1e1e1e';

export enum Action {
  Save = 'code_editor_action_save',
}

export type CodeEditorProps = Omit<EditorProps, 'onChange' | 'value' | 'language'> & {
  /** Code text */
  value?: string;
  onChange?: (value: string) => void;
  language?: 'json' | 'python' | 'javascript' | 'java' | 'go';
  isReadOnly?: boolean;
  /** Get editor/monaco instance on mount */
  getInstance?: (editor: monaco.editor.IStandaloneCodeEditor, monaco: Monaco) => void;
};

const CodeEditor: FC<CodeEditorProps> = ({ value, onChange, getInstance, isReadOnly }) => {
  const keyToModelMap = useRef<{
    [key: string]: {
      code: string;
      dispose: () => void;
    };
  }>({});
  const $input = useRef<HTMLInputElement>(null);

  const [innerValue, setInnerValue] = useState(value);

  const isControlled = typeof value === 'string';

  useEffect(() => {
    if (isControlled) {
      setInnerValue(value);
    }
  }, [value, isControlled]);

  useEffect(() => {
    getInstance?.(
      {
        saveViewState: noop as any,
        restoreViewState: noop as any,
        setModel: (model: any) => {
          const code = model.code;
          if (isControlled) {
            setInnerValue(code);
          } else {
            $input.current!.value = code;
          }
        },
      } as any,
      {
        Uri: {
          file: (key: string) => key,
        },
        editor: {
          getModel: (key: string) => keyToModelMap.current[key] ?? null,
          createModel: (code: string, language: string, uri: string) => {
            if (isControlled) {
              setInnerValue(code);
            } else {
              $input.current!.value = code;
            }

            const model = {
              code,
              dispose: () => {
                delete keyToModelMap.current[uri];
                if (Object.keys(keyToModelMap.current).length === 0) {
                  if (isControlled) {
                    setInnerValue('');
                  } else {
                    $input.current!.value = '';
                  }
                }
              },
            };
            keyToModelMap.current[uri] = model;
            return model;
          },
        },
      } as any,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <input
      ref={$input}
      type="text"
      onChange={(event: any) => {
        const { value, fileKey } = event.target;

        const model = keyToModelMap.current[fileKey];
        if (model) {
          model.code = value;
        }
        onChange?.(value);
      }}
      value={isControlled ? innerValue : undefined}
      data-testid="input-code-editor"
      disabled={isReadOnly}
    />
  );
};
export default CodeEditor;
