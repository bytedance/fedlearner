import { ChangeEvent, useEffect, useState, useMemo, useRef, useCallback } from 'react';
import store from 'store2';
import { useRecoilValue } from 'recoil';
import keyboardjs, { KeyEvent } from 'keyboardjs';
import { useToggle, useUnmount } from 'react-use';
import PubSub from 'pubsub-js';
import { parse, stringify, IStringifyOptions, IParseOptions } from 'qs';
import { useHistory, useLocation } from 'react-router';

import { appFlag, systemInfoQuery } from 'stores/app';
import { projectState } from 'stores/project';

import logoWhite from 'assets/images/logo-white.png';
import logoBlack from 'assets/images/logo-black.png';
import logoBioland from 'assets/icons/logo-bioland.png';
import logoBiolandColoful from 'assets/icons/logo-bioland-colorful.svg';

import { FlagKey } from 'typings/flag';
import { useRecoilQuery } from './recoil';
import { useQuery } from 'react-query';
import { getProjectDetailById } from 'services/project';
import { ProjectBaseAbilitiesType, ProjectTaskType } from 'typings/project';

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const callback = useCallback((...inputs) => cb(...inputs), [channel, ...deps]);

  useEffect(() => {
    const token = PubSub.subscribe(channel, callback);

    return () => {
      PubSub.unsubscribe(token);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel, callback, deps.join('')]);
}

/**
 * Listen any element's size change
 */
export function useResizeObserver(callback: any) {
  const ref = useRef();

  const resizeObserver = useMemo(() => {
    return new ResizeObserver((entries: ResizeObserverEntry[]) => {
      for (const entry of entries) {
        if (entry.target === ref.current) {
          callback && callback();
        }
      }
    });
  }, [callback]);

  useEffect(() => {
    if (ref.current) {
      resizeObserver.observe((ref.current as unknown) as Element);
    }
  }, [ref, resizeObserver]);

  useUnmount(() => {
    resizeObserver.disconnect();
  });

  return ref;
}

export function useWhyDidYouUpdate(name: string, props: Record<any, any>) {
  // Get a mutable ref object where we can store props ...
  // ... for comparison next time this hook runs.
  const previousProps = useRef<typeof props>();
  useEffect(() => {
    if (previousProps.current) {
      // Get all keys from previous and current props
      const allKeys = Object.keys({ ...previousProps.current, ...props });
      // Use this object to keep track of changed props
      const changesObj: Record<any, any> = {};
      // Iterate through keys
      allKeys.forEach((key) => {
        // If previous is different from current
        if (previousProps.current?.[key] !== props[key]) {
          // Add to changesObj
          changesObj[key] = {
            from: previousProps.current?.[key],
            to: props[key],
          };
        }
      });
      // If changesObj not empty then output to console
      if (Object.keys(changesObj).length) {
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.log('[why-did-you-update]', name, changesObj);
        }
      }
    }
    // Finally update previousProps with current props for next hook call
    previousProps.current = props;
  });
}

export function useGetLogoSrc() {
  const appFlagValue = useRecoilValue(appFlag);

  let primaryLogo = logoWhite;
  let secondaryLogo = logoBlack;

  if (process.env.THEME === 'bioland') {
    primaryLogo = logoBioland;
    secondaryLogo = logoBiolandColoful;
  }

  const logoSrc = useMemo(() => {
    if (appFlagValue[FlagKey.LOGO_URL]) {
      return appFlagValue[FlagKey.LOGO_URL];
    }

    return primaryLogo;
  }, [appFlagValue, primaryLogo]);

  return { primaryLogo: logoSrc, secondaryLogo };
}

export function useGetThemeBioland() {
  return process.env.THEME === 'bioland';
}

interface UseUrlStateOptions {
  navigateMode?: 'push' | 'replace';
  parseConfig?: IParseOptions;
  stringifyConfig?: IStringifyOptions;
}

interface UrlState {
  [key: string]: any;
}

/**
 * A hook that stores the state into url query parameters
 */
export function useUrlState<S extends UrlState = UrlState>(
  initialState?: S | (() => S),
  options?: UseUrlStateOptions,
) {
  type state = Partial<{ [key in keyof S]: any }>;

  const {
    navigateMode = 'push',
    parseConfig = {
      ignoreQueryPrefix: true,
    },
    stringifyConfig = {
      addQueryPrefix: true,
    },
  } = options || {};
  const location = useLocation();
  const history = useHistory();

  const [, forceUpdate] = useState(false);

  const initialStateRef = useRef(
    typeof initialState === 'function' ? (initialState as () => S)() : initialState || {},
  );

  const parseConfigRef = useRef(parseConfig);

  const queryFromUrl = useMemo(() => {
    return parse(location.search, parseConfigRef.current);
  }, [location.search]);

  const targetQuery: state = useMemo(
    () => ({
      ...initialStateRef.current,
      ...queryFromUrl,
    }),
    [queryFromUrl],
  );

  const setState = (s: React.SetStateAction<state>) => {
    const newQuery = typeof s === 'function' ? (s as Function)(targetQuery) : s;

    // If the url search does not change after setState(), forceUpdate() is needed to trigger an update.
    forceUpdate((v) => !v);

    history[navigateMode]({
      hash: location.hash,
      search: stringify({ ...queryFromUrl, ...newQuery }, stringifyConfig) || '?',
    });
  };

  return [targetQuery, setState] as const;
}

interface UseTablePaginationWithUrlStateOptions {
  defaultPage?: number;
  defaultPageSize?: number;
  urlStateOption?: UseUrlStateOptions;
}

