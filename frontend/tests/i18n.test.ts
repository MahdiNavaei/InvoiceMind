import { describe, expect, it } from "vitest";
import { getDict } from "../lib/i18n";

describe("i18n dictionary", () => {
  it("returns english keys", () => {
    const d = getDict("en");
    expect(d.dashboard).toBe("Dashboard");
  });

  it("returns persian keys", () => {
    const d = getDict("fa");
    expect(d.dashboard).toBe("داشبورد");
  });
});
