import { ChangeEvent, useState } from 'react'

export function useInputChange<T>(defaultValue: T) {
  const [value, setState] = useState(defaultValue)

  function onChange(event: ChangeEvent) {
    setState(((event.target as HTMLInputElement).value as unknown) as T)
  }

  return [value, onChange]
}
