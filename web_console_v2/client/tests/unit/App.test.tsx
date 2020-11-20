import React from 'react'
import { render, screen } from '@testing-library/react'
import App from '../../src/App'

test('renders', () => {
  render(<App />)
  const view = screen.getByText(/❤️/i)
  expect(view).toBeInTheDocument()
})
