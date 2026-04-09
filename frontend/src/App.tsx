import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Estimates from './pages/Estimates'
import Calculator from './pages/Calculator'
import EstimateDetail from './pages/EstimateDetail'
import TestCalculations from './pages/TestCalculations'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Estimates />} />
        <Route path="calculator" element={<Calculator />} />
        <Route path="calculator/:id" element={<Calculator />} />
        <Route path="estimate/:id" element={<EstimateDetail />} />
        <Route path="test-calculations" element={<TestCalculations />} />
      </Route>
    </Routes>
  )
}

export default App


