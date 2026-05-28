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
    // Savanna Sky palette — see docs/brand-tokens.md
    expect(colors?.dark).toBe("#1E0F05");
    expect(colors?.steel).toBe("#1B4F72");
    expect(colors?.["steel-lt"]).toBe("#D0E8F5");
    expect(colors?.gold).toBe("#C9A84C");
    expect(colors?.["gold-lt"]).toBe("#FEF3CC");
    expect(colors?.fog).toBe("#F7EFE0");
    expect(colors?.muted).toBe("#7D6245");
    expect(colors?.green).toBe("#1A6B40");
    expect(colors?.red).toBe("#A83822");
    expect(colors?.amber).toBe("#C47B2E");
  });
});
