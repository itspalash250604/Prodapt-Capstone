import {
  BriefcaseBusiness,
  FileText,
  Gauge,
  GraduationCap,
  Layers3,
  Mic,
  Route,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from 'lucide-react'

export const navItems = [
  { label: 'Finder', icon: Sparkles },
  { label: 'Path', icon: Route },
  { label: 'Skills', icon: Layers3 },
  { label: 'Career', icon: BriefcaseBusiness },
  { label: 'Safety', icon: ShieldCheck },
]

export const capabilityCards = [
  {
    title: 'AI recommendations',
    description: 'Semantic course retrieval, reranking, skill-gap analysis, and learning-path generation in one workflow.',
    icon: GraduationCap,
  },
  {
    title: 'Profile-aware search',
    description: 'Tune recommendations with current skills, career target, result depth, and reranker controls.',
    icon: Gauge,
  },
  {
    title: 'Enterprise-ready inputs',
    description: 'Designed for text today, with clear space for resume upload, PDF parsing, voice, and image-based intent.',
    icon: UploadCloud,
  },
]

export const inputModes = [
  { key: 'text', label: 'Text', icon: FileText },
  { key: 'pdf', label: 'PDF', icon: UploadCloud },
  { key: 'audio', label: 'Voice', icon: Mic },
]
