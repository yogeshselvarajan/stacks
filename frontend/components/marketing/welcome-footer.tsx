import Link from "next/link";
import { Library, Heart, Cpu } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";

// Only real, actually-used services -- confirmed against
// infra/environments/dev.tfvars and src/stacks/ this session. No invented
// AWS integrations.
const AWS_SERVICES = [
  "Amazon Bedrock",
  "Amazon Nova",
  "Bedrock AgentCore Runtime",
  "AgentCore Memory",
  "Bedrock Guardrails",
  "Amazon DynamoDB",
  "Amazon Cognito",
];

const PRODUCT_LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "/login", label: "Sign in" },
];

export function WelcomeFooter() {
  return (
    <footer id="built-on-aws" className="border-t px-6 py-16" style={{ borderColor: "var(--color-border)" }}>
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <div className="grid gap-10 md:grid-cols-2">
            <div>
              <div className="flex items-center gap-2">
                <Library size={20} aria-hidden="true" style={{ color: "var(--color-accent)" }} />
                <span className="font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--color-ink)" }}>
                  Stacks
                </span>
              </div>
              <p className="mt-3 max-w-sm text-sm" style={{ color: "var(--color-ink-muted)" }}>
                A library task-completion agent: room-booking conflicts, interlibrary-loan
                routing, and overdue chasing, with a human in the loop wherever it matters.
              </p>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
                Product
              </p>
              <ul className="mt-3 space-y-2">
                {PRODUCT_LINKS.map((link) => (
                  <li key={link.href}>
                    <a href={link.href} className="stacks-focus-ring rounded-md text-sm" style={{ color: "var(--color-ink-muted)" }}>
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-10 border-t pt-6" style={{ borderColor: "var(--color-border)" }}>
            <p className="text-xs font-semibold uppercase tracking-wide" style={{ fontFamily: "var(--font-mono)", color: "var(--color-ink-faint)" }}>
              Built on AWS
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {AWS_SERVICES.map((service) => (
                <li
                  key={service}
                  className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium"
                  style={{ borderColor: "var(--color-border)", color: "var(--color-ink-muted)" }}
                >
                  <Cpu size={12} aria-hidden="true" />
                  {service}
                </li>
              ))}
            </ul>
          </div>

          <p className="mt-8 text-xs" style={{ color: "var(--color-ink-faint)" }}>
            Working prototype on real AWS infrastructure, running against a synthetic library dataset.
          </p>

          <div
            className="mt-3 flex flex-col gap-3 border-t pt-6 text-sm sm:flex-row sm:items-center sm:justify-between"
            style={{ borderColor: "var(--color-border)", color: "var(--color-ink-faint)" }}
          >
            <p>Stacks · Good Neighbor Agents, Agents for Humans hackathon</p>
            <p className="flex items-center gap-1.5">
              Developed with
              <Heart size={14} aria-hidden="true" style={{ color: "var(--color-tier-red-text)" }} />
              by{" "}
              <Link
                href="https://www.linkedin.com/in/yogesh-selvarajan/"
                target="_blank"
                rel="noopener noreferrer"
                className="stacks-focus-ring rounded-md font-medium underline-offset-4 hover:underline"
                style={{ color: "var(--color-ink)" }}
              >
                Yogesh Selvarajan
              </Link>
              ·
              <Link
                href="https://builder.aws.com/community/@yogeshs"
                target="_blank"
                rel="noopener noreferrer"
                className="stacks-focus-ring rounded-md font-medium underline-offset-4 hover:underline"
                style={{ color: "var(--color-ink)" }}
              >
                AWS Builder Center
              </Link>
            </p>
          </div>
        </Reveal>
      </div>
    </footer>
  );
}
