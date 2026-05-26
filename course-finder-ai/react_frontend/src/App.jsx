import { useEffect, useMemo, useRef, useState } from 'react'
import { extractPdfText, getHealthStatus, getRecommendations, transcribeAudio } from './api/recommendations'
import { FinderPanel } from './components/FinderPanel'
import { InsightCards } from './components/InsightCards'
import { ResultsDashboard } from './components/ResultsDashboard'
import { Shell } from './components/Shell'
import { blobToWavFile } from './utils/audio'
import { normalizeSkills } from './utils/formatters'

const initialForm = {
  inputMode: 'text',
  query: 'I know Python, SQL, and basic statistics. I want to become a data analyst for enterprise business teams.',
  currentSkills: 'Python, SQL, Excel, Statistics',
  careerGoal: 'Data Analyst',
  candidateK: 20,
  topK: 8,
  maxPathCourses: 6,
  useReranker: true,
}

function App() {
  const [form, setForm] = useState(initialForm)
  const [intake, setIntake] = useState({
    status: 'idle',
    error: '',
    text: '',
    filename: '',
    currentSkills: [],
    careerGoal: '',
    recording: false,
    processing: false,
  })
  const [response, setResponse] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [apiStatus, setApiStatus] = useState('checking')
  const [activeSection, setActiveSection] = useState('Finder')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const mediaRecorderRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => {
    getHealthStatus()
      .then((data) => setApiStatus(data.status ?? 'ok'))
      .catch(() => setApiStatus('offline'))
  }, [])

  useEffect(() => {
    const sections = ['finder', 'path', 'skills', 'career', 'safety']
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((entry) => entry.isIntersecting)
        if (visible) {
          setActiveSection(visible.target.id.charAt(0).toUpperCase() + visible.target.id.slice(1))
        }
      },
      { rootMargin: '-30% 0px -60% 0px' },
    )

    sections.forEach((section) => {
      const element = document.getElementById(section)
      if (element) observer.observe(element)
    })

    return () => observer.disconnect()
  }, [])

  const canSubmit = useMemo(() => {
    if (form.inputMode === 'text') {
      return form.query.trim().length >= 3
    }

    return intake.status === 'ready' && intake.text.trim().length >= 3
  }, [form.inputMode, form.query, intake.status, intake.text])

  function handleChange(event) {
    const { name, type, value, checked } = event.target
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : type === 'range' ? Number(value) : value,
    }))
  }

  function handleModeChange(mode) {
    if (mode !== 'audio') {
      stopRecordingSession()
    }
    setForm((current) => ({
      ...current,
      inputMode: mode,
    }))
    setIntake((current) => ({
      ...current,
      error: '',
      text: mode === 'text' ? current.text : '',
      filename: mode === 'text' ? current.filename : '',
      currentSkills: mode === 'text' ? current.currentSkills : [],
      careerGoal: mode === 'text' ? current.careerGoal : '',
      recording: false,
      processing: false,
    }))
  }

  function cleanupRecordingResources() {
    stopMediaStreamTracks()
    mediaRecorderRef.current = null
    audioChunksRef.current = []
  }

  function stopMediaStreamTracks() {
    if (!mediaStreamRef.current) return

    mediaStreamRef.current.getTracks().forEach((track) => track.stop())
    mediaStreamRef.current = null
  }

  function stopRecordingSession() {
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
    stopMediaStreamTracks()
    mediaRecorderRef.current = null
  }

  async function handleStartRecording() {
    if (intake.recording || intake.processing || loading) return

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !window.AudioContext) {
      setIntake((current) => ({
        ...current,
        error: 'Voice recording is not supported in this browser.',
      }))
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const preferredMimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'].find((type) =>
        MediaRecorder.isTypeSupported(type),
      )
      const recorder = new MediaRecorder(stream, preferredMimeType ? { mimeType: preferredMimeType } : undefined)

      audioChunksRef.current = []
      mediaStreamRef.current = stream
      mediaRecorderRef.current = recorder
      setIntake({ status: 'idle', error: '', text: '', filename: 'voice-note.wav', recording: true, processing: false })

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onerror = () => {
        setIntake((current) => ({
          ...current,
          recording: false,
          processing: false,
          error: 'Voice recording failed while capturing audio.',
        }))
      }

      recorder.start()
    } catch {
      cleanupRecordingResources()
      setIntake((current) => ({
        ...current,
        recording: false,
        processing: false,
        error: 'Microphone access was denied or unavailable.',
      }))
    }
  }

  async function handleStopRecording() {
    const recorder = mediaRecorderRef.current
    if (!recorder || intake.processing) return

    setIntake((current) => ({
      ...current,
      recording: false,
      processing: true,
      error: '',
    }))

    const stopPromise = new Promise((resolve) => {
      recorder.addEventListener(
        'stop',
        async () => {
          const chunks = [...audioChunksRef.current]
          cleanupRecordingResources()

          if (!chunks.length) {
            setIntake({
              status: 'idle',
              error: 'No audio was captured.',
              text: '',
              filename: '',
              currentSkills: [],
              careerGoal: '',
              recording: false,
              processing: false,
            })
            resolve()
            return
          }

          try {
            const wavFile = await blobToWavFile(new Blob(chunks, { type: chunks[0]?.type ?? 'audio/webm' }))
            const data = await transcribeAudio(wavFile)
            const text = data.text ?? ''
            const inferredSkills = Array.isArray(data.current_skills) ? data.current_skills : []
            const inferredCareerGoal = typeof data.career_goal === 'string' ? data.career_goal : ''

            setForm((current) => ({
              ...current,
              query: text,
              currentSkills: inferredSkills.length > 0 ? inferredSkills.join(', ') : current.currentSkills,
              careerGoal: inferredCareerGoal || current.careerGoal,
            }))
            setIntake({
              status: 'ready',
              error: '',
              text,
              filename: data.filename ?? wavFile.name,
              currentSkills: inferredSkills,
              careerGoal: inferredCareerGoal,
              recording: false,
              processing: false,
            })
          } catch (requestError) {
            setIntake({
              status: 'error',
              error: requestError.message,
              text: '',
              filename: '',
              currentSkills: [],
              careerGoal: '',
              recording: false,
              processing: false,
            })
          }

          resolve()
        },
        { once: true },
      )
    })

    try {
      recorder.requestData?.()
    } catch {
      // Some browsers don't support requestData consistently; stop still works without it.
    }

    stopMediaStreamTracks()
    recorder.stop()
    await stopPromise
  }


  useEffect(
    () => () => {
      cleanupRecordingResources()
    },
    [],
  )
  async function handleFileSelected(event) {
    const file = event.target.files?.[0]
    if (!file) {
      setIntake({ status: 'idle', error: '', text: '', filename: '' })
      return
    }

    setIntake({ status: 'loading', error: '', text: '', filename: file.name })

    try {
      const data = form.inputMode === 'pdf' ? await extractPdfText(file) : await transcribeAudio(file)
      const text = data.text ?? ''
      const inferredSkills = Array.isArray(data.current_skills) ? data.current_skills : []
      const inferredCareerGoal = typeof data.career_goal === 'string' ? data.career_goal : ''

      setForm((current) => ({
        ...current,
        query: text,
        currentSkills: inferredSkills.length > 0 ? inferredSkills.join(', ') : current.currentSkills,
        careerGoal: inferredCareerGoal || current.careerGoal,
      }))
      setIntake({
        status: 'ready',
        error: '',
        text,
        filename: data.filename ?? file.name,
        currentSkills: inferredSkills,
        careerGoal: inferredCareerGoal,
      })
    } catch (requestError) {
      setIntake({
        status: 'error',
        error: requestError.message,
        text: '',
        filename: file.name,
        currentSkills: [],
        careerGoal: '',
      })
    } finally {
      event.target.value = ''
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return

    setLoading(true)
    setError('')
    setHasSearched(true)

    try {
      const currentSkills =
        form.inputMode === 'audio' && intake.currentSkills.length > 0
          ? intake.currentSkills
          : normalizeSkills(form.currentSkills)
      const careerGoal =
        form.inputMode === 'audio' && intake.careerGoal
          ? intake.careerGoal
          : form.careerGoal.trim() || null

      const data = await getRecommendations({
        query: (form.inputMode === 'audio' ? intake.text : form.query).trim(),
        current_skills: currentSkills,
        career_goal: careerGoal,
        candidate_k: Number(form.candidateK),
        top_k: Math.min(Number(form.topK), Number(form.candidateK)),
        max_path_courses: Number(form.maxPathCourses),
        use_reranker: form.useReranker,
      })
      setResponse(data)
      setApiStatus('ok')
    } catch (requestError) {
      setError(requestError.message)
      setApiStatus('offline')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Shell activeSection={activeSection} apiStatus={apiStatus}>
      <div className="mx-auto max-w-7xl space-y-6">
        <FinderPanel
          form={form}
          intake={intake}
          onChange={handleChange}
          onModeChange={handleModeChange}
          onFileSelected={handleFileSelected}
          onStartRecording={handleStartRecording}
          onStopRecording={handleStopRecording}
          onSubmit={handleSubmit}
          loading={loading}
        />
        <InsightCards />
        <ResultsDashboard response={response} error={error} hasSearched={hasSearched} loading={loading} />
      </div>
    </Shell>
  )
}

export default App
