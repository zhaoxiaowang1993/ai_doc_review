import { FluentProvider } from '@fluentui/react-components'
import ReactDOM from 'react-dom/client'
import { BrowserRouter as Router } from 'react-router-dom'
import App from './App'
import './index.css'
import { getAppTheme } from './theme'

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement)

function Root() {
  return (
    <Router>
      <FluentProvider theme={getAppTheme()}>
        <App />
      </FluentProvider>
    </Router>
  )
}

root.render(<Root />)
