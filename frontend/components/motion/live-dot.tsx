/** A single small pulsing dot indicating "this is live/active", not
 * decorative -- used sparingly (nav eyebrow, workflow visualization's
 * current step) per this project's "no continuous animation on static
 * state" rule. The pulse itself is disabled under prefers-reduced-motion
 * via globals.css's blanket animation-duration override.
 */
export function LiveDot({ color = "var(--color-accent)" }: { color?: string }) {
  return (
    <span className="relative inline-flex h-2 w-2" aria-hidden="true">
      <span
        className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
        style={{ backgroundColor: color }}
      />
      <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
    </span>
  );
}
