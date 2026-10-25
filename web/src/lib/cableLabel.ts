import type { CableType } from "@/types/contracts";

/** Human label for cable type, e.g. nm_14_2 -> "14/2". */
export function cableTypeLabel(cableType: CableType): string {
  if (cableType === "nm_14_2") return "14/2";
  if (cableType === "nm_14_3") return "14/3";
  return cableType;
}

/** Wire overlay caption: "14/2 - 12.4 ft". */
export function wireRunLabel(cableType: CableType, totalLengthFt: number): string {
  return `${cableTypeLabel(cableType)} - ${totalLengthFt.toFixed(1)} ft`;
}
