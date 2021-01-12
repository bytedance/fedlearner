import { RecoilValue, useRecoilValueLoadable } from 'recoil';

export function useRecoilQuery<T>(recoilValue: RecoilValue<T>) {
  const loadable = useRecoilValueLoadable<T>(recoilValue);

  return {
    data: loadable.state === 'hasValue' ? loadable.contents : null,
    isLoading: loadable.state === 'loading',
    error: loadable.state === 'hasError' ? loadable.errorOrThrow() : null,
  };
}
