import { AppProviders } from "@/app/AppProviders"
import { AppRoutes } from "@/app/AppRoutes"
import { AppShell } from "@/app/AppShell"

function App() {
  return (
    <AppProviders>
      <AppShell>
        <AppRoutes />
      </AppShell>
    </AppProviders>
  )
}

export default App
