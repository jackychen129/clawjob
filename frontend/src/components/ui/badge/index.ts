import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Badge } from './Badge.vue'

export const badgeVariants = cva(
  'ui-badge inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium tabular-nums tracking-wide transition-colors duration-[var(--duration-fast)] motion-reduce:transition-none',
  {
    variants: {
      variant: {
        default:
          'border-[var(--border-muted-strong)] bg-[var(--surface-2)] text-[var(--text-secondary)]',
        outline:
          'border-[var(--border-color)] bg-transparent text-[var(--text-secondary)]',
        escrow:
          'border-[rgba(var(--exchange-escrow-rgb),0.35)] bg-[rgba(var(--exchange-escrow-rgb),0.12)] text-[var(--exchange-escrow)]',
        p2p:
          'border-[rgba(var(--exchange-ask-rgb),0.35)] bg-[rgba(var(--exchange-ask-rgb),0.12)] text-[var(--exchange-ask)]',
        verified:
          'border-[rgba(var(--exchange-verified-rgb),0.35)] bg-[rgba(var(--exchange-verified-rgb),0.12)] text-[var(--exchange-verified)]',
        bid:
          'border-[rgba(var(--exchange-bid-rgb),0.35)] bg-[rgba(var(--exchange-bid-rgb),0.12)] text-[var(--exchange-bid)]',
        ask:
          'border-[rgba(var(--exchange-ask-rgb),0.35)] bg-[rgba(var(--exchange-ask-rgb),0.12)] text-[var(--exchange-ask)]',
        settlement:
          'border-[rgba(var(--exchange-settlement-rgb),0.35)] bg-[rgba(var(--exchange-settlement-rgb),0.12)] text-[var(--exchange-settlement)]',
        'status-open':
          'border-[rgba(34,197,94,0.35)] bg-[rgba(34,197,94,0.12)] text-[#22c55e]',
        'status-in-progress':
          'border-[rgba(59,130,246,0.35)] bg-[rgba(59,130,246,0.12)] text-[#3b82f6]',
        'status-pending':
          'border-[rgba(234,179,8,0.35)] bg-[rgba(234,179,8,0.12)] text-[#eab308]',
        'status-disputed':
          'border-[rgba(249,115,22,0.35)] bg-[rgba(249,115,22,0.12)] text-[#f97316]',
        'status-completed':
          'border-[rgba(113,113,122,0.35)] bg-[rgba(113,113,122,0.12)] text-[#a1a1aa]',
        'status-settled':
          'border-[rgba(167,139,250,0.35)] bg-[rgba(167,139,250,0.12)] text-[#a78bfa]',
        destructive:
          'border-[rgba(239,68,68,0.35)] bg-[rgba(239,68,68,0.12)] text-[var(--danger-color)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export type BadgeVariants = VariantProps<typeof badgeVariants>
