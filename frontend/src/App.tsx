import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Estimates from './pages/Estimates'
import Calculator from './pages/Calculator'
import EstimateDetail from './pages/EstimateDetail'
import TestCalculations from './pages/TestCalculations'
import Pricing from './pages/Pricing'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Estimates />} />
        <Route path="calculator" element={<Calculator />} />
        <Route path="calculator/:id" element={<Calculator />} />
        <Route path="estimate/:id" element={<EstimateDetail />} />
        <Route path="pricing" element={<Pricing />} />
        <Route path="test-calculations" element={<TestCalculations />} />
      </Route>
    </Routes>
  )
}

export default App


