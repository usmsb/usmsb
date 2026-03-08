import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import GeneCapsuleExplore from '@/pages/GeneCapsuleExplore'
import * as api from '@/lib/api'

// Mock the API module
vi.mock('@/lib/api', () => ({
  searchAgentsByExperience: vi.fn(),
}))

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

const mockSearchResults = [
  {
    agent_id: 'agent-1',
    agent_name: 'Test Agent',
    overall_relevance: 0.85,
    matched_experiences: [
      {
        experience: { task_description: 'Built a React app' },
        relevance_score: 0.9,
        matching_skills: ['React', 'TypeScript'],
      },
    ],
    verified_experiences_count: 5,
    total_experience_value: 120,
  },
  {
    agent_id: 'agent-2',
    agent_name: 'Another Agent',
    overall_relevance: 0.72,
    matched_experiences: [
      {
        experience: { task_description: 'Python data analysis' },
        relevance_score: 0.8,
        matching_skills: ['Python', 'Pandas'],
      },
    ],
    verified_experiences_count: 3,
    total_experience_value: 85,
  },
]

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

describe('GeneCapsuleExplore - Theme Consistency', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Theme Classes', () => {
    it('uses theme-aware text colors', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // Check for theme-aware classes (light/dark pattern)
      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading.className).toMatch(/text-light-text-primary|dark:/)
    })

    it('uses theme-aware secondary text colors', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // Check for secondary text with dark mode variant
      const descriptions = document.querySelectorAll('[class*="text-secondary"]')
      expect(descriptions.length).toBeGreaterThan(0)
    })

    it('uses card class for containers', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // Check for card class usage
      const cards = document.querySelectorAll('[class*="card"]')
      expect(cards.length).toBeGreaterThan(0)
    })

    it('uses btn classes for buttons', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // Check for btn class usage
      const buttons = document.querySelectorAll('[class*="btn"]')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })

  describe('Initial State', () => {
    it('shows initial state before search', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      expect(screen.getByText('Discover Agent Capabilities')).toBeInTheDocument()
    })

    it('shows DNA icon in initial state', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // The Dna icon should be present
      const initialIcon = document.querySelector('[class*="rounded-full"]')
      expect(initialIcon).toBeInTheDocument()
    })
  })

  describe('Search Functionality', () => {
    it('has search input with theme-aware styles', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      const searchInput = screen.getByPlaceholderText(/describe the task/i)
      expect(searchInput).toBeInTheDocument()

      // Check for theme-aware input styles
      expect(searchInput.className).toMatch(/bg-white|dark:bg-gray/)
    })

    it('search button is styled correctly', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      const searchButton = screen.getByRole('button', { name: /search/i })
      expect(searchButton).toBeInTheDocument()
      expect(searchButton.className).toMatch(/btn/)
    })

    it('performs search on button click', async () => {
      vi.mocked(api.searchAgentsByExperience).mockResolvedValueOnce(mockSearchResults)

      renderWithRouter(<GeneCapsuleExplore />)

      const searchInput = screen.getByPlaceholderText(/describe the task/i)
      fireEvent.change(searchInput, { target: { value: 'React developer' } })

      const searchButton = screen.getByRole('button', { name: /search/i })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(api.searchAgentsByExperience).toHaveBeenCalledWith(
          'React developer',
          [],
          0.2,
          20
        )
      })
    })

    it('shows loading state during search', async () => {
      vi.mocked(api.searchAgentsByExperience).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve([]), 100))
      )

      renderWithRouter(<GeneCapsuleExplore />)

      const searchInput = screen.getByPlaceholderText(/describe the task/i)
      fireEvent.change(searchInput, { target: { value: 'test' } })

      const searchButton = screen.getByRole('button', { name: /search/i })
      fireEvent.click(searchButton)

      // Should show loading spinner
      await waitFor(() => {
        expect(screen.getByText(/searching/i)).toBeInTheDocument()
      })
    })
  })

  describe('Skill Filters', () => {
    it('allows adding skill filters', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      const skillInput = screen.getByPlaceholderText(/add skill/i)
      fireEvent.change(skillInput, { target: { value: 'React' } })

      const addButton = screen.getByText(/\+ add/i)
      fireEvent.click(addButton)

      expect(screen.getByText('React')).toBeInTheDocument()
    })

    it('skill filter tags use theme-aware colors', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      const skillInput = screen.getByPlaceholderText(/add skill/i)
      fireEvent.change(skillInput, { target: { value: 'TypeScript' } })

      const addButton = screen.getByText(/\+ add/i)
      fireEvent.click(addButton)

      const skillTag = screen.getByText('TypeScript')
      expect(skillTag.className).toMatch(/bg-blue-100|dark:bg-blue-900/)
    })

    it('allows removing skill filters', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // Add a skill first
      const skillInput = screen.getByPlaceholderText(/add skill/i)
      fireEvent.change(skillInput, { target: { value: 'Node.js' } })
      fireEvent.click(screen.getByText(/\+ add/i))

      expect(screen.getByText('Node.js')).toBeInTheDocument()

      // Remove it
      const removeButton = screen.getByText('Node.js').parentElement?.querySelector('button')
      if (removeButton) {
        fireEvent.click(removeButton)
      }

      expect(screen.queryByText('Node.js')).not.toBeInTheDocument()
    })
  })

  describe('View Mode Toggle', () => {
    it('has grid and list view options', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      // Find view toggle buttons
      const viewButtons = document.querySelectorAll('[class*="rounded"]')
      expect(viewButtons.length).toBeGreaterThan(0)
    })
  })

  describe('Sort Options', () => {
    it('has sort dropdown with theme-aware styles', () => {
      renderWithRouter(<GeneCapsuleExplore />)

      const sortSelect = screen.getByRole('combobox')
      expect(sortSelect).toBeInTheDocument()
      expect(sortSelect.className).toMatch(/bg-white|dark:bg-gray/)
    })
  })

  describe('Error Handling', () => {
    it('shows error with theme-aware styles', async () => {
      vi.mocked(api.searchAgentsByExperience).mockRejectedValueOnce(new Error('Search failed'))

      renderWithRouter(<GeneCapsuleExplore />)

      const searchInput = screen.getByPlaceholderText(/describe the task/i)
      fireEvent.change(searchInput, { target: { value: 'test' } })
      fireEvent.click(screen.getByRole('button', { name: /search/i }))

      await waitFor(() => {
        const errorElement = screen.getByText(/search failed/i)
        expect(errorElement).toBeInTheDocument()
        // Check parent element for theme-aware styles
        const parent = errorElement.closest('[class*="bg-red"]')
        expect(parent).toBeInTheDocument()
      })
    })
  })

  describe('Search Results', () => {
    it('displays results with theme-aware styles', async () => {
      vi.mocked(api.searchAgentsByExperience).mockResolvedValueOnce(mockSearchResults)

      renderWithRouter(<GeneCapsuleExplore />)

      const searchInput = screen.getByPlaceholderText(/describe the task/i)
      fireEvent.change(searchInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /search/i }))

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument()
      })

      // Check result card uses card class
      const resultCard = screen.getByText('Test Agent').closest('[class*="card"]')
      expect(resultCard).toBeInTheDocument()
    })

    it('shows no results state when empty', async () => {
      vi.mocked(api.searchAgentsByExperience).mockResolvedValueOnce([])

      renderWithRouter(<GeneCapsuleExplore />)

      const searchInput = screen.getByPlaceholderText(/describe the task/i)
      fireEvent.change(searchInput, { target: { value: 'xyz123' } })
      fireEvent.click(screen.getByRole('button', { name: /search/i }))

      await waitFor(() => {
        expect(screen.getByText(/no agents found/i)).toBeInTheDocument()
      })
    })
  })
})
