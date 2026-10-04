"use client";

import PhoneIphoneIcon from "@mui/icons-material/PhoneIphone";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import AuthCard from "../auth-card";

export default function VerifyPage() {
  const [code, setCode] = useState("");
  const [sms, setSms] = useState<{ username: string; code: string } | null>(null);

  // The demo has no real phones, so the "text message" appears right here.
  useEffect(() => {
    fetch("/api/verify").then((r) => (r.ok ? r.json() : null)).then(setSms);
  }, []);

  return (
    <Box className="mx-auto max-w-md px-4 py-16">
      {sms && (
        <Box sx={{ p: 2, mb: 3, borderRadius: 3, bgcolor: "#0f172a", color: "white" }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", opacity: 0.7 }}>
            <PhoneIphoneIcon fontSize="small" />
            <Typography variant="caption">{sms.username}’s phone · Messages · now</Typography>
          </Stack>
          <Typography sx={{ mt: 1 }}>Your LightRBA sign-in code is <b style={{ letterSpacing: "0.15em" }}>{sms.code}</b></Typography>
        </Box>
      )}
      <AuthCard title="Check it’s you" intro="This sign-in looks unusual, so we sent a 6-digit code to your phone."
                action="/api/verify" submitLabel="Verify" values={{ code }}>
        <TextField label="One-time code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                   autoComplete="one-time-code" required
                   slotProps={{ htmlInput: { inputMode: "numeric", style: { letterSpacing: "0.5em", fontSize: 24, fontWeight: 700 } } }} />
      </AuthCard>
    </Box>
  );
}
