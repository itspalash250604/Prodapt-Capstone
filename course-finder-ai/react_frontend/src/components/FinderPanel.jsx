import { AlertTriangle, FileUp, Loader2, Mic, Pause, Search, SlidersHorizontal, Sparkles } from 'lucide-react'
import { inputModes } from '../data/appData'

export function FinderPanel({
  form,
  intake,
  onChange,
  onModeChange,
  onFileSelected,
  onStartRecording,
  onStopRecording,
  onSubmit,
  loading,
}) {
  const activeMode = form.inputMode ?? 'text'
  const fileLabel = 'Upload a PDF'
  const isVoiceMode = activeMode === 'audio'

  return (
    <section id="finder" className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-teal-700">AI recommendation engine</p>
            <h3 className="mt-1 text-2xl font-semibold tracking-tight">Find the right course path</h3>
          </div>
          <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1">
            {inputModes.map((mode) => {
              const Icon = mode.icon
              const selected = mode.key === activeMode
              return (
                <button
                  key={mode.key}
                  type="button"
                  onClick={() => onModeChange(mode.key)}
                  className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
                    selected ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500'
                  }`}
                >
                  <Icon className="size-4" />
                  {mode.label}
                </button>
              )
            })}
          </div>
        </div>

        <form className="mt-6 space-y-5" onSubmit={onSubmit}>
          {isVoiceMode ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-700">Voice input replaces the typed learning intent</p>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Record your question or goal and stop recording. The transcript becomes the query that is sent to the recommendation pipeline.
              </p>
              {intake.text ? (
                <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Captured transcript</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{intake.text}</p>
                </div>
              ) : null}
              {intake.currentSkills?.length > 0 || intake.careerGoal ? (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-white p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Inferred current skills</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(intake.currentSkills ?? []).map((skill) => (
                        <span key={skill} className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Inferred career goal</p>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{intake.careerGoal || 'Not detected yet'}</p>
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Learning intent</span>
              <textarea
                name="query"
                value={form.query}
                onChange={onChange}
                rows={5}
                className="mt-2 w-full resize-none rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                placeholder="Example: I know Python and SQL, and I want to become a data analyst in healthcare."
              />
            </label>
          )}

          {activeMode === 'pdf' ? (
            <label className="block rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
              <span className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <FileUp className="size-4 text-teal-700" />
                {fileLabel}
              </span>
              <input
                type="file"
                accept={activeMode === 'pdf' ? 'application/pdf,.pdf' : 'audio/*'}
                onChange={onFileSelected}
                className="mt-3 block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-950 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-slate-800"
              />
              <p className="mt-2 text-xs leading-5 text-slate-500">
                {activeMode === 'pdf'
                  ? 'The backend uses PyMuPDF to extract text and then sends that text into the same recommendation workflow.'
                  : 'The backend uses Whisper from Hugging Face to transcribe the audio before recommendation.'}
              </p>
              {intake.status === 'loading' ? (
                <p className="mt-3 flex items-center gap-2 text-xs font-medium text-teal-700">
                  <Loader2 className="size-3.5 animate-spin" />
                  {activeMode === 'pdf' ? 'Extracting text from the PDF...' : 'Transcribing audio with Whisper...'}
                </p>
              ) : null}
              {intake.error ? (
                <p className="mt-3 flex items-center gap-2 text-xs font-medium text-red-600">
                  <AlertTriangle className="size-3.5" />
                  {intake.error}
                </p>
              ) : null}
              {intake.text ? (
                <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Normalized text</p>
                  <p className="mt-2 line-clamp-5 text-sm leading-6 text-slate-700">{intake.text}</p>
                </div>
              ) : null}
            </label>
          ) : null}

          {activeMode === 'audio' ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Mic className="size-4 text-teal-700" />
                Record your voice
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Start recording, speak your learning intent, then stop to transcribe it with faster-whisper before recommendation.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={onStartRecording}
                  disabled={intake.recording || intake.processing || loading}
                  className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Mic className="size-4" />
                  Start recording
                </button>
                <button
                  type="button"
                  onClick={onStopRecording}
                  disabled={!intake.recording || intake.processing}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Pause className="size-4" />
                  Stop and transcribe
                </button>
              </div>
              {intake.recording ? <p className="mt-3 text-xs font-medium text-teal-700">Recording in progress...</p> : null}
              {intake.status === 'loading' ? (
                <p className="mt-3 flex items-center gap-2 text-xs font-medium text-teal-700">
                  <Loader2 className="size-3.5 animate-spin" />
                  Transcribing audio with Whisper...
                </p>
              ) : null}
              {intake.error ? (
                <p className="mt-3 flex items-center gap-2 text-xs font-medium text-red-600">
                  <AlertTriangle className="size-3.5" />
                  {intake.error}
                </p>
              ) : null}
              {intake.currentSkills?.length > 0 || intake.careerGoal ? (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-white p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Inferred current skills</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(intake.currentSkills ?? []).map((skill) => (
                        <span key={skill} className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Inferred career goal</p>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{intake.careerGoal || 'Not detected yet'}</p>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {!isVoiceMode ? (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Current skills</span>
                <input
                  name="currentSkills"
                  value={form.currentSkills}
                  onChange={onChange}
                  className="mt-2 h-11 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                  placeholder="Python, SQL, Excel"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Career goal</span>
                <input
                  name="careerGoal"
                  value={form.careerGoal}
                  onChange={onChange}
                  className="mt-2 h-11 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                  placeholder="Data Analyst"
                />
              </label>
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-5">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Sparkles className="size-4 text-teal-600" />
              Uses retrieval, reranking, skill gaps, pathing, guardrails, and one normalized text pipeline.
            </div>
            <button
              type="submit"
              disabled={loading || intake.status === 'loading'}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
              Generate recommendations
            </button>
          </div>
        </form>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="size-5 text-teal-700" />
          <h3 className="text-lg font-semibold">Search controls</h3>
        </div>
        <div className="mt-6 space-y-5">
          <Slider label="Candidate pool" name="candidateK" min="5" max="50" value={form.candidateK} onChange={onChange} />
          <Slider label="Top results" name="topK" min="1" max="20" value={form.topK} onChange={onChange} />
          <Slider label="Path length" name="maxPathCourses" min="1" max="12" value={form.maxPathCourses} onChange={onChange} />
          <label className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <span>
              <span className="block text-sm font-medium text-slate-800">Reranker</span>
              <span className="block text-xs text-slate-500">Improve ranking quality after retrieval</span>
            </span>
            <input
              type="checkbox"
              name="useReranker"
              checked={form.useReranker}
              onChange={onChange}
              className="size-5 accent-teal-700"
            />
          </label>
        </div>
      </div>
    </section>
  )
}

function Slider({ label, name, min, max, value, onChange }) {
  return (
    <label className="block">
      <span className="flex items-center justify-between text-sm font-medium text-slate-700">
        {label}
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">{value}</span>
      </span>
      <input className="mt-3 w-full accent-teal-700" type="range" name={name} min={min} max={max} value={value} onChange={onChange} />
    </label>
  )
}

