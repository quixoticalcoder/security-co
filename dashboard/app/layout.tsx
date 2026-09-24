import type { Metadata, Viewport } from 'next'
import { ThemeProvider } from '@/lib/theme'
import './globals.css'

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
            Free hosted edition: AI investigations use HTTP page text. Local ML scores, rendered screenshots and device monitoring require the local installation. History resets on host restart.
          </div>}
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
