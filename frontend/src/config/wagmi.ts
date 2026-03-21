import { http, createConfig, createStorage, cookieStorage } from 'wagmi'
import { injected, metaMask, walletConnect } from 'wagmi/connectors'
import { base, baseSepolia, mainnet, sepolia } from 'wagmi/chains'

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'demo-project-id'

export const config = createConfig({
  chains: [baseSepolia, base, mainnet, sepolia],
  connectors: [
    injected(),
    metaMask(),
    walletConnect({ projectId }),
  ],
  transports: {
    [baseSepolia.id]: http('https://sepolia.base.org'),
    [base.id]: http(),
    [mainnet.id]: http(),
    [sepolia.id]: http(),
  },
  storage: createStorage({
    storage: cookieStorage,
  }),
  ssr: true,
})

declare module 'wagmi' {
  interface Register {
    config: typeof config
  }
}
