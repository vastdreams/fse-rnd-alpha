import { create } from "zustand"

interface AppState {
  // Selected company
  selectedTicker: string | null
  setSelectedTicker: (ticker: string | null) => void

  // Sidebar state
  sidebarOpen: boolean
  toggleSidebar: () => void

  // Search query
  searchQuery: string
  setSearchQuery: (query: string) => void

  // Filter state
  yearFilter: number | null
  setYearFilter: (year: number | null) => void

  sectorFilter: string | null
  setSectorFilter: (sector: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Selected company
  selectedTicker: null,
  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

  // Sidebar state
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  // Search query
  searchQuery: "",
  setSearchQuery: (query) => set({ searchQuery: query }),

  // Filter state
  yearFilter: null,
  setYearFilter: (year) => set({ yearFilter: year }),

  sectorFilter: null,
  setSectorFilter: (sector) => set({ sectorFilter: sector }),
}))

