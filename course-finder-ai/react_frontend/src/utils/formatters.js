export function normalizeSkills(value) {
  return value
    .split(',')
    .map((skill) => skill.trim())
    .filter(Boolean)
}

export function asPercent(score) {
  if (typeof score !== 'number') return 'N/A'
  return `${Math.round(score <= 1 ? score * 100 : score)}%`
}

export function getMetadataList(metadata, key) {
  const value = metadata?.[key]
  if (Array.isArray(value)) return value
  if (typeof value === 'string' && value.length > 0) return [value]
  return []
}

