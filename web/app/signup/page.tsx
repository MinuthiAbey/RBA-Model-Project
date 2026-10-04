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

export default function SignupPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const { data } = usePlatformData();
  const conditions = useConditions(data, "");

  return (
    <Box className="mx-auto grid max-w-6xl gap-6 px-4 py-12 md:grid-cols-2 md:items-start">
      <AuthCard title="Create an account" intro="Where you sign up from becomes your first known place and device."
                action="/api/signup" submitLabel="Create account" values={{ username, password, confirm, simulate: conditions.simulate }}
                footer={<Typography variant="body2" color="text.secondary">Already have an account? <Link component={NextLink} href="/login">Sign in</Link></Typography>}>
        <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value.toLowerCase())} autoComplete="username"
                   helperText="3–20 lowercase letters, digits or underscores" required />
        <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                   autoComplete="new-password" helperText="At least 8 characters" required />
        <TextField label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
                   autoComplete="new-password" required />
      </AuthCard>
      {data && conditions.sim && (
        <ConditionsCard options={data.options} profile={undefined} username="" sim={conditions.sim} setSim={conditions.setSim}
                        simulated={conditions.simulated} setSimulated={conditions.setSimulated} />
      )}
    </Box>
  );
}
