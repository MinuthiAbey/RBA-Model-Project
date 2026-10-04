import type { LabOptions } from "@/lib/types";

// Two-letter country code to its flag emoji (regional indicator letters).
export function flag(country: string): string {
  return String.fromCodePoint(...[...country.toUpperCase()].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65));
}

export function countryName(options: LabOptions, country: string): string {
  return options.locations.find((l) => l.country === country)?.name ?? country;
}

export function hourLabel(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}
