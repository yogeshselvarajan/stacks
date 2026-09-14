import type { Metadata } from "next";
import { WelcomeNav } from "@/components/marketing/welcome-nav";
import { Hero } from "@/components/marketing/hero";
import { ProblemSection } from "@/components/marketing/problem-section";
import { StartsWhereTheyStop } from "@/components/marketing/starts-where-they-stop";
import { WorkflowsSection } from "@/components/marketing/workflows-section";
import { ActionVsAnswer } from "@/components/marketing/action-vs-answer";
import { SafetySection } from "@/components/marketing/safety-section";
import { PolicySection } from "@/components/marketing/policy-section";
import { CapabilityGrid } from "@/components/marketing/capability-grid";
import { AuditPreview } from "@/components/marketing/audit-preview";
import { AwsArchitecture } from "@/components/marketing/aws-architecture";
import { CtaSection } from "@/components/marketing/cta-section";
import { WelcomeFooter } from "@/components/marketing/welcome-footer";

export const metadata: Metadata = {
  title: { absolute: "Stacks | Task-completion agent for library operations" },
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
  alternates: {
    canonical: "/",
  },
};

export default function RootPage() {
  return (
    <div style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <WelcomeNav />
      <main>
        <Hero />
        <ProblemSection />
        <StartsWhereTheyStop />
        <WorkflowsSection />
        <ActionVsAnswer />
        <SafetySection />
        <PolicySection />
        <CapabilityGrid />
        <AuditPreview />
        <AwsArchitecture />
        <CtaSection />
      </main>
      <WelcomeFooter />
    </div>
  );
}
