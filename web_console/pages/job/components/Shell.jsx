import React, { useRef, useEffect, useCallback } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import SockJS from 'sockjs-client';
import { useToasts } from '@zeit-ui/react';
import debounce from 'lodash/debounce';

function Shell({ id, base }) {
  const [, setToast] = useToasts();
  const ref = useRef();

  const connRef = useRef(null);
  const termRef = useRef(null);

  const onTerminalResize = useCallback(() => {
    if (connRef.current) {
      connRef.current.send(
        JSON.stringify({
          Op: 'resize',
          Cols: termRef.current.cols,
          Rows: termRef.current.rows,
        }),
      );
    }
  }, []);

  const onTerminalSendString = useCallback((str) => {
    if (connRef.current) {
      connRef.current.send(
        JSON.stringify({
          Op: 'stdin',
          Data: str,
          Cols: termRef.current.cols,
          Rows: termRef.current.rows,
        }),
      );
    }
  }, []);

  const initTerm = useCallback(() => {
    if (termRef.current) {
      termRef.current.dispose();
    }
    termRef.current = new Terminal({
      fontSize: 14,
      fontFamily: 'Consolas, "Courier New", monospace',
      bellStyle: 'sound',
      cursorBlink: true,
    });
    const fitAddon = new FitAddon();
    termRef.current.loadAddon(fitAddon);
    termRef.current.open(ref.current);
    fitAddon.fit();

    termRef.current.onData(onTerminalSendString);
    termRef.current.onResize(onTerminalResize);

    const listener = debounce(() => {
      fitAddon.fit();
    }, 100);
    window.addEventListener('resize', listener);
    return () => window.removeEventListener('resize', listener);
  }, [onTerminalResize, onTerminalSendString]);

  const onConnectionOpen = useCallback((sessionId) => {
    const startData = { Op: 'bind', SessionID: sessionId };
    connRef.current.send(JSON.stringify(startData));

    onTerminalResize();
    if (termRef.current) termRef.current.focus();
  }, [onTerminalResize]);

  const onConnectionMessage = useCallback((evt) => {
    const frame = JSON.parse(evt.data);

    if (frame.Op === 'stdout') {
      termRef.current.write(frame.Data);
    }

    if (frame.Op === 'toast') {
      setToast({ text: frame.Data });
    }
  }, []);

  const onConnectionClose = useCallback((evt) => {
    if (connRef.current) {
      connRef.current.close();
      setToast({ text: (evt && evt.reason) || 'Something went wrong.' });
    }
  }, []);

  const initConn = useCallback(() => {
    if (connRef.current) {
      connRef.current.close();
    }
    connRef.current = new SockJS(`${base}/api/sockjs?${id}`);
    connRef.current.onopen = onConnectionOpen.bind(this, id);
    connRef.current.onmessage = onConnectionMessage;
    connRef.current.onclose = onConnectionClose;
  }, [id, base, onConnectionOpen, onConnectionMessage, onConnectionClose]);

  useEffect(() => {
    initConn();
    initTerm();
  }, []);

  return (
    <>
      <div ref={ref} />
      {/* import 'xterm/css/xterm.css'; */}
      <style jsx global>{`
        html body {
          margin: 0;
          padding: 0;
          height: 100vh;
        }
        .xterm {
          font-feature-settings: "liga" 0;
          position: relative;
          user-select: none;
          -ms-user-select: none;
          -webkit-user-select: none;
          height: 100vh;
        }
        
        .xterm.focus,
        .xterm:focus {
          outline: none;
        }
        
        .xterm .xterm-helpers {
          position: absolute;
          top: 0;
          z-index: 5;
        }
        
        .xterm .xterm-helper-textarea {
          position: absolute;
          opacity: 0;
          left: -9999em;
          top: 0;
          width: 0;
          height: 0;
          z-index: -5;
          white-space: nowrap;
          overflow: hidden;
          resize: none;
        }
        
        .xterm .composition-view {
          background: #000;
          color: #FFF;
          display: none;
          position: absolute;
          white-space: nowrap;
          z-index: 1;
        }
        
        .xterm .composition-view.active {
          display: block;
        }
        
        .xterm .xterm-viewport {
          background-color: #000;
          overflow-y: scroll;
          cursor: default;
          position: absolute;
          right: 0;
          left: 0;
          top: 0;
          bottom: 0;
        }
        
        .xterm .xterm-screen {
          position: relative;
        }
        
        .xterm .xterm-screen canvas {
          position: absolute;
          left: 0;
          top: 0;
        }
        
        .xterm .xterm-scroll-area {
          visibility: hidden;
        }
        
        .xterm-char-measure-element {
          display: inline-block;
          visibility: hidden;
          position: absolute;
          top: 0;
          left: -9999em;
          line-height: normal;
        }
        
        .xterm {
          cursor: text;
        }
        
        .xterm.enable-mouse-events {
          cursor: default;
        }
        
        .xterm.xterm-cursor-pointer {
          cursor: pointer;
        }
        
        .xterm.column-select.focus {
          cursor: crosshair;
        }
        
        .xterm .xterm-accessibility,
        .xterm .xterm-message {
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          right: 0;
          z-index: 10;
          color: transparent;
        }
        
        .xterm .live-region {
          position: absolute;
          left: -9999px;
          width: 1px;
          height: 1px;
          overflow: hidden;
        }
        
        .xterm-dim {
          opacity: 0.5;
        }
        
        .xterm-underline {
          text-decoration: underline;
        }
      `}</style>
    </>
  );
}

export default Shell;
