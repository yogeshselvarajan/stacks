import type { Metadata } from "next";
import { WelcomeNav } from "@/components/marketing/welcome-nav";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { CapabilityGrid } from "@/components/marketing/capability-grid";
import { CtaSection } from "@/components/marketing/cta-section";
import { WelcomeFooter } from "@/components/marketing/welcome-footer";

export const metadata: Metadata = {
  title: "Stacks, a library task-completion agent",
  description:
    "Stacks resolves room-booking conflicts, routes ambiguous interlibrary-loan requests, and chases overdue items, automatically when it's safe, with a human in the loop when it isn't. Built on Amazon Bedrock AgentCore.",
  openGraph: {
    title: "Stacks, a library task-completion agent",
    description:
      "Automate the routine, keep a human on anything sensitive. Built on Amazon Bedrock AgentCore for the Agents for Humans hackathon.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Stacks, a library task-completion agent",
    description: "Automate the routine, keep a human on anything sensitive.",
  },
};

export default function WelcomePage() {
  return (
    <div style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <WelcomeNav />
      <main>
        <Hero />
        <HowItWorks />
        <CapabilityGrid />
        <CtaSection />
      </main>
      <WelcomeFooter />
    </div>
  );
}
