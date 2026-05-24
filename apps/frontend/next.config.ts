import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  experimental: {
    // Required for streaming SSE
  },
  // Allow spawning Python subprocess from API routes
  serverExternalPackages: [],
}

export default nextConfig
