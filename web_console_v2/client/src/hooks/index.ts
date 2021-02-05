import { ChangeEvent, useEffect, useState } from 'react';
import store from 'store2';
import keyboardjs, { KeyEvent } from 'keyboardjs';
import { useToggle } from 'react-use';
import PubSub from 'pubsub-js';

export function useInputChange<T>(defaultValue: T) {
  const [value, setState] = useState(defaultValue);

  function onChange(event: ChangeEvent) {
    setState(((event.target as HTMLInputElement).value as unknown) as T);
  }

  return [value, onChange];
}

/** Get local storage data and return an reactive state */
const _originalSetItem = localStorage.setItem;

localStorage.setItem = function (key, value) {
  const event: any = new Event('storageset');

  event.value = value;
  event.key = key;

  document.dispatchEvent(event);

  _originalSetItem.apply(this, [key, value]);
};

export function useReactiveLocalStorage<T>(key: string, initalValue?: T) {
  const [val, setter] = useState<T>(store.get(key, initalValue));

  useEffect(() => {
    function handler(event: any) {
      if (event.key === key) {
        setter(typeof val === 'object' ? JSON.parse(event.value) : event.value);
      }
    }

    document.addEventListener('storageset', handler, false);

    return () => document.removeEventListener('storageset', handler);
  }, [initalValue, key, val]);

  return [val];
}

export function useListenKeyboard(
  combination: string | string[],
  cb: (ev?: KeyboardEvent) => void,
  shouldDoublePress?: boolean,
) {
  const [isPressed, set] = useToggle(false);

  useEffect(() => {
    const down = (event?: KeyEvent) => {
      cb(event);
      set(true);
    };

    const up = () => set(false);

    keyboardjs.bind(combination, down, up, shouldDoublePress);

    return () => keyboardjs.unbind(combination, down, up);
  }, [combination, cb, set, shouldDoublePress]);

  return [isPressed];
}

export function useSubscribe(channel: string, cb: any, deps: any[] = []) {
  useEffect(() => {
    PubSub.subscribe(channel, cb);

    return () => PubSub.unsubscribe(channel);
  }, [cb, channel, deps]);
}
