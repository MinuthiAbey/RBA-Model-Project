"use client";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { LabOptions, LabResult, Profile, Simulation } from "@/lib/types";
import Controls, { ResetButton } from "./controls";
import EngineSettings, { SCORER_NAMES } from "./engine-settings";
import ProfileCard from "./profile-card";
import ResultPanel from "./result-panel";

type LabData = { profiles: Record<string, Profile>; options: LabOptions; info: { scorer: string; challenge_budget: number } };

const USERS = [
  { name: "alice", about: "regular" },
  { name: "bob", about: "fairly new" },
  { name: "charlie", about: "brand new" },
];

function usualSimulation(profile: Profile, options: LabOptions): Simulation {
  const usual = profile.usual;
  if (!usual) return { country: options.locations[0].country, asn: options.locations[0].asns[0], ip: "new", device: options.devices[0].key, hour: new Date().getHours() };
  return { country: usual.country, asn: usual.asn, ip: "usual", device: usual.device ?? options.devices[0].key, hour: usual.hour ?? new Date().getHours() };
}

export default function DemoPage() {
  const router = useRouter();
  const [data, setData] = useState<LabData | null>(null);
  const [offline, setOffline] = useState(false);
  const [username, setUsername] = useState("alice");
  const [sim, setSim] = useState<Simulation | null>(null);
  const [failures, setFailures] = useState(0);
  const [password, setPassword] = useState("demo1234");
  const [result, setResult] = useState<LabResult | null>(null);
  const [scorer, setScorer] = useState("");
  const [budget, setBudget] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const response = await fetch("/api/demo/options");
    if (!response.ok) return setOffline(true);
    setData(await response.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  function reset(name = username, lab = data) {
    if (!lab) return;
    setSim(usualSimulation(lab.profiles[name], lab.options));
    setFailures(0);
    setPassword("demo1234");
  }

  useEffect(() => {
    if (data && !sim) {
      setSim(usualSimulation(data.profiles[username], data.options));
      setScorer(data.info.scorer);
      setBudget(String(data.info.challenge_budget));
    }
  }, [data, sim, username]);

  function pickUser(name: string | null) {
    if (!name || !data) return;
    setUsername(name);
    setResult(null);
    reset(name);
  }

  async function signIn() {
    setBusy(true);
    const response = await fetch("/api/demo/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, simulate: sim, failures, scorer, budget }),
    });
    setBusy(false);
    if (!response.ok) return setOffline(true);
    const outcome: LabResult = await response.json();
    setResult(outcome);
    if (outcome.outcome === "allow") signedIn();
  }

  function signedIn() {
    load(); // the history has changed: the profile now includes this sign-in
    router.refresh();
  }

  if (offline) return <Box className="mx-auto max-w-3xl px-4 py-16"><Alert severity="error">The risk engine is offline.</Alert></Box>;
  if (!data || !sim) return null;
  const profile = data.profiles[username];

  return (
    <Box className="mx-auto max-w-7xl px-4 py-10">
      <Typography variant="overline" color="primary">Live demo</Typography>
      <Typography variant="h3">Sign-in lab</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 4, maxWidth: 720 }}>
        Pick a user, change where and how they sign in, and see how each model responds.
      </Typography>

      <Box className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-5">
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 1.5 }}>1 · Pick a user</Typography>
            <ToggleButtonGroup exclusive fullWidth value={username} onChange={(_, name) => pickUser(name)} sx={{ mb: 2 }}>
              {USERS.map((user) => (
                <ToggleButton key={user.name} value={user.name} sx={{ py: 1.25, gap: 1, justifyContent: "flex-start" }}>
                  <Avatar sx={{ width: 28, height: 28, fontSize: 14, bgcolor: username === user.name ? "primary.main" : "grey.400" }}>
                    {user.name[0].toUpperCase()}
                  </Avatar>
                  <Box sx={{ textAlign: "left", textTransform: "none" }}>
                    <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{user.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{data.profiles[user.name].logins} sign-ins</Typography>
                  </Box>
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            <ProfileCard profile={profile} options={data.options} />

            <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mt: 4, mb: 1.5 }}>
              <Typography variant="h6">2 · Change the sign-in</Typography>
              <ResetButton onClick={() => reset()} />
            </Stack>
            <Controls options={data.options} usual={profile.usual} sim={sim} setSim={setSim}
                      failures={failures} setFailures={setFailures} password={password} setPassword={setPassword} />

            <Button fullWidth size="large" variant="contained" onClick={signIn} disabled={busy} sx={{ mt: 3 }}>
              {busy ? "Scoring…" : `3 · Sign in as ${username}`}
            </Button>
          </CardContent>
        </Card>

        <Stack className="lg:col-span-7" spacing={3}>
          <EngineSettings options={data.options} scorer={scorer} setScorer={setScorer} budget={budget} setBudget={setBudget} />
          <ResultPanel result={result} username={username} onSignedIn={signedIn} />
        </Stack>
      </Box>
    </Box>
  );
}
