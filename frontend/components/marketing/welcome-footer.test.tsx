import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WelcomeFooter } from "./welcome-footer";

describe("WelcomeFooter", () => {
  it("links the real attribution lines verbatim, never invented URLs", () => {
    render(<WelcomeFooter />);
    expect(screen.getByRole("link", { name: "Yogesh Selvarajan" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/yogesh-selvarajan/",
    );
    expect(screen.getByRole("link", { name: "AWS Builder Center" })).toHaveAttribute(
      "href",
      "https://builder.aws.com/community/@yogeshs",
    );
  });

  it("lists only real, actually-used AWS services, each linked to its own official page", () => {
    render(<WelcomeFooter />);
    expect(screen.getByRole("link", { name: /Amazon Bedrock$/ })).toHaveAttribute("href", "https://aws.amazon.com/bedrock/");
    expect(screen.getByRole("link", { name: /Bedrock AgentCore Runtime/ })).toHaveAttribute("href", "https://aws.amazon.com/bedrock/agentcore/");
    expect(screen.getByRole("link", { name: /AgentCore Memory/ })).toHaveAttribute(
      "href",
      "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-memory.html",
    );
    expect(screen.getByRole("link", { name: /Bedrock Guardrails/ })).toHaveAttribute("href", "https://aws.amazon.com/bedrock/guardrails/");
    expect(screen.getByRole("link", { name: /Amazon DynamoDB/ })).toHaveAttribute("href", "https://aws.amazon.com/dynamodb/");
    expect(screen.getByRole("link", { name: /Amazon Cognito/ })).toHaveAttribute("href", "https://aws.amazon.com/cognito/");
  });

  it("links the hackathon attribution to the real Agents for Humans devpost", () => {
    render(<WelcomeFooter />);
    expect(screen.getByRole("link", { name: /Agents for Humans hackathon/ })).toHaveAttribute(
      "href",
      "https://agentsforhumans.devpost.com/",
    );
  });

});
