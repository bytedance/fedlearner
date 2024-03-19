/* istanbul ignore file */

import { waitFor, RenderResult, fireEvent } from '@testing-library/react';

export async function waitForLoadingEnd(wrapper: RenderResult) {
  // Start fetch async data, so loading should be displayed
  await waitFor(() => expect(wrapper.container.querySelector('.arco-spin-icon')).toBeVisible());

  // End fetch async data, so loading should be removed
  await waitFor(() =>
    expect(wrapper.container.querySelector('.arco-spin-icon')).not.toBeInTheDocument(),
  );
}

export function typeInput(input: HTMLElement, value: string | number) {
  fireEvent.change(input, {
    target: { value },
  });
}
