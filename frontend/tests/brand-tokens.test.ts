import { describe, expect, it } from "vitest";
import config from "../tailwind.config";

describe("DN brand tokens", () => {
  const colors = (config.theme?.extend?.colors as { dn: Record<string, string> } | undefined)?.dn;

  it("loads every brand colour", () => {
    expect(colors).toBeDefined();
    const required = [
      "dark",
      "steel",
      "steel-lt",
      "gold",
      "gold-lt",
      "fog",
      "muted",
      "green",
      "red",
      "amber",
    ];
    for (const key of required) {
      expect(colors).toHaveProperty(key);
    }
  });

  it("uses the exact hex values from docs/brand-tokens.md", () => {
    // DN reference palette — see docs/brand-tokens.md
    expect(colors?.dark).toBe("#1C1C1C");
    expect(colors?.steel).toBe("#4A7FA5");
    expect(colors?.["steel-lt"]).toBe("#D6E4F0");
    expect(colors?.gold).toBe("#C9A84C");
    expect(colors?.["gold-lt"]).toBe("#FFF8E6");
    expect(colors?.fog).toBe("#F4F4F2");
    expect(colors?.muted).toBe("#6B7280");
    expect(colors?.green).toBe("#1E8449");
    expect(colors?.red).toBe("#C0392B");
    expect(colors?.amber).toBe("#D4AC0D");
  });
});
