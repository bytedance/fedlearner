import { ServerError } from 'libs/request';
import { RecoilValue, useRecoilValueLoadable } from 'recoil';

export function useRecoilQuery<T>(recoilValue: RecoilValue<T>) {
  const loadable = useRecoilValueLoadable(recoilValue);
  return {
    data: loadable.state === 'hasValue' ? loadable.contents : (undefined as never),
    isLoading: loadable.state === 'loading',
    error: loadable.state === 'hasError' ? (loadable.errorOrThrow() as ServerError) : null,
  };
}
