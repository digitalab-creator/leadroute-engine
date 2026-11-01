import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./api", () => ({
  fetchLeads: vi.fn(() => Promise.resolve([])),
  fetchOptions: vi.fn(() =>
    Promise.resolve({ channels: ["email_reply"], sources: ["paid"] }),
  ),
  fetchKpi: vi.fn(() => new Promise(() => undefined)),
  fetchVisibility: vi.fn(() => new Promise(() => undefined)),
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "The request failed",
}));

describe("App shell", () => {
  it("shows the four operator routes in the nav", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("LeadRoute")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Queue" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "KPI pack" })).toHaveAttribute("href", "/kpi");
    expect(screen.getByRole("link", { name: "AI visibility" })).toHaveAttribute(
      "href",
      "/visibility",
    );
  });
});
