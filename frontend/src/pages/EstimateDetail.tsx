import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function EstimateDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  
  useEffect(() => {
    if (id) {
      // Redirect to calculator view
      navigate(`/calculator/${id}`, { replace: true })
    }
  }, [id, navigate])
  
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <div className="w-8 h-8 rounded-full border-2 border-lava-600 border-t-transparent animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-500">Loading...</p>
      </div>
    </div>
  )
}
