// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { act, renderHook, RenderHookResult } from '@testing-library/react-hooks';
import routeData from 'react-router';

import { useUrlState, useTablePaginationWithUrlState, useIsFormValueChange } from './index';

describe('useUrlState/useTablePaginationWithUrlState', () => {
  it('should be defined', () => {
    expect(useUrlState).toBeDefined();
    expect(useTablePaginationWithUrlState).toBeDefined();
  });

  const replaceFn = jest.fn();

  let mockLocation = {
    pathname: '/',
    hash: '',
    search: '',
    state: '',
  };

  const mockHistory: any = {
    push: ({ search }: any) => {
      replaceFn();
      mockLocation.search = search;
    },
  };

  beforeEach(() => {
    jest.spyOn(routeData, 'useLocation').mockReturnValue(mockLocation);
    jest.spyOn(routeData, 'useHistory').mockReturnValue(mockHistory);
  });

  afterEach(() => {
    replaceFn.mockClear();
    mockLocation = {
      pathname: '/',
      hash: '',
      search: '',
      state: '',
    };
  });

  describe('useUrlState', () => {
    it('history replace should work', async () => {
      const hook = renderHook(() => {
        return useUrlState({ mock: '0' });
      }) as any;

      // If const [urlState, setUrlState] = hook.result.current, urlState is the oldest data after invoking setUrlState
      // hook.result.current[0] meaning the lastest data
      const [, setUrlState] = hook.result.current;

      expect(replaceFn).toBeCalledTimes(0);
      expect(hook.result.current[0]).toEqual({ mock: '0' });
      expect(mockLocation.search).toEqual('');
      act(() => {
        setUrlState({ mock: 1 });
      });
      expect(hook.result.current[0]).toEqual({ mock: '1' });

      expect(replaceFn).toBeCalledTimes(1);
      expect(mockLocation.search).toEqual('?mock=1');
      act(() => {
        setUrlState({ mock: 2, test: 3 });
      });
      expect(hook.result.current[0]).toEqual({ mock: '2', test: '3' });
      expect(mockLocation.search).toEqual('?mock=2&test=3');
    });
  });

  describe('useTablePaginationWithUrlState', () => {
    it('default options', async () => {
      const hook: RenderHookResult<
        any,
        ReturnType<typeof useTablePaginationWithUrlState>
      > = renderHook(() => {
        return useTablePaginationWithUrlState();
      }) as any;

      expect(hook.result.current).toMatchObject({
        urlState: expect.objectContaining({
          page: '1',
          pageSize: '10',
        }),
        setUrlState: expect.any(Function),
        reset: expect.any(Function),
        paginationProps: expect.objectContaining({
          current: 1,
          pageSize: 10,
          onChange: expect.any(Function),
          onShowSizeChange: expect.any(Function),
        }),
      });

      act(() => {
        hook.result.current.paginationProps.onChange(2, 10);
      });

      expect(hook.result.current.urlState).toEqual({
        page: '2',
        pageSize: '10',
      });
      expect(hook.result.current.paginationProps).toMatchObject({
        current: 2,
        pageSize: 10,
      });

      act(() => {
        hook.result.current.paginationProps.onShowSizeChange(3, 20);
      });

      expect(hook.result.current.urlState).toEqual({
        page: '3',
        pageSize: '20',
      });
      expect(hook.result.current.paginationProps).toMatchObject({
        current: 3,
        pageSize: 20,
      });

      act(() => {
        hook.result.current.reset();
      });
      expect(hook.result.current.urlState).toEqual({
        page: '1',
        pageSize: '10',
      });
      expect(hook.result.current.paginationProps).toMatchObject({
        current: 1,
        pageSize: 10,
      });
    });

    it('custom options', async () => {
      const hook: RenderHookResult<
        any,
        ReturnType<typeof useTablePaginationWithUrlState>
      > = renderHook(() => {
        return useTablePaginationWithUrlState({
          defaultPage: 2,
          defaultPageSize: 15,
        });
      }) as any;

      expect(hook.result.current.urlState).toEqual({
        page: '2',
        pageSize: '15',
      });

      act(() => {
        hook.result.current.paginationProps.onChange(2, 10);
      });

      expect(hook.result.current.urlState).toEqual({
        page: '2',
        pageSize: '10',
      });
      expect(hook.result.current.paginationProps).toMatchObject({
        current: 2,
        pageSize: 10,
      });

      act(() => {
        hook.result.current.reset();
      });
      expect(hook.result.current.urlState).toEqual({
        page: '2',
        pageSize: '15',
      });
      expect(hook.result.current.paginationProps).toMatchObject({
        current: 2,
        pageSize: 15,
      });
    });
  });
});
it('useIsFormValueChange', () => {
  const mockFn = jest.fn();

  const { result } = renderHook(() => {
    return useIsFormValueChange(mockFn);
  });

  expect(result.current.isFormValueChanged).toBe(false);
  expect(mockFn).toBeCalledTimes(0);

  act(() => {
    result.current.onFormValueChange();
  });

  expect(result.current.isFormValueChanged).toBe(true);
  expect(mockFn).toBeCalledTimes(1);

  act(() => {
    result.current.resetChangedState();
  });

  expect(result.current.isFormValueChanged).toBe(false);
  expect(mockFn).toBeCalledTimes(1);
});
