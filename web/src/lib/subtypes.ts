/** Taxonomy from SPEC section 2 — used by the add/edit forms. */
export const SUBTYPES: Record<string, string[]> = {
  ceiling_fan: ["ceiling_fan", "fan_light"],
  light: ["recessed", "recessed_vapor_proof", "pendant", "wall", "exterior_wall"],
  switch: [
    "single_pole",
    "three_way",
    "three_way_dimmer",
    "dimmer",
    "fan",
    "vacancy_sensor",
    "astronomical_timer",
  ],
  receptacle: [
    "duplex",
    "afci",
    "afci_half_hot",
    "gfci",
    "gfci_weatherproof",
    "gfci_240v",
    "gfci_microwave",
    "gfci_dishwasher",
    "range_hood",
    "fan_coil_dedicated",
    "240v",
  ],
  exhaust_fan: ["bath_exhaust", "indoor_air_quality"],
  detector: ["smoke", "smoke_co"],
  junction_box: ["junction_box"],
};

export function defaultSubtype(category: string): string {
  return SUBTYPES[category]?.[0] ?? category;
}
