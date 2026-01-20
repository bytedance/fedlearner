import { useState, useRef, useCallback } from 'react';

export function useSearchBox() {
  const filterTimer: any = useRef();

  const [filter, setFilter] = useState('');

  const onFilterChange = useCallback((value: string, e: any) => {
    clearTimeout(filterTimer.current);

    filterTimer.current = setTimeout(() => {
      setFilter(value);
    }, 400);
  }, []);

  const onInputKeyPress = useCallback((evt: React.KeyboardEvent) => {
    if (evt.key === 'Enter') evt.preventDefault();
  }, []);

  return {
    onFilterChange,
    filter,
    onInputKeyPress,
  };
}
