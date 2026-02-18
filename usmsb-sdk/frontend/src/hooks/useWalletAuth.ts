import { useCallback, useState } from 'react'
import { useAccount, useConnect, useDisconnect, useSignMessage, useChainId } from 'wagmi'
import { SiweMessage } from 'siwe'
import { useAuthStore } from '../stores/authStore'
import { getNonce, verifySignature, getSession, logout as apiLogout } from '../services/authService'

export function useWalletAuth() {
  const { address, isConnected, connector } = useAccount()
  const { connect, connectors, isPending: isConnecting } = useConnect()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()
  const chainId = useChainId()

  const {
    setWallet,
    setDid,
    setSession,
    setAgent,
    setRole,
    setProfile,
    logout: clearAuth,
    sessionId,
    accessToken,
  } = useAuthStore()

  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)

  // Connect wallet and authenticate
  const connectAndAuth = useCallback(async (connectorIndex = 0) => {
    setAuthError(null)
    setIsAuthenticating(true)

    try {
      // Connect wallet
      const selectedConnector = connectors[connectorIndex]
      if (!selectedConnector) {
        throw new Error('No connector available')
      }

      await connect({ connector: selectedConnector })
    } catch (error) {
      console.error('Connection error:', error)
      setAuthError(error instanceof Error ? error.message : 'Failed to connect wallet')
      setIsAuthenticating(false)
    }
  }, [connect, connectors])

  // Sign in with Ethereum
  const signIn = useCallback(async () => {
    if (!address || !chainId) {
      setAuthError('Wallet not connected')
      return false
    }

    setIsAuthenticating(true)
    setAuthError(null)

    try {
      // Get nonce from server
      const nonceData = await getNonce(address)

      // Create SIWE message
      const message = new SiweMessage({
        domain: window.location.host,
        address,
        statement: 'Sign in to AI Civilization Platform',
        uri: window.location.origin,
        version: '1',
        chainId,
        nonce: nonceData.nonce,
      })

      const messageStr = message.prepareMessage()

      // Request signature
      const signature = await signMessageAsync({ message: messageStr })

      // Verify with backend
      const verifyResponse = await verifySignature({
        message: messageStr,
        signature,
        address,
      })

      if (verifyResponse.success) {
        setWallet(address, chainId)
        setDid(verifyResponse.did)
        setSession(verifyResponse.sessionId, verifyResponse.accessToken)

        setIsAuthenticating(false)
        return true
      } else {
        setAuthError('Authentication failed')
        setIsAuthenticating(false)
        return false
      }
    } catch (error) {
      console.error('Sign in error:', error)
      setAuthError(error instanceof Error ? error.message : 'Failed to sign in')
      setIsAuthenticating(false)
      return false
    }
  }, [address, chainId, signMessageAsync, setWallet, setDid, setSession])

  // Check existing session
  const checkSession = useCallback(async () => {
    if (!sessionId || !accessToken) {
      return false
    }

    try {
      const session = await getSession()
      if (session.valid && session.agentId) {
        setAgent(session.agentId, session.stake || 0, session.reputation || 0)
        return true
      }
      return false
    } catch {
      clearAuth()
      return false
    }
  }, [sessionId, accessToken, setAgent, clearAuth])

  // Logout
  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } catch {
      // Ignore logout API errors
    }
    disconnect()
    clearAuth()
  }, [disconnect, clearAuth])

  // Check if authenticated
  const isAuthenticated = !!sessionId && !!accessToken && isConnected

  return {
    // Wallet state
    address,
    chainId,
    isConnected,
    connector,
    connectors,

    // Auth state
    isAuthenticated,
    isAuthenticating: isAuthenticating || isConnecting,
    authError,

    // Actions
    connectAndAuth,
    signIn,
    checkSession,
    logout,

    // Store actions
    setAgent,
    setRole,
    setProfile,
  }
}
