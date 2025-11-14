import { describe, it, expect } from "vitest";
import en from "../../../messages/en.json";
import sv from "../../../messages/sv.json";

/**
 * Test to ensure all locale files have complete translations
 * This prevents missing translation keys across different languages
 */

describe("Locale Completeness", () => {
  /**
   * Helper function to get all nested keys from an object
   * e.g., { a: { b: "value" } } => ["a.b"]
   */
  function getAllKeys(obj: Record<string, any>, prefix = ""): string[] {
    let keys: string[] = [];

    for (const key in obj) {
      const fullKey = prefix ? `${prefix}.${key}` : key;

      if (typeof obj[key] === "object" && obj[key] !== null && !Array.isArray(obj[key])) {
        // Recursively get keys from nested objects
        keys = keys.concat(getAllKeys(obj[key], fullKey));
      } else {
        // Leaf node - add the full key path
        keys.push(fullKey);
      }
    }

    return keys.sort();
  }

  it("should have all English keys in Swedish locale", () => {
    const enKeys = getAllKeys(en);
    const svKeys = getAllKeys(sv);

    // Check if all English keys exist in Swedish
    const missingKeys = enKeys.filter((key) => !svKeys.includes(key));

    expect(
      missingKeys,
      `Missing Swedish translations for keys: ${missingKeys.join(", ")}`
    ).toHaveLength(0);
  });

  it("should have all Swedish keys in English locale", () => {
    const enKeys = getAllKeys(en);
    const svKeys = getAllKeys(sv);

    // Check if all Swedish keys exist in English (no extra keys)
    const extraKeys = svKeys.filter((key) => !enKeys.includes(key));

    expect(
      extraKeys,
      `Extra Swedish keys not in English: ${extraKeys.join(", ")}`
    ).toHaveLength(0);
  });

  it("should have exactly the same keys in both locales", () => {
    const enKeys = getAllKeys(en);
    const svKeys = getAllKeys(sv);

    expect(enKeys).toEqual(svKeys);
  });

  it("should not have any empty string values in English", () => {
    const enKeys = getAllKeys(en);
    const emptyKeys: string[] = [];

    enKeys.forEach((key) => {
      const keys = key.split(".");
      let value: any = en;

      for (const k of keys) {
        value = value[k];
      }

      if (typeof value === "string" && value.trim() === "") {
        emptyKeys.push(key);
      }
    });

    expect(
      emptyKeys,
      `Empty English translations: ${emptyKeys.join(", ")}`
    ).toHaveLength(0);
  });

  it("should not have any empty string values in Swedish", () => {
    const svKeys = getAllKeys(sv);
    const emptyKeys: string[] = [];

    svKeys.forEach((key) => {
      const keys = key.split(".");
      let value: any = sv;

      for (const k of keys) {
        value = value[k];
      }

      if (typeof value === "string" && value.trim() === "") {
        emptyKeys.push(key);
      }
    });

    expect(
      emptyKeys,
      `Empty Swedish translations: ${emptyKeys.join(", ")}`
    ).toHaveLength(0);
  });

  it("should have matching structure between locales", () => {
    // Verify top-level keys match
    const enTopLevel = Object.keys(en).sort();
    const svTopLevel = Object.keys(sv).sort();

    expect(svTopLevel).toEqual(enTopLevel);
  });
});
