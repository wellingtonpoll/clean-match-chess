import type { Metadata } from 'next'
import './globals.css'

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
      <body>{children}</body>
    </html>
  )
}
