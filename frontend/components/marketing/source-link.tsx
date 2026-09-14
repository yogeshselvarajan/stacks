// frontend/components/marketing/source-link.tsx
// Every named external product/organization on /welcome links to its own
// real, verified source (see docs/research/competitive_landscape_2026_update.md's
// own Sources section) rather than sitting there as an unlinked claim.
export function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="stacks-focus-ring rounded-sm underline-offset-4 hover:underline"
      style={{ color: "inherit", fontWeight: 600 }}
    >
      {children}
    </a>
  );
}
