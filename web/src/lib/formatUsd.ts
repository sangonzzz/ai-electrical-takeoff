/** USD for UI / e2e: `$1,234.56` (comma thousands, two decimals). */
export function formatUsd(amount: number): string {
  return `$${amount.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
