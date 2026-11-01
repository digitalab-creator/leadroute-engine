import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, errorMessage, fetchKpi, fetchLeads } from "./api";

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 400,
    statusText: ok ? "OK" : "Bad Request",
    json: async () => body,
  } as Response;
}

describe("fetchLeads", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps snake_case lead rows into typed cards", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          leads: [
            {
              person_id: "p-1",
              name: "Ada Quote",
              company: "Example Forwarder",
              channel: "email_reply",
              channel_label: "Email reply",
              received_at_israel: "2026-10-06 14:30",
              score: 82,
              band: "A",
              status: "qualified",
              status_label: "Qualified lead",
              owner: "Noa",
            },
          ],
        }),
      ),
    );

    const leads = await fetchLeads();
    expect(leads).toHaveLength(1);
    expect(leads[0]?.personId).toBe("p-1");
    expect(leads[0]?.statusLabel).toBe("Qualified lead");
  });

  it("rejects a lead row that is missing a required field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          leads: [{ person_id: "p-1", name: "Ada" }],
        }),
      ),
    );

    await expect(fetchLeads()).rejects.toBeInstanceOf(ApiError);
  });

  it("surfaces API validation detail on HTTP 400", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Need email or LinkedIn" }, false)),
    );

    await expect(fetchLeads()).rejects.toThrow(/Need email or LinkedIn/);
  });
});

describe("fetchKpi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("marks unknown feeds without turning them into zero", async () => {
    const line = {
      actual: null,
      target: null,
      unknown: true,
      records: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          week_start: "2026-10-04",
          week_end: "2026-10-08",
          qls: { actual: 6, target: 25, unknown: false, records: [] },
          meetings_booked: { actual: 4, target: 15, unknown: false, records: [] },
          meetings_held: { actual: 3, target: 12, unknown: false, records: [] },
          opportunities: { actual: 2, target: 5, unknown: false, records: [] },
          by_source: { "historical-reactivation": line },
          expansion_meetings_booked: line,
          expansion_meetings_held: line,
          expansion_opportunities: line,
        }),
      ),
    );

    const pack = await fetchKpi();
    const reactivation = pack.bySource.find((row) => row.source === "historical-reactivation");
    expect(reactivation?.line.unknown).toBe(true);
    expect(reactivation?.line.actual).toBeNull();
  });
});

describe("errorMessage", () => {
  it("returns the Error message when present", () => {
    expect(errorMessage(new ApiError("bad shape"))).toBe("bad shape");
  });
});
