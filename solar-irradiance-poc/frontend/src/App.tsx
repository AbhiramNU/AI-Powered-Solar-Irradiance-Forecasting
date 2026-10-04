import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Loading } from './components/ui'
import Home from './pages/Home'

const ForecastView = lazy(() => import('./pages/ForecastView'))
const AccuracyScorecard = lazy(() => import('./pages/AccuracyScorecard'))
const LocationComparison = lazy(() => import('./pages/LocationComparison'))
const EnergyEstimate = lazy(() => import('./pages/EnergyEstimate'))
const DataMethod = lazy(() => import('./pages/DataMethod'))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="forecast" element={<ForecastView />} />
            <Route path="accuracy" element={<AccuracyScorecard />} />
            <Route path="locations" element={<LocationComparison />} />
            <Route path="energy" element={<EnergyEstimate />} />
            <Route path="method" element={<DataMethod />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
