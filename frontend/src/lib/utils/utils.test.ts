import { describe, it, expect } from "vitest";
import { formatTime, formatBytes, formatTimestamp } from "./format";

describe("formatTime", () => {
  it("formats 0 seconds as 0:00", () => {
    expect(formatTime(0)).toBe("0:00");
  });

  it("formats 59 seconds as 0:59", () => {
    expect(formatTime(59)).toBe("0:59");
  });

  it("formats 60 seconds as 1:00", () => {
    expect(formatTime(60)).toBe("1:00");
  });

  it("formats 125 seconds as 2:05", () => {
    expect(formatTime(125)).toBe("2:05");
  });

  it("formats 3661 seconds as 61:01", () => {
    expect(formatTime(3661)).toBe("61:01");
  });

  it("handles fractional seconds by flooring", () => {
    expect(formatTime(60.9)).toBe("1:00");
  });
});

describe("formatBytes", () => {
  it("formats bytes under 1KB", () => {
    expect(formatBytes(500)).toBe("500 B");
  });

  it("formats KB", () => {
    expect(formatBytes(1536)).toBe("1.5 KB");
  });

  it("formats MB", () => {
    expect(formatBytes(1572864)).toBe("1.5 MB");
  });

  it("formats GB", () => {
    expect(formatBytes(1610612736)).toBe("1.50 GB");
  });
});

describe("formatTimestamp", () => {
  it("formats numeric timestamp", () => {
    const result = formatTimestamp(0);
    expect(result).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it("formats ISO string", () => {
    const result = formatTimestamp("2026-05-03T12:00:00Z");
    expect(result).toMatch(/\d{2}:\d{2}:\d{2}/);
  });
});
