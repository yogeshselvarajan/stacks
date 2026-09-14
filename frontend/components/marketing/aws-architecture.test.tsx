import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AwsArchitecture } from "./aws-architecture";

describe("AwsArchitecture", () => {
  it("shows the real data-flow sequence, case to audit", () => {
    render(<AwsArchitecture />);
    expect(screen.getByText("Case")).toBeInTheDocument();
    expect(screen.getByText("Audit")).toBeInTheDocument();
    expect(screen.getByText("Amazon Bedrock")).toBeInTheDocument();
  });

  it("is anchorable from the nav via #built-on-aws", () => {
    const { container } = render(<AwsArchitecture />);
    expect(container.querySelector("#built-on-aws")).not.toBeNull();
  });
});
