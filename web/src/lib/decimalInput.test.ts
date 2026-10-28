import { describe, expect, it } from "vitest";
import { formatFixedDecimal, parseLocaleDecimal } from "./decimalInput";

describe("parseLocaleDecimal / formatFixedDecimal", () => {
  it("parses comma or dot as decimal separator", () => {
    expect(parseLocaleDecimal("3,977")).toBe(3.977);
    expect(parseLocaleDecimal("3.977")).toBe(3.977);
    expect(parseLocaleDecimal(" 12,5 ")).toBe(12.5);
  });

  it("rejects empty / invalid and formats with a dot", () => {
    expect(parseLocaleDecimal("")).toBeNull();
    expect(parseLocaleDecimal("abc")).toBeNull();
    expect(formatFixedDecimal(3.977, 1)).toBe("4.0");
    expect(formatFixedDecimal(3.977, 3)).toBe("3.977");
  });
});
