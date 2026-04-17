# USMSB Distributed Inference - Frontend Specification

## 1. Project Overview

**Project**: USMSB Distributed Inference Frontend
**Type**: Real-time monitoring dashboard for GPU inference network
**Stack**: Vite + React 18 + TypeScript + Tailwind CSS
**Target Users**: Platform operators (Global Scheduler) and GPU node owners (Node Executor)

## 2. Design System

### 2.1 Color Palette (Cyberpunk)

| Token | Hex | Usage |
|-------|-----|-------|
| `--cyber-dark` | #0a0a0f | Page background |
| `--cyber-card` | #0d0d14 | Card background |
| `--cyber-border` | #1a1a2e | Card/element borders |
| `--neon-blue` | #00f5ff | Primary accent, links, active states |
| `--neon-purple` | #bf00ff | Secondary accent, gradients |
| `--neon-green` | #00ff88 | Success, positive metrics |
| `--neon-pink` | #ff00ff | Tertiary accent, highlights |
| `--neon-red` | #ff0044 | Errors, critical alerts |
| `--neon-yellow` | #ffd700 | Warnings |
| `--text-primary` | #e0e0ff | Primary text |
| `--text-secondary` | #8888aa | Secondary/muted text |

### 2.2 Typography

| Role | Font | Fallback |
|------|------|---------|
| Headings / Logo | Orbitron | sans-serif |
| Body / UI Labels | Rajdhani | sans-serif |
| Data / Code / Addresses | JetBrains Mono | monospace |

### 2.3 Visual Effects

- **Grid background**: 50px CSS grid lines, subtle opacity
- **Scanlines**: CSS pseudo-element overlay with repeating gradient
- **Neon glow**: `text-shadow` / `box-shadow` with accent colors
- **Glassmorphism**: `backdrop-filter: blur()` on cards and modals
- **Gradient borders**: 1px border with `linear-gradient` on cards
- **Scrollbar**: Thin, neon-gradient track

### 2.4 Spacing & Layout

- Base unit: 4px
- Card padding: 16px (mobile) / 24px (desktop)
- Section gap: 24px
- Sidebar width: 240px (desktop)
- Mobile tab bar height: 56px + safe-area

## 3. Breakpoints (Tailwind)

| Name | Min-width | Target |
|------|-----------|--------|
| `sm` | 640px | Large phones, small tablets |
| `md` | 768px | Tablets |
| `lg` | 1024px | Laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1536px | Large screens |

## 4. Application Structure

### 4.1 Global Scheduler (Platform Admin)
Routes under `/`:

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | DashboardPage | System overview, KPIs, live queue |
| `/nodes` | NodesPage | GPU node list |
| `/nodes/:nodeId` | NodeDetailPage | Single node detail |
| `/models` | ModelsPage | Model registry |
| `/requests` | RequestsPage | Inference request list |
| `/requests/:id` | RequestDetailPage | Request detail |
| `/revenue` | RevenuePage | Revenue center |
| `/users` | UsersPage | Wallet user list |
| `/users/:wallet` | UserDetailPage | User detail |
| `/monitor` | MonitorPage | Real-time monitoring |
| `/settings` | SettingsPage | Platform settings |

### 4.2 Node Executor (GPU Operator)
Routes under `/node`:

| Route | Component | Description |
|-------|-----------|-------------|
| `/node` | NodeDashboardPage | Node status overview |
| `/node/revenue` | NodeRevenuePage | Earnings breakdown |
| `/node/models` | NodeModelsPage | Model management |
| `/node/history` | NodeHistoryPage | Inference history |
| `/node/settings` | NodeSettingsPage | Node configuration |

## 5. Authentication

- **Wallet-only**: No email/phone
- **Method**: wagmi + viem + SIWE (Sign-In With Ethereum)
- **User identity**: Ethereum wallet address (0x...)
- **Roles**: Platform Admin, Node Owner, API User, Guest

## 6. Settlement

- **Currency**: VIBE token
- All amounts displayed in VIBE
- Blockchain-based settlement records

## 7. Real-time Data

