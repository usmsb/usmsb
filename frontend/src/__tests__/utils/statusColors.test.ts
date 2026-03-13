import { describe, it, expect } from 'vitest'
import {
  getStatusColor,
  getStatusBgColor,
  getStatusTextColor,
  getMatchScoreColor,
  getMatchScoreBgColor,
  getReputationColor,
} from '@/utils/statusColors'

describe('statusColors', () => {
  describe('getStatusColor', () => {
    it('should return correct color for online status', () => {
      const result = getStatusColor('online')
      expect(result).toContain('bg-green-100')
      expect(result).toContain('text-green-700')
    })

    it('should return correct color for offline status', () => {
      const result = getStatusColor('offline')
      expect(result).toContain('bg-gray-100')
      expect(result).toContain('text-gray-700')
    })

    it('should return correct color for busy status', () => {
      const result = getStatusColor('busy')
      expect(result).toContain('bg-yellow-100')
      expect(result).toContain('text-yellow-700')
    })

    it('should return correct color for discovered opportunity status', () => {
      const result = getStatusColor('discovered')
      expect(result).toContain('bg-blue-100')
      expect(result).toContain('text-blue-700')
    })

    it('should return correct color for accepted status', () => {
      const result = getStatusColor('accepted')
      expect(result).toContain('bg-green-100')
      expect(result).toContain('text-green-700')
    })

    it('should return correct color for rejected status', () => {
      const result = getStatusColor('rejected')
      expect(result).toContain('bg-red-100')
      expect(result).toContain('text-red-700')
    })

    it('should return default color for unknown status', () => {
      const result = getStatusColor('unknown_status')
      expect(result).toContain('bg-gray-100')
      expect(result).toContain('text-gray-700')
    })

    it('should include dark mode classes', () => {
      const result = getStatusColor('online')
      expect(result).toContain('dark:bg-green-900/30')
      expect(result).toContain('dark:text-green-400')
    })
  })

  describe('getStatusBgColor', () => {
    it('should return only background color classes', () => {
      const result = getStatusBgColor('online')
      expect(result).toContain('bg-green-100')
      expect(result).not.toContain('text-green-700')
    })
  })

  describe('getStatusTextColor', () => {
    it('should return only text color classes', () => {
      const result = getStatusTextColor('online')
      expect(result).toContain('text-green-700')
      expect(result).not.toContain('bg-green-100')
    })
  })

  describe('getMatchScoreColor', () => {
    it('should return green for high scores (>= 0.8)', () => {
      const result = getMatchScoreColor(0.9)
      expect(result).toContain('text-green-500')
    })

    it('should return blue for medium-high scores (>= 0.6 and < 0.8)', () => {
      const result = getMatchScoreColor(0.7)
      expect(result).toContain('text-blue-500')
    })

    it('should return yellow for medium scores (>= 0.4 and < 0.6)', () => {
      const result = getMatchScoreColor(0.5)
      expect(result).toContain('text-yellow-500')
    })

    it('should return red for low scores (< 0.4)', () => {
      const result = getMatchScoreColor(0.3)
      expect(result).toContain('text-red-500')
    })
  })

  describe('getMatchScoreBgColor', () => {
    it('should return green background for high scores', () => {
      const result = getMatchScoreBgColor(0.9)
      expect(result).toContain('bg-green-500/20')
    })

    it('should return red background for low scores', () => {
      const result = getMatchScoreBgColor(0.2)
      expect(result).toContain('bg-red-500/20')
    })
  })

  describe('getReputationColor', () => {
    it('should return green for high reputation (>= 80)', () => {
      const result = getReputationColor(90)
      expect(result).toContain('text-green-500')
    })

    it('should return blue for medium-high reputation (>= 60 and < 80)', () => {
      const result = getReputationColor(70)
      expect(result).toContain('text-blue-500')
    })

    it('should return yellow for medium reputation (>= 40 and < 60)', () => {
      const result = getReputationColor(50)
      expect(result).toContain('text-yellow-500')
    })

    it('should return red for low reputation (< 40)', () => {
      const result = getReputationColor(30)
      expect(result).toContain('text-red-500')
    })
  })
})
