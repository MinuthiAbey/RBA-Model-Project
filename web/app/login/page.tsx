"use client";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import { useState } from "react";
import AuthCard from "../auth-card";
import { ConditionsCard } from "../conditions";
import { useConditions } from "../use-conditions";
import { usePlatformData } from "../use-platform-data";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { data } = usePlatformData();
  const conditions = useConditions(data, username.trim().toLowerCase());

  return (
    <Box className="mx-auto grid max-w-6xl gap-6 px-4 py-12 md:grid-cols-2 md:items-start">
      <AuthCard title="Sign in" intro="Welcome back." action="/api/login" submitLabel="Sign in"
                values={{ username, password, simulate: conditions.simulate }}
                footer={<Typography variant="body2" color="text.secondary">New here? <Link component={NextLink} href="/signup">Create an account</Link></Typography>}>
        <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                   autoComplete="current-password" required />
      </AuthCard>
      {data && conditions.sim && (
        <ConditionsCard options={data.options} profile={conditions.profile} username={username.trim().toLowerCase()}
                        sim={conditions.sim} setSim={conditions.setSim}
                        simulated={conditions.simulated} setSimulated={conditions.setSimulated} />
      )}
    </Box>
  );
}
