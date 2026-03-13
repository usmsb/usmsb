import { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { vi } from 'vitest'
import userEvent from '@testing-library/user-event'

/**
 * Custom render function that includes all necessary providers
 */
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return {
    user: userEvent.setup(),
    ...render(ui, options),
  }
}

/**
 * Create a mock function with typed return value
 */
function createMockFn<T = unknown>(): ReturnType<typeof vi.fn<T>> {
  return vi.fn()
}

/**
 * Wait for a condition to be true
 */
async function waitForCondition(
  condition: () => boolean,
  timeout = 1000
): Promise<void> {
  const start = Date.now()
  while (!condition()) {
    if (Date.now() - start > timeout) {
      throw new Error('Timeout waiting for condition')
    }
    await new Promise((resolve) => setTimeout(resolve, 10))
  }
}

/**
 * Mock API response
 */
function mockApiResponse<T>(data: T, status = 200) {
  return Promise.resolve({
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as any,
  })
}

/**
 * Mock API error
 */
function mockApiError(message: string, status = 500) {
  return Promise.reject({
    response: {
      data: { message },
      status,
    },
    message,
  })
}

export * from '@testing-library/react'
export { customRender as render, createMockFn, waitForCondition, mockApiResponse, mockApiError }
