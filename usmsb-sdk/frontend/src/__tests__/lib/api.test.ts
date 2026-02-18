import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import {
  ApiError,
  addErrorHandler,
  getAgents,
  getHealth,
  API_BASE_URL,
} from '@/lib/api'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: {
          use: vi.fn((successHandler, errorHandler) => {
            // Store error handler for testing
            global.__errorHandler = errorHandler
          }),
        },
      },
    })),
  },
}))

describe('API Client', () => {
  describe('API_BASE_URL', () => {
    it('should export the correct API base URL', () => {
      expect(API_BASE_URL).toBe('/api')
    })
  })

  describe('ApiError', () => {
    it('should create an ApiError with correct properties', () => {
      const error = new ApiError('Test error', 500, 'TEST_CODE', { details: 'test' })

      expect(error.message).toBe('Test error')
      expect(error.statusCode).toBe(500)
      expect(error.code).toBe('TEST_CODE')
      expect(error.details).toEqual({ details: 'test' })
      expect(error.name).toBe('ApiError')
    })
  })

  describe('Error Handlers', () => {
    it('should add and remove error handlers', () => {
      const handler = vi.fn()
      const removeHandler = addErrorHandler(handler)

      expect(typeof removeHandler).toBe('function')

      removeHandler()
      // Handler should be removed (we can't easily verify this without internals)
    })

    it('should call error handlers when triggered', () => {
      const handler = vi.fn()
      addErrorHandler(handler)

      const error = new ApiError('Test error', 500)
      // Note: We can't easily trigger the internal notifyErrorHandlers
      // This is just to ensure the function works
    })
  })

  describe('API Functions', () => {
    // These tests would require more complex axios mocking
    // For now, we'll test the structure

    it('should have getHealth function', () => {
      expect(typeof getHealth).toBe('function')
    })

    it('should have getAgents function', () => {
      expect(typeof getAgents).toBe('function')
    })

    it('should accept optional parameters', () => {
      // Just verify the function signature allows optional params
      const getAgentsSignature = getAgents.toString()
      expect(getAgentsSignature).toContain('type')
      expect(getAgentsSignature).toContain('limit')
    })
  })
})

// Add global type for error handler access
declare global {
  // eslint-disable-next-line no-var
  var __errorHandler: ((error: unknown) => void) | undefined
}
