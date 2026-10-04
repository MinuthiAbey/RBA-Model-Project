"use client";

import { useEffect, useState } from "react";
import type { Simulation } from "@/lib/types";
import { usualSimulation } from "./conditions";
import type { PlatformData } from "./use-platform-data";

// Conditions for the sign-in and sign-up forms; typing a known username starts from that user's usual sign-in.
export function useConditions(data: PlatformData | null, username: string) {
  const [sim, setSim] = useState<Simulation | null>(null);
  const [simulated, setSimulated] = useState(true);
  const profile = data?.profiles[username];

  useEffect(() => {
    if (data) setSim(usualSimulation(profile, data.options));
  }, [data, profile]);

  return { sim, setSim, simulated, setSimulated, profile, simulate: simulated && sim ? sim : undefined };
}
