import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// 1. We import our new file instead of App.jsx
import UserInterface from './UserInterface.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* 2. We tell React to render our file instead of <App /> */}
    <UserInterface />
  </StrictMode>,
)