"use client";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { LabResult, Simulation } from "@/lib/types";
import { usualSimulation } from "../conditions";
import { flag } from "../labels";
import { usePlatformData } from "../use-platform-data";
import Controls, { ResetButton } from "./controls";
import EngineSettings from "./engine-settings";
import ProfileCard from "./profile-card";
import ResultPanel from "./result-panel";

export default function DemoPage() {
  const router = useRouter();
  const { data, offline, reload } = usePlatformData();
  const [username, setUsername] = useState("alice");
  const [sim, setSim] = useState<Simulation | null>(null);
  const [failures, setFailures] = useState(0);
  const [password, setPassword] = useState("demo1234");
  const [result, setResult] = useState<LabResult | null>(null);
  const [scorer, setScorer] = useState("");
  const [budget, setBudget] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (data && !sim) {
      setSim(usualSimulation(data.profiles[username], data.options));
      setScorer(data.info.scorer);
      setBudget(String(data.info.challenge_budget));
    }
  }, [data, sim, username]);

  function reset(name = username) {
    if (!data) return;
    setSim(usualSimulation(data.profiles[name], data.options));
    setFailures(0);
    setPassword("demo1234");
  }

  function pickUser(name: string) {
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
    if (!response.ok) return setFailed(true);
    const outcome: LabResult = await response.json();
    setResult(outcome);
    if (outcome.outcome === "allow") signedIn();
  }

  function signedIn() {
    reload(); // the history has changed: the profile now includes this sign-in
    router.refresh();
  }

  if (offline || failed) return <Box className="mx-auto max-w-3xl px-4 py-16"><Alert severity="error">The risk engine is offline.</Alert></Box>;
  if (!data || !sim) return null;
  const profile = data.profiles[username];

  return (
    <Box className="mx-auto max-w-7xl px-4 py-10">
      <Typography variant="h3">Live demo</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 4, maxWidth: 720 }}>
        Pick a user, change where and how they sign in, and see how each model responds.
      </Typography>

      <Box className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-5">
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 1.5 }}>1 · Pick a user</Typography>
            <TextField select fullWidth value={username} onChange={(e) => pickUser(e.target.value)} sx={{ mb: 2 }}>
              {Object.entries(data.profiles).map(([name, p]) => (
                <MenuItem key={name} value={name}>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", width: "100%" }}>
                    <Avatar sx={{ width: 26, height: 26, fontSize: 13, bgcolor: "primary.main" }}>{name[0].toUpperCase()}</Avatar>
                    <Typography sx={{ fontWeight: 600 }}>{name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ ml: "auto" }}>
                      {p.usual ? `${flag(p.usual.country)} · ` : ""}{p.logins} sign-ins
                    </Typography>
                  </Stack>
                </MenuItem>
              ))}
            </TextField>
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
