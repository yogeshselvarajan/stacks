import { CheckCircle2, Clock, AlertTriangle } from "lucide-react";

type Tier = "GREEN" | "YELLOW" | "RED";

const TIER_CONFIG: Record<Tier, { label: string; Icon: typeof CheckCircle2; textVar: string; bgVar: string }> = {
  GREEN: { label: "Auto-executed", Icon: CheckCircle2, textVar: "var(--color-tier-green-text)", bgVar: "var(--color-tier-green-bg)" },
  YELLOW: { label: "Awaiting confirmation", Icon: Clock, textVar: "var(--color-tier-yellow-text)", bgVar: "var(--color-tier-yellow-bg)" },
  RED: { label: "Requires review", Icon: AlertTriangle, textVar: "var(--color-tier-red-text)", bgVar: "var(--color-tier-red-bg)" },
};

export function TierBadge({ tier }: { tier: Tier }) {
  const { label, Icon, textVar, bgVar } = TIER_CONFIG[tier];
  return (
    <span
      role="status"
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium"
      style={{ color: textVar, backgroundColor: bgVar }}
    >
      <Icon size={16} aria-hidden="true" />
      {label}
    </span>
  );
}
