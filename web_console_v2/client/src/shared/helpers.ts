import { isNil } from 'lodash';

/**
 * @param time time in ms
 */
export function sleep(time: number): Promise<null> {
  return new Promise((resolve) => {
    setTimeout(resolve, time);
  });
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

/**
 * Give a random string base on Math.random
 */
export function giveWeakRandomKey() {
  return Math.random().toString(16).slice(2);
}

type ScriptStatus = 'loading' | 'idle' | 'ready' | 'error';
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
export function copyToClipboard(str: string) {
  str = str.toString();

  const inputEl = document.createElement('textArea') as HTMLTextAreaElement;
  let copyOk = false;

  inputEl.value = str;
  document.body.append(inputEl);
  inputEl.select();

  try {
    copyOk = document.execCommand('Copy');
  } catch (e) {
    copyOk = false;
  }

  document.body.removeChild(inputEl);

  return copyOk;
}

export function saveBlob(blob: Blob, fileName: string) {
  const a = document.createElement('a');
  a.href = window.URL.createObjectURL(blob);
  a.download = fileName;
  a.dispatchEvent(new MouseEvent('click'));
}
