import { useState, useEffect } from 'react'
import './styles/globals.css'

function App(): JSX.Element {
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false)

  // Apply dark mode class to the root html element
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode)
  }, [isDarkMode])

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200">
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold">Welcome to mini-app-v2</h1>
        <button
          onClick={() => setIsDarkMode(!isDarkMode)}
          className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          Toggle {isDarkMode ? 'Light' : 'Dark'} Mode
        </button>
      </main>
    </div>
  )
}

export default App
