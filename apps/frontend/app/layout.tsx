import type { Metadata } from 'next'
import './globals.css'
import { AnalysisProvider } from '../lib/AnalysisContext'

export const metadata: Metadata = {
  title: 'CleanMatch — Chess Fairplay Auditor',
  description: 'Audit chess games for suspicious patterns using Stockfish analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body>
        <AnalysisProvider>{children}</AnalysisProvider>
      </body>
    </html>
  )
}
