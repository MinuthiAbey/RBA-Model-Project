"use client";

import { useCallback, useEffect, useState } from "react";
import type { LabOptions, Profile } from "@/lib/types";

export type PlatformData = {
  profiles: Record<string, Profile>;
  options: LabOptions;
  info: { scorer: string; challenge_budget: number };
};

// Users, their usual sign-ins and the condition choices, from the scoring API.
export function usePlatformData() {
  const [data, setData] = useState<PlatformData | null>(null);
  const [offline, setOffline] = useState(false);

  const reload = useCallback(async () => {
    const response = await fetch("/api/demo/options").catch(() => null);
    if (!response?.ok) return setOffline(true);
    setData(await response.json());
  }, []);

  useEffect(() => { reload(); }, [reload]);
  return { data, offline, reload };
}
