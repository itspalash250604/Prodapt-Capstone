import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ArrowUpRight, BadgeCheck, BookOpen, BriefcaseBusiness, ChevronLeft, ChevronRight, ChevronDown, Route, ShieldCheck } from 'lucide-react'
import { asPercent, getMetadataList } from '../utils/formatters'

export function ResultsDashboard({ response, error, hasSearched, loading }) {
  const courses = response?.courses ?? []
  const skillGaps = response?.skill_gaps ?? []
  const qualityIssues = response?.quality_issues ?? []
  const pathStages = normalizeLearningPath(response?.learning_path)
  const career = response?.career_alignment
  const guardrails = response?.guardrails
  const showEmptyState = !hasSearched && !response
  const [coursePage, setCoursePage] = useState(1)
  const [showAllCourses, setShowAllCourses] = useState(false)
  const [expandedCourseIds, setExpandedCourseIds] = useState([])
  const [rawJsonVisibleIds, setRawJsonVisibleIds] = useState([])

  const hasExtraInfo = (course) => {
    if (!course) return false
    const fullDesc = getFullDescription(course)
    const meta = course.metadata || {}
    return Boolean(
      fullDesc ||
        course.document ||
        meta.long_description ||
        meta.full_description ||
        meta.about ||
        course.url ||
        meta.url ||
        course.learning_outcomes?.length ||
        meta.learning_outcomes?.length ||
        course.prerequisites?.length
    )
  }

  const toggleExpanded = (key, course) => {
    setExpandedCourseIds((prev) => {
      const isOpen = prev.includes(key)
      const next = isOpen ? prev.filter((id) => id !== key) : [...prev, key]

      // if we're opening and there is no extra info, show raw JSON automatically
      if (!isOpen && !hasExtraInfo(course)) {
        setRawJsonVisibleIds((rawPrev) => (rawPrev.includes(key) ? rawPrev : [...rawPrev, key]))
      }

      // if we're closing, hide raw JSON for cleanliness
      if (isOpen) {
        setRawJsonVisibleIds((rawPrev) => rawPrev.filter((id) => id !== key))
      }

      return next
    })
  }
  const toggleRawJson = (key) => setRawJsonVisibleIds((prev) => (prev.includes(key) ? prev.filter((id) => id !== key) : [...prev, key]))
  const coursesPerPage = 5

  const totalCoursePages = Math.max(1, Math.ceil(courses.length / coursesPerPage))

  useEffect(() => {
    setCoursePage(1)
    setShowAllCourses(false)
    setExpandedCourseIds([])
  }, [response])

  useEffect(() => {
    setCoursePage((currentPage) => Math.min(currentPage, totalCoursePages))
  }, [totalCoursePages])

  const visibleCourses = useMemo(() => {
    if (showAllCourses) {
      return courses
    }
    const startIndex = (coursePage - 1) * coursesPerPage
    return courses.slice(startIndex, startIndex + coursesPerPage)
  }, [coursePage, courses, showAllCourses])

  return (
    <section className="grid gap-6 xl:grid-cols-[1fr_32rem]">
      <div className="space-y-6">
        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="size-4" />
              Recommendation request failed
            </div>
            <p className="mt-2">{error}</p>
          </div>
        ) : null}

        <div id="path" className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-teal-700">Generated answer</p>
              <h3 className="mt-1 text-xl font-semibold">Advisor summary</h3>
            </div>
            <BadgeCheck className="size-5 text-emerald-600" />
          </div>
          {loading ? <p className="mt-3 text-xs font-medium uppercase tracking-[0.16em] text-teal-700">Processing uploaded content and running the recommendation pipeline...</p> : null}
          <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700">
            {loading
              ? 'Generating a personalized course recommendation summary...'
              : response?.final_response ?? 'Run a search to generate a personalized course recommendation summary.'}
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold">Recommended courses</h3>
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-500">{courses.length} matches</span>
              {courses.length > coursesPerPage ? (
                <button
                  type="button"
                  onClick={() => setShowAllCourses((current) => !current)}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-teal-300 hover:text-teal-700"
                >
                  {showAllCourses ? 'Collapse to 5' : `Show all ${courses.length}`}
                </button>
              ) : null}
            </div>
          </div>
          {courses.length > 0 ? (
            <>
              <div className="mt-5 space-y-4">
                {visibleCourses.map((course, index) => {
                  const absoluteRank = (coursePage - 1) * coursesPerPage + index + 1
                  const courseKey = course.course_id ?? course.title
                  const shortDesc = getShortDescription(course)
                  const fullDesc = getFullDescription(course)
                  const isExpanded = expandedCourseIds.includes(courseKey)

                  return (
                    <article
                      key={courseKey}
                      role="button"
                      tabIndex={0}
                      aria-expanded={isExpanded}
                      onClick={() => toggleExpanded(courseKey, course)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          toggleExpanded(courseKey, course)
                        }
                      }}
                      className="rounded-lg border border-slate-200 p-4 transition hover:border-teal-300 hover:shadow-sm cursor-pointer"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                            <BookOpen className="size-3.5" />
                            Rank {absoluteRank}
                          </div>
                          <h4 className="mt-2 text-lg font-semibold">{course.title}</h4>
                          <p className="mt-1 text-sm text-slate-600">{course.organization}</p>
                          <div className="mt-3 rounded-lg border border-teal-100 bg-teal-50/60 px-3 py-2">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">
                              {isExpanded ? 'Course description' : 'Why this course'}
                            </p>
                            <p className="mt-1 text-sm leading-6 text-slate-700">{isExpanded ? fullDesc || buildShortCourseDescription(course) : shortDesc}</p>
                          </div>
                          {isExpanded ? (
                            <div className="mt-3 text-sm leading-6 text-slate-700">
                              {/** show original document or longer metadata fields when available */}
                              {course.document ? (
                                <div className="mt-2">
                                  <p className="text-sm font-medium">About</p>
                                  <p className="text-xs leading-5 text-slate-600">{course.document.slice(0, 800)}{course.document.length > 800 ? '...' : ''}</p>
                                </div>
                              ) : null}
                              {course.metadata?.long_description || course.metadata?.full_description || course.metadata?.about ? (
                                <div className="mt-2">
                                  <p className="text-sm font-medium">About</p>
                                  <p className="text-xs leading-5 text-slate-600">{(course.metadata.long_description || course.metadata.full_description || course.metadata.about).slice(0, 800)}{((course.metadata.long_description || course.metadata.full_description || course.metadata.about) || '').length > 800 ? '...' : ''}</p>
                                </div>
                              ) : null}
                              {/** provider/course URL fallbacks */}
                              {(course.url || course.metadata?.url || course.metadata?.course_url || course.metadata?.link) ? (
                                <p className="mt-2 text-xs text-teal-700">
                                  <a
                                    href={course.url ?? course.metadata?.url ?? course.metadata?.course_url ?? course.metadata?.link}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    View course
                                  </a>
                                </p>
                              ) : null}
                              {/** learning outcomes from metadata */}
                              {(course.learning_outcomes && Array.isArray(course.learning_outcomes) && course.learning_outcomes.length > 0) || (course.metadata && Array.isArray(course.metadata.learning_outcomes) && course.metadata.learning_outcomes.length > 0) ? (
                                <div className="mt-2">
                                  <p className="text-sm font-medium">Learning outcomes</p>
                                  <ul className="list-disc ml-5 text-xs leading-5 text-slate-600">
                                    {(course.learning_outcomes ?? course.metadata.learning_outcomes).slice(0, 5).map((outcome, i) => (
                                      <li key={i}>{outcome}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}
                              {course.prerequisites && Array.isArray(course.prerequisites) ? (
                                <div className="mt-2">
                                  <p className="text-sm font-medium">Prerequisites</p>
                                  <p className="text-xs text-slate-600">{course.prerequisites.join(', ')}</p>
                                </div>
                              ) : null}
                              <div className="mt-3">
                                <p className="text-sm font-medium">Preparatory resources</p>
                                {course.preparatory_resources && Array.isArray(course.preparatory_resources) && course.preparatory_resources.length > 0 ? (
                                  <div className="mt-2 space-y-2 text-xs text-slate-600">
                                    {course.preparatory_resources.map((item, i) => {
                                      const resources = Array.isArray(item.resources) ? item.resources : []
                                      return (
                                        <div key={i} className="rounded-md bg-slate-50 p-2">
                                          <p className="font-semibold text-[12px]">{item.skill}</p>
                                          {resources.length > 0 ? (
                                            <ul className="mt-1 list-disc ml-4">
                                              {resources.map((r, j) => (
                                                <li key={j} className="mt-1">
                                                  <a
                                                    href={r.url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="text-teal-700 hover:underline"
                                                  >
                                                    {r.title}
                                                  </a>
                                                  {r.source ? <span className="ml-2 text-slate-500">· {r.source}</span> : null}
                                                  {r.estimated_time ? <span className="ml-2 text-slate-400">({r.estimated_time})</span> : null}
                                                </li>
                                              ))}
                                            </ul>
                                          ) : (
                                            <p className="mt-1 text-slate-500">No external prep resource needed.</p>
                                          )}
                                        </div>
                                      )
                                    })}
                                  </div>
                                ) : (
                                  <p className="mt-2 text-xs text-slate-500">No specific preparation gaps were identified for this course.</p>
                                )}
                              </div>
                              <div className="mt-2">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    toggleRawJson(courseKey)
                                  }}
                                  className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded"
                                >
                                  {rawJsonVisibleIds.includes(courseKey) ? 'Hide raw JSON' : 'Show raw JSON'}
                                </button>
                                {rawJsonVisibleIds.includes(courseKey) ? (
                                  <pre className="mt-2 bg-slate-100 p-3 rounded text-xs overflow-auto max-h-48">{JSON.stringify(course, null, 2)}</pre>
                                ) : null}
                              </div>
                            </div>
                          ) : (
                            <p className="mt-2 text-sm leading-6 text-slate-700">{buildShortCourseDescription(course)}</p>
                          )}
                        </div>
                        <div className="rounded-lg bg-teal-50 px-3 py-2 text-right flex flex-col items-end gap-1">
                          <ChevronDown className={`size-4 text-teal-700 transition-transform duration-200 ease-in-out ${isExpanded ? 'rotate-180' : ''}`} />
                          <p className="text-xs font-medium text-teal-700">Match</p>
                          <p className="text-lg font-semibold text-teal-900">{asPercent(course.match_percentage ?? course.score)}</p>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {getMetadataList(course.metadata, 'skills').slice(0, 5).map((skill) => (
                          <span key={skill} className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                            {skill}
                          </span>
                        ))}
                        {course.metadata?.level ? <span className="rounded-md bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">{course.metadata.level}</span> : null}
                        {(course.time_to_complete || course.metadata?.duration) ? <span className="rounded-md bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">{course.time_to_complete || course.metadata?.duration}</span> : null}
                      </div>
                    </article>
                  )
                })}
              </div>
              {showAllCourses ? (
                <div className="mt-5 border-t border-slate-200 pt-4">
                  <p className="text-sm text-slate-500">Showing all {courses.length} courses in one view.</p>
                </div>
              ) : (
                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
                  <p className="text-sm text-slate-500">
                    Showing {Math.min((coursePage - 1) * coursesPerPage + 1, courses.length)}-{Math.min(coursePage * coursesPerPage, courses.length)} of {courses.length}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setCoursePage((currentPage) => Math.max(1, currentPage - 1))}
                      disabled={coursePage <= 1}
                      className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <ChevronLeft className="size-4" />
                      Previous
                    </button>
                    <span className="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">
                      Page {coursePage} of {totalCoursePages}
                    </span>
                    <button
                      type="button"
                      onClick={() => setCoursePage((currentPage) => Math.min(totalCoursePages, currentPage + 1))}
                      disabled={coursePage >= totalCoursePages}
                      className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Next
                      <ChevronRight className="size-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyBlock
              title={showEmptyState ? 'No search has been run yet' : 'No courses returned'}
              description={showEmptyState ? 'Enter your learning intent and generate recommendations to see live results.' : 'Try a broader query or increase the candidate pool.'}
            />
          )}
        </div>
      </div>

      <aside className="space-y-6">
        <Panel id="skills" title="Skill gaps" icon={Route}>
          {skillGaps.length > 0 ? (
            <div className="space-y-3">
              {skillGaps.map((gap, index) => (
                <SkillGapCard key={`${gap.course_id ?? gap.skill ?? gap.name}-${index}`} gap={gap} index={index} />
              ))}
            </div>
          ) : (
            <EmptyBlock
              title="No skill gaps yet"
              description="This section updates from the backend skill-gap analyzer after you generate recommendations."
            />
          )}
        </Panel>

        <Panel id="quality" title="Quality / readiness" icon={ArrowUpRight}>
          {qualityIssues.length > 0 ? (
            <div className="space-y-3">
              {qualityIssues.map((issue, index) => (
                <QualityIssueCard key={`${issue.course_id ?? issue.stage_number ?? issue.check_name}-${index}`} issue={issue} index={index} />
              ))}
            </div>
          ) : (
            <EmptyBlock
              title="No quality issues"
              description="Readiness and alignment notes will appear here when the pipeline detects them."
            />
          )}
        </Panel>

        <Panel title="Learning path" icon={Route}>
          {pathStages.length > 0 ? (
            <div className="space-y-4">
              <p className="text-sm leading-6 text-slate-600">
                {response?.learning_path?.readiness_summary ?? response?.learning_path?.title ?? response?.learning_path?.goal}
              </p>
              {pathStages.map((stage, stageIndex) => (
                <div key={`${stage.title}-${stageIndex}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="flex gap-3">
                    <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-950 text-xs font-semibold text-white">
                      {stage.stage_number ?? stageIndex + 1}
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{stage.title}</p>
                      <p className="text-xs leading-5 text-slate-500">{stage.purpose}</p>
                    </div>
                  </div>
                  <div className="mt-3 space-y-2 border-l border-slate-300 pl-4">
                    {stage.courses.map((course, courseIndex) => (
                      <div key={`${course.course_id ?? course.title}-${courseIndex}`}>
                        <p className="text-sm font-medium">{course.title ?? course.course_title ?? course.name}</p>
                        <p className="text-xs leading-5 text-slate-500">
                          {course.organization ? `${course.organization} · ` : ''}
                          {course.reason ?? course.description ?? course.missing_skill ?? 'Recommended for this step'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {response?.learning_path?.note ? <p className="text-xs leading-5 text-slate-500">{response.learning_path.note}</p> : null}
            </div>
          ) : (
            <EmptyBlock
              title="No path generated yet"
              description="The learning path will be built from the courses and skill gaps returned for your specific input."
            />
          )}
        </Panel>

        <Panel id="career" title="Career fit" icon={BriefcaseBusiness}>
          <div className="rounded-lg bg-slate-950 p-4 text-white">
            <p className="text-sm text-slate-300">Alignment score</p>
            <p className="mt-1 text-3xl font-semibold">{asPercent(career?.score ?? career?.alignment_score ?? 0)}</p>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-600">{career?.summary ?? career?.explanation ?? 'Career alignment will update after analysis.'}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(career?.roles ?? career?.recommended_roles ?? []).map((role) => (
              <span key={role} className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
                {role}
              </span>
            ))}
          </div>
        </Panel>

        <Panel id="safety" title="Safety & errors" icon={ShieldCheck}>
          <p className="text-sm font-semibold text-emerald-700">{guardrails?.status ?? 'Ready'}</p>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
            {normalizeGuardrailNotes(guardrails).map((note) => (
              <li key={note.message ?? note} className="flex gap-2">
                <ArrowUpRight className="mt-1 size-3.5 shrink-0 text-teal-700" />
                <span>{note.message ?? note}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </aside>
    </section>
  )
}

function SkillGapCard({ gap, index }) {
  const missingSkills = gap.missing_skills ?? []
  const matchedSkills = gap.matched_skills ?? []
  const readiness = typeof gap.readiness_score === 'number' ? asPercent(gap.readiness_score) : gap.readiness_label

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold">{gap.course_title ?? gap.skill ?? gap.name ?? `Skill gap ${index + 1}`}</p>
        <span className="rounded-md bg-white px-2 py-1 text-xs text-slate-600">{readiness ?? gap.priority ?? 'Focus'}</span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-500">
        {gap.note ?? gap.description ?? `${missingSkills.length} missing skills detected for this course.`}
      </p>
      {missingSkills.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {missingSkills.slice(0, 6).map((skill) => (
            <span key={skill} className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700">
              {skill}
            </span>
          ))}
        </div>
      ) : null}
      {matchedSkills.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {matchedSkills.slice(0, 5).map((skill) => (
            <span key={skill} className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
              {skill}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function QualityIssueCard({ issue, index }) {
  const severity = issue.severity ?? 'info'
  const severityStyles =
    severity === 'error'
      ? 'bg-red-50 text-red-700'
      : severity === 'warning'
        ? 'bg-amber-50 text-amber-700'
        : 'bg-sky-50 text-sky-700'

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold">{issue.check_name ?? `Issue ${index + 1}`}</p>
        <span className={`rounded-md px-2 py-1 text-xs font-medium ${severityStyles}`}>{severity}</span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-600">{issue.message ?? 'No details available.'}</p>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
        {issue.course_id ? <span className="rounded-md bg-white px-2 py-1">Course: {issue.course_id}</span> : null}
        {issue.stage_number ? <span className="rounded-md bg-white px-2 py-1">Stage {issue.stage_number}</span> : null}
      </div>
    </div>
  )
}

function EmptyBlock({ title, description }) {
  return (
    <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>
    </div>
  )
}

function normalizeLearningPath(path) {
  if (!path) return []

  if (Array.isArray(path.stages)) {
    return path.stages.map((stage) => ({
      ...stage,
      title: stage.title ?? `Stage ${stage.stage_number ?? ''}`,
      purpose: stage.purpose ?? 'Recommended learning stage',
      courses: Array.isArray(stage.courses) ? stage.courses : [],
    }))
  }

  const flatSteps = path.steps ?? path.courses ?? []
  if (Array.isArray(flatSteps) && flatSteps.length > 0) {
    return [
      {
        stage_number: 1,
        title: path.title ?? path.goal ?? 'Recommended sequence',
        purpose: path.readiness_summary ?? 'Follow these courses in order.',
        courses: flatSteps,
      },
    ]
  }

  return []
}

function normalizeGuardrailNotes(guardrails) {
  if (!guardrails) return ['Safety report will appear after the request completes.']
  if (Array.isArray(guardrails.notes)) return guardrails.notes
  if (Array.isArray(guardrails.findings)) return guardrails.findings
  if (Array.isArray(guardrails.issues) && guardrails.issues.length > 0) return guardrails.issues
  if (guardrails.summary) return [guardrails.summary]
  return ['No guardrail issues returned.']
}

function buildShortCourseDescription(course) {
  const description = course.description?.trim()
  const rationale = course.rationale?.trim()
  const metadataDescription = course.metadata?.description?.trim()
  const skills = getMetadataList(course.metadata, 'skills').slice(0, 3)
  const timeValue = course.time_to_complete || course.metadata?.duration

  const candidateText = description || metadataDescription || rationale || ''
  const shortText = candidateText ? candidateText.replace(/\s+/g, ' ').trim() : ''

  if (shortText) {
    const truncated = shortText.length > 150 ? `${shortText.slice(0, 147)}...` : shortText
    return truncated
  }

  const skillText = skills.length > 0 ? ` Focus areas: ${skills.join(', ')}.` : ''
  const durationText = timeValue ? ` Estimated time: ${timeValue}.` : ''
  return `Recommended based on your profile.${skillText}${durationText}`
}

function getShortDescription(course) {
  const desc =
    course.summary ?? course.short_description ?? course.description ?? course.metadata?.description ?? course.rationale ?? ''
  const cleaned = (desc || '').replace(/\s+/g, ' ').trim()
  if (!cleaned) return ''
  return cleaned.length > 140 ? `${cleaned.slice(0, 137)}...` : cleaned
}

function getFullDescription(course) {
  const desc = course.description ?? course.metadata?.description ?? course.rationale ?? course.summary ?? course.short_description ?? ''
  return (desc || '').replace(/\s+/g, ' ').trim()
}

function Panel({ id, title, icon: Icon, children }) {
  return (
    <div id={id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="size-5 text-teal-700" />
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      {children}
    </div>
  )
}
