import { describe, expect, it } from "vitest";
import config from "../tailwind.config";

describe("DN brand tokens", () => {
  const colors = (config.theme?.extend?.colors as { dn: Record<string, string> } | undefined)?.dn;

  it("loads every brand colour", () => {
    expect(colors).toBeDefined();
    const required = [
      "dark",
      "navy",
      "navy-lt",
      "amber",
      "amber-lt",
      "fog",
      "sand",
      "muted",
      "green",
      "red",
    ];
    for (const key of required) {
      expect(colors).toHaveProperty(key);
    }
  });

  it("uses the exact hex values from docs/brand-tokens.md", () => {
    // DN reference palette (navy + amber) — see docs/brand-tokens.md
    expect(colors?.dark).toBe("#0A192F");
    expect(colors?.navy).toBe("#0A192F");
    expect(colors?.["navy-lt"]).toBe("#DCE3ED");
    expect(colors?.amber).toBe("#D97706");
    expect(colors?.["amber-lt"]).toBe("#FFF6E5");
    expect(colors?.fog).toBe("#F7F3EA");
    expect(colors?.muted).toBe("#5C6B7D");
    expect(colors?.green).toBe("#1E7A4A");
    expect(colors?.red).toBe("#C0392B");
  });
});
