import { describe, expect, it } from "vitest";
import { isHlsErrorData, isHlsLevelUpdatedData } from "./hls-guards";

describe("isHlsErrorData", () => {
  it("accepts a valid hls.js error payload", () => {
    expect(
      isHlsErrorData({ type: "networkError", fatal: true, details: "x" }),
    ).toBe(true);
  });

  it("accepts missing details (hls.js sometimes omits it)", () => {
    expect(isHlsErrorData({ type: "mediaError", fatal: false })).toBe(true);
  });

  it("rejects non-object payloads", () => {
    expect(isHlsErrorData(null)).toBe(false);
    expect(isHlsErrorData("error")).toBe(false);
    expect(isHlsErrorData(42)).toBe(false);
    expect(isHlsErrorData(undefined)).toBe(false);
  });

  it("rejects arrays and malformed fields", () => {
    expect(isHlsErrorData([])).toBe(false);
    expect(isHlsErrorData({ type: 42, fatal: true })).toBe(false);
    expect(isHlsErrorData({ type: "x", fatal: "yes" })).toBe(false);
    expect(isHlsErrorData({ type: "x", fatal: true, details: 42 })).toBe(false);
  });
});

describe("isHlsLevelUpdatedData", () => {
  it("accepts a valid level-updated payload", () => {
    expect(
      isHlsLevelUpdatedData({ level: 0, details: { bitrate: 1500000 } }),
    ).toBe(true);
  });

  it("accepts level without details", () => {
    expect(isHlsLevelUpdatedData({ level: 1 })).toBe(true);
  });

  it("rejects non-object payloads", () => {
    expect(isHlsLevelUpdatedData(null)).toBe(false);
    expect(isHlsLevelUpdatedData("x")).toBe(false);
    expect(isHlsLevelUpdatedData(undefined)).toBe(false);
  });

  it("rejects malformed fields", () => {
    expect(isHlsLevelUpdatedData({ level: "0" })).toBe(false);
    expect(isHlsLevelUpdatedData({ details: { bitrate: "1.5M" } })).toBe(false);
    expect(
      isHlsLevelUpdatedData({ level: 0, details: { totalduration: "10s" } }),
    ).toBe(false);
  });
});
