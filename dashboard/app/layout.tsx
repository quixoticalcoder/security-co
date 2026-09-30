import type { Metadata, Viewport } from 'next'
import { ThemeProvider } from '@/lib/theme'
import './globals.css'
import { SessionControls } from '@/components/session-controls'

export const metadata: Metadata = {
  title: 'Security Co | Security intelligence',
  description: 'A focused security operations workspace for link, email, and anomaly analysis.',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ThemeProvider>
          {process.env.HOSTED_LITE === 'true' && <div style={{padding:'10px 20px', background:'#172033', color:'#dce6ff', fontSize:13}}>
            Live demo: link and email investigations, history, and report exports. For local ML detection, browser screenshots, device monitoring, and Report &amp; Block, run the full application locally.{' '}
            <a href="https://github.com/quixoticalcoder/security-co#quick-start" target="_blank" rel="noopener noreferrer" style={{color:'inherit', textDecoration:'underline'}}>Local setup instructions</a>. History resets on host restart.
          </div>}
          {process.env.HOSTED_LITE === 'true' && <SessionControls />}
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
