import { capabilityCards } from '../data/appData'

export function InsightCards() {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {capabilityCards.map((card) => {
        const Icon = card.icon
        return (
          <article key={card.title} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex size-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              <Icon className="size-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold">{card.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
          </article>
        )
      })}
    </section>
  )
}

