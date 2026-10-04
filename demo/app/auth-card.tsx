"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import { useState } from "react";

// Shared card for the sign-in and one-time-code steps: posts JSON and follows the `next` page the API returns.
export default function AuthCard({ title, intro, action, submitLabel, values, children }: {
  title: string;
  intro: string;
  action: string;
  submitLabel: string;
  values: Record<string, string>;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const response = await fetch(action, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    const result = await response.json().catch(() => ({}));
    setBusy(false);
    if (result.next) {
      router.push(result.next);
      router.refresh();
    }
    if (!response.ok) setError(result.error ?? "Something went wrong.");
  }

  return (
    <Card sx={{ boxShadow: "0 12px 40px rgba(15,23,42,0.08)" }}>
      <CardContent component="form" onSubmit={submit} sx={{ p: 4 }}>
        <Typography variant="h4">{title}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>{intro}</Typography>
        <Box sx={{ display: "grid", gap: 2.5 }}>{children}</Box>
        {error && <Alert severity="error" sx={{ mt: 2.5 }}>{error}</Alert>}
        <Button type="submit" variant="contained" size="large" fullWidth disabled={busy} sx={{ mt: 3 }}>
          {busy ? "Checking…" : submitLabel}
        </Button>
      </CardContent>
    </Card>
  );
}
