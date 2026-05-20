import { cn } from '@/lib/utils'

function parseInline(text: string): (string | { bold: string })[] {
  const parts: (string | { bold: string })[] = []
  const re = /\*\*(.+?)\*\*/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    parts.push({ bold: match[1] })
    last = re.lastIndex
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function InlineContent({ text }: { text: string }) {
  const parts = parseInline(text)
  return (
    <>
      {parts.map((p, i) =>
        typeof p === 'string' ? (
          <span key={i}>{p}</span>
        ) : (
          <strong key={i} className="font-semibold text-foreground">
            {p.bold}
          </strong>
        ),
      )}
    </>
  )
}

export function FormattedText({
  text,
  className,
}: {
  text: string
  className?: string
}) {
  const lines = text.split('\n')

  const elements: { type: 'p' | 'bullet'; content: string }[] = []
  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) continue
    if (/^[-*•]\s+/.test(trimmed)) {
      elements.push({ type: 'bullet', content: trimmed.replace(/^[-*•]\s+/, '') })
    } else {
      elements.push({ type: 'p', content: trimmed })
    }
  }

  const groups: { type: 'p' | 'ul'; items: string[] }[] = []
  for (const el of elements) {
    if (el.type === 'bullet') {
      const last = groups[groups.length - 1]
      if (last?.type === 'ul') {
        last.items.push(el.content)
      } else {
        groups.push({ type: 'ul', items: [el.content] })
      }
    } else {
      groups.push({ type: 'p', items: [el.content] })
    }
  }

  return (
    <div className={cn('space-y-2', className)}>
      {groups.map((g, i) =>
        g.type === 'ul' ? (
          <ul key={i} className="list-disc list-inside space-y-0.5 text-muted-foreground">
            {g.items.map((item, j) => (
              <li key={j}>
                <InlineContent text={item} />
              </li>
            ))}
          </ul>
        ) : (
          <p key={i} className="text-muted-foreground">
            <InlineContent text={g.items[0]} />
          </p>
        ),
      )}
    </div>
  )
}
