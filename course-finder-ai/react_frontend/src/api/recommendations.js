const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function extractErrorMessage(data, fallbackMessage) {
  const message = data?.detail ?? fallbackMessage
  return Array.isArray(message) ? message.map((item) => item.msg).join(', ') : message
}

export async function getHealthStatus() {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`)

  if (!response.ok) {
    throw new Error('Unable to reach Course Finder API.')
  }

  return response.json()
}

export async function getRecommendations(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/recommendations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Recommendation request failed.'))
  }

  return data
}

export async function extractPdfText(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/v1/intake/pdf`, {
    method: 'POST',
    body: formData,
  })
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'PDF extraction failed.'))
  }

  return data
}

export async function transcribeAudio(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/v1/intake/audio`, {
    method: 'POST',
    body: formData,
  })
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Audio transcription failed.'))
  }

  return data
}

