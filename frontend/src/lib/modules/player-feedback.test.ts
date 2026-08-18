import { afterEach, describe, expect, it, vi } from "vitest";
import { getFeedbackUrl } from "./player-feedback";

describe("player feedback WebSocket contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the page token when present", () => {
    vi.stubGlobal("window", {
      location: {
        protocol: "https:",
        host: "example.com",
        search: "?token=query token",
      },
    });

    expect(getFeedbackUrl()).toBe(
      "wss://example.com/ws/player-feedback?token=query%20token",
    );
  });

  it("falls back to the stored auth token", () => {
    vi.stubGlobal("window", {
      location: {
        protocol: "http:",
        host: "localhost:9999",
        search: "",
      },
    });
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => "stored token"),
    });

    expect(getFeedbackUrl()).toBe(
      "ws://localhost:9999/ws/player-feedback?token=stored%20token",
    );
  });
});
