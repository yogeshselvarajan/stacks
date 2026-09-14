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

  it("lists only real, actually-used AWS services", () => {
    render(<WelcomeFooter />);
    expect(screen.getByText("Amazon Bedrock")).toBeInTheDocument();
    expect(screen.getByText("Bedrock AgentCore Runtime")).toBeInTheDocument();
    expect(screen.getByText("AgentCore Memory")).toBeInTheDocument();
    expect(screen.getByText("Bedrock Guardrails")).toBeInTheDocument();
    expect(screen.getByText("Amazon DynamoDB")).toBeInTheDocument();
    expect(screen.getByText("Amazon Cognito")).toBeInTheDocument();
  });

});
