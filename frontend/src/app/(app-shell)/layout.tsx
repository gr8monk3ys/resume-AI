import { AppShell } from '@/components/AppShell'

export default function AppShellLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <AppShell>{children}</AppShell>
}