export function useTablePaginationWithUrlState(options?: UseTablePaginationWithUrlStateOptions) {
  const initialStateRef = useRef({
    page: String(options?.defaultPage || 1),
    pageSize: String(options?.defaultPageSize || 10),
  });

  const [urlState, setUrlState] = useUrlState(initialStateRef.current, options?.urlStateOption);

  function reset() {
    setUrlState((prevState) => ({
      ...prevState,
      ...initialStateRef.current,
    }));
  }
  function onChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }
  function onShowSizeChange(page: number, pageSize: number) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }

  return {
    urlState,
    setUrlState,
    reset,
    paginationProps: {
      pageSize: Number(urlState.pageSize),
      current: Number(urlState.page),
      onChange,
      onShowSizeChange,
      showTotal: (total: number) => `共 ${total} 条记录`,
    },
  };
}

// borrow from: https://github.com/alibaba/hooks/blob/master/packages/hooks/src/usePrevious/index.ts
type ShouldUpdateFunc<T> = (prev: T | undefined, next: T) => boolean;
const defaultShouldUpdate = <T>(a?: T, b?: T) => a !== b;
export function usePrevious<T>(
  state: T,
  shouldUpdate: ShouldUpdateFunc<T> = defaultShouldUpdate,
): T | undefined {
  const prevRef = useRef<T>();
  const curRef = useRef<T>();

  if (shouldUpdate(curRef.current, state)) {
    prevRef.current = curRef.current;
    curRef.current = state;
  }

  return prevRef.current;
}

export function useInterval(
  fn: () => void,
  delay: number | undefined,
  options?: {
    immediate?: boolean;
  },
) {
  const immediate = options?.immediate;
  const fnRef = useRef<() => void>();
  fnRef.current = fn;

  useEffect(() => {
    if (typeof delay !== 'number' || delay <= 0) return;
    if (immediate) {
      fnRef.current?.();
    }
    const timer = setInterval(() => {
      fnRef.current?.();
    }, delay);
    return () => {
      clearInterval(timer);
    };
  }, [delay, immediate]);
}

export function useIsFormValueChange(cb?: Function) {
  const [isFormValueChanged, setIsFormValueChanged] = useState(false);

  function onValuesChange(...args: any[]) {
    if (!isFormValueChanged) {
      setIsFormValueChanged(true);
    }
    cb?.(...args);
  }
  function resetChangedState() {
    setIsFormValueChanged(false);
  }
  return {
    isFormValueChanged: isFormValueChanged,
    onFormValueChange: onValuesChange,
    resetChangedState,
  };
}

/* istanbul ignore next */
export function useGetCurrentProjectId() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.id;
}
export function useGetCurrentUserName() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.creator;
}
/* istanbul ignore next */
export function useGetCurrentProjectParticipantId() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.participants?.[0]?.id;
}

/* istanbul ignore next */
export function useGetCurrentProjectParticipantList() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.participants ?? [];
}
/* istanbul ignore next */
export function useGetCurrentProjectParticipantName() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.participants?.[0]?.name ?? '';
}
/* istanbul ignore next */
export function useGetCurrentParticipantPureDomainName() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.participants?.[0]?.pure_domain_name ?? '';
}
/* istanbul ignore next */
export function useGetCurrentProjectType() {
  const selectedProject = useRecoilValue(projectState);
  return selectedProject.current?.participant_type;
}
/* istanbul ignore next */
export function useGetCurrentDomainName() {
  const { data: systemInfo } = useRecoilQuery(systemInfoQuery);
  return systemInfo?.domain_name ?? '';
}
/* istanbul ignore next */
export function useGetCurrentPureDomainName() {
  const { data: systemInfo } = useRecoilQuery(systemInfoQuery);
  return systemInfo?.pure_domain_name ?? '';
}

/* istanbul ignore next */
export function useGetAppFlagValue(flagKey?: FlagKey) {
  const appFlagValue = useRecoilValue(appFlag);
  return flagKey ? appFlagValue[flagKey] : appFlagValue;
}

export function useGetCurrentProjectAbilityConfig(): {
  abilities: (ProjectTaskType | ProjectBaseAbilitiesType)[] | undefined;
  action_rules: any;
  hasIdAlign: Boolean;
  hasHorizontal: Boolean;
  hasVertical: Boolean;
  hasTrusted: Boolean;
} {
  const projectId = useGetCurrentProjectId();
  const projectDetailQuery = useQuery(
    ['getProjectDetailById', projectId],
    () => getProjectDetailById(projectId!),
    {
      enabled: Boolean(projectId),
      retry: 2,
    },
  );
  const { abilities, action_rules } = useMemo(() => {
    if (projectDetailQuery.isLoading) {
      return { abilities: [], action_rules: {} };
    }
    if (!projectId) {
      return { abilities: [ProjectBaseAbilitiesType.BASE], action_rules: {} };
    }
    const projectConfig = projectDetailQuery.data?.data.config;
    return {
      // If the user  select  a old project, it will be used as “VERTICAL”
      abilities: projectConfig?.abilities?.length
        ? projectConfig?.abilities
        : [ProjectTaskType.VERTICAL],
      // todo: old project action_rules define
      action_rules: projectConfig?.action_rules,
    };
  }, [projectDetailQuery, projectId]);
  return {
    abilities,
    action_rules,
    hasIdAlign: (abilities as ProjectTaskType[])?.includes(ProjectTaskType.ALIGN), // 是否有ID对齐能力
    hasHorizontal: (abilities as ProjectTaskType[])?.includes(ProjectTaskType.HORIZONTAL), // 是否有横向联邦能力
    hasVertical: (abilities as ProjectTaskType[])?.includes(ProjectTaskType.VERTICAL), // 是否有纵向联邦能力
    hasTrusted: (abilities as ProjectTaskType[])?.includes(ProjectTaskType.TRUSTED), // 是否有可信分析能力
  };
}
