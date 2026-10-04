"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import AuthCard from "../auth-card";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  return (
    <Box className="mx-auto max-w-md px-4 py-16">
      <AuthCard title="Sign in" intro="Welcome back to LightRBA." action="/api/login" submitLabel="Sign in"
                values={{ username, password }}>
        <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                   autoComplete="current-password" required />
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Typography variant="body2" color="text.secondary">Demo users:</Typography>
          {["alice", "bob", "charlie"].map((name) => (
            <Chip key={name} label={name} variant="outlined" color="primary" clickable
                  onClick={() => { setUsername(name); setPassword("demo1234"); }} />
          ))}
        </Stack>
      </AuthCard>
    </Box>
  );
}