- **Protocol**: Server-Sent Events (SSE)
- **Endpoints**: `/api/sse/gpu-pool`, `/api/sse/requests`, `/api/sse/node/:id/gpu`
- **Reconnection**: Exponential backoff (1s → 2s → 4s → max 30s)
- **Mobile**: visibilitychange detection for background/foreground切换

## 8. Component Library

### Layout
- `Sidebar` — Desktop left navigation (hidden on mobile)
- `MobileTabBar` — Bottom tab bar (mobile only)
- `TopBar` — Logo + wallet + notifications (desktop)

### Data Display
- `MetricCard` — KPI card with value + trend + progress bar
- `DataTable` — Sortable, filterable, responsive table
- `ProgressBar` — VRAM/GPU utilization bar with neon fill
- `WalletAddress` — Truncated address with copy button

### Charts
- `AreaChart` — Revenue/inference trends (Recharts Area)
- `BarChart` — Earnings composition (Recharts Bar)
- `PieChart` — Revenue breakdown (Recharts Pie)

### Forms
- `CyberInput` — Styled input with neon focus ring
- `CyberSelect` — Dropdown select
- `CyberButton` — Primary/secondary/ghost variants

### Feedback
- `Badge` — Status badges (idle/busy/offline/loading)
- `Toast` — Notification toasts
- `Modal` — Glassmorphic modal dialog

## 9. Technical Stack

| Package | Version | Purpose |
|---------|---------|---------|
| vite | ^5.x | Build tool |
| react | ^18.x | UI framework |
| typescript | ^5.x | Type safety |
| tailwindcss | ^3.x | Styling |
| react-router-dom | ^6.x | Routing |
| recharts | ^2.x | Charts |
| zustand | ^4.x | State management |
| wagmi | ^2.x | Wallet connection |
| viem | ^2.x | Ethereum client |
| siwe | ^2.x | Sign-In With Ethereum |
| framer-motion | ^11.x | Animations |
| lucide-react | ^0.4.x | Icons |
| @tanstack/react-query | ^5.x | Server state |
| date-fns | ^3.x | Date formatting |
| axios | ^1.x | HTTP client |
| react-hot-toast | ^2.x | Toast notifications |

## 10. File Structure

```
frontend/
├── SPEC.md
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── public/
│   └── fonts/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── lib/
│   │   ├── api.ts           # Axios instance + API calls
│   │   ├── sse.ts           # SSE client
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useSSE.ts
│   │   ├── useGpuPool.ts
│   │   ├── useRequests.ts
│   │   └── useRevenue.ts
│   ├── store/
│   │   ├── authStore.ts     # Wallet auth state
│   │   ├── gpuPoolStore.ts  # GPU nodes state
│   │   └── uiStore.ts       # UI state (sidebar, theme)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── MobileTabBar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   └── AppShell.tsx
│   │   ├── ui/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── DataTable.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── WalletAddress.tsx
│   │   │   ├── CyberInput.tsx
│   │   │   ├── CyberButton.tsx
│   │   │   ├── CyberSelect.tsx
│   │   │   └── Modal.tsx
│   │   └── charts/
│   │       ├── AreaTrendChart.tsx
│   │       ├── EarningsBarChart.tsx
│   │       └── RevenuePieChart.tsx
│   ├── pages/
│   │   ├── scheduler/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── NodesPage.tsx
│   │   │   ├── NodeDetailPage.tsx
│   │   │   ├── ModelsPage.tsx
│   │   │   ├── RequestsPage.tsx
│   │   │   ├── RequestDetailPage.tsx
│   │   │   ├── RevenuePage.tsx
│   │   │   ├── UsersPage.tsx
│   │   │   ├── UserDetailPage.tsx
│   │   │   ├── MonitorPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── executor/
│   │   │   ├── NodeDashboardPage.tsx
│   │   │   ├── NodeRevenuePage.tsx
│   │   │   ├── NodeModelsPage.tsx
│   │   │   ├── NodeHistoryPage.tsx
│   │   │   └── NodeSettingsPage.tsx
│   │   └── auth/
│   │       └── LoginPage.tsx
│   └── types/
│       ├── api.ts
│       ├── gpu.ts
│       ├── models.ts
│       └── user.ts
└── env.example
```
