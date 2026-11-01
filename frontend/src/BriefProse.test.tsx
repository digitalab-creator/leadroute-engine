import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BriefProse } from "./BriefProse";

describe("BriefProse", () => {
  it("renders BC and PP ids as cite tags", () => {
    render(<BriefProse text="Stargo quotes lanes in minutes [PP-2] and serves forwarders [BC-1]." />);
    const citeTags = screen.getAllByTitle(/Approved claim id/);
    expect(citeTags).toHaveLength(2);
    expect(citeTags.map((node) => node.textContent)).toEqual(["PP-2", "BC-1"]);
  });
});
