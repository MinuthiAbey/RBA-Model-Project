"use client";

import PhoneIphoneIcon from "@mui/icons-material/PhoneIphone";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import type { LabResult } from "@/lib/types";
import { SCORER_NAMES } from "./engine-settings";
import { flag } from "./labels";

const VIEW = {
  allow: { label: "Allowed", tone: "success", user: "Signed in. Nothing unusual, so no extra step." },
  otp: { label: "One-time code", tone: "warning", user: "“This sign-in looks unusual. Enter the code we sent to your phone.”" },
  block: { label: "Blocked", tone: "error", user: "“We couldn't sign you in right now. Please try again later.” (the reason is never shown)" },
} as const;

function OtpStep({ code, username, onDone }: { code: string; username: string; onDone: () => void }) {
  const [entered, setEntered] = useState("");
  const [message, setMessage] = useState<{ tone: "success" | "error" | "warning"; text: string } | null>(null);

  async function verify(value: string) {
    const response = await fetch("/api/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: value }) });
    const body = await response.json().catch(() => ({}));
    if (response.ok) {
      setMessage({ tone: "success", text: `Code accepted, ${username} is signed in. This sign-in is now part of their history.` });
      onDone();
    } else {
      setMessage({ tone: body.blocked ? "error" : "warning", text: body.blocked ? "Three wrong codes: the sign-in is blocked." : body.error });
    }
  }

  return (
    <Box>
      <Box sx={{ p: 2, borderRadius: 3, bgcolor: "#0f172a", color: "white", maxWidth: 360 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", opacity: 0.7 }}>
          <PhoneIphoneIcon fontSize="small" />
          <Typography variant="caption">{username}’s phone · Messages · now</Typography>
        </Stack>
        <Typography sx={{ mt: 1 }}>Your LightRBA sign-in code is <b style={{ letterSpacing: "0.15em" }}>{code}</b></Typography>
      </Box>
      <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
        <TextField size="small" label="Code" value={entered} onChange={(e) => setEntered(e.target.value.replace(/\D/g, "").slice(0, 6))}
                   slotProps={{ htmlInput: { inputMode: "numeric" } }} />
        <Button variant="contained" onClick={() => verify(entered)} disabled={entered.length !== 6}>Verify</Button>
        <Button onClick={() => verify("000000")} color="error">Wrong code</Button>
      </Stack>
      {message && <Alert severity={message.tone} sx={{ mt: 2 }}>{message.text}</Alert>}
    </Box>
  );
}

function Comparison({ result }: { result: LabResult }) {
  if (!result.comparison?.length) return null;
  return (
    <>
      <Typography variant="overline" color="text.secondary" sx={{ display: "block", mt: 3 }}>
        The same sign-in, every model · {Math.round(Number(result.budget) * 100)}% budget
      </Typography>
      <Stack spacing={1} sx={{ mt: 0.5 }}>
        {result.comparison.map((row) => (
          <Stack key={row.scorer} direction="row" spacing={1.5}
                 sx={{ alignItems: "center", p: 1, borderRadius: 2, bgcolor: row.scorer === result.scorer ? "rgba(61,90,254,0.07)" : "transparent" }}>
            <Typography sx={{ width: 150, fontWeight: row.scorer === result.scorer ? 700 : 500 }}>{SCORER_NAMES[row.scorer] ?? row.scorer}</Typography>
            <Typography sx={{ width: 56, fontWeight: 700, textAlign: "right" }}>{row.score}</Typography>
            <Box sx={{ width: 130 }}>
              <Chip label={row.trusted ? "Remembered" : VIEW[row.decision].label} color={VIEW[row.decision].tone} size="small" />
            </Box>
            <Typography variant="body2" color="text.secondary" noWrap sx={{ flex: 1 }}>{row.reason ?? "nothing unusual"}</Typography>
          </Stack>
        ))}
      </Stack>
    </>
  );
}

export default function ResultPanel({ result, username, onSignedIn }: {
  result: LabResult | null;
  username: string;
  onSignedIn: () => void;
}) {
  if (!result) {
    return (
      <Card sx={{ height: "100%" }}>
        <CardContent sx={{ p: 4, textAlign: "center", color: "text.secondary" }}>
          <Typography variant="h6" color="text.primary">No sign-in yet</Typography>
          <Typography sx={{ mt: 1 }}>Change anything on the left and press Sign in. The decision and its reasons appear here.</Typography>
        </CardContent>
      </Card>
    );
  }

  if (result.outcome === "wrong_password") {
    return (
      <Card>
        <CardContent sx={{ p: 4 }}>
          <Chip label="Wrong password" variant="outlined" />
          <Alert severity="error" sx={{ mt: 2 }}>What {username} sees: “Wrong username or password.”</Alert>
          <Typography color="text.secondary" sx={{ mt: 2 }}>
            The password check failed, so the attempt was never scored. It still counts towards the failed-attempts signal for this user.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const view = VIEW[result.outcome];
  const context = result.context!;
  return (
    <Card>
      <CardContent sx={{ p: 4 }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
          <Box>
            <Typography variant="overline" color="text.secondary">Decision</Typography>
            <Box><Chip label={view.label} color={view.tone} sx={{ fontSize: 16, height: 34, px: 1 }} /></Box>
          </Box>
          <Box sx={{ textAlign: "right" }}>
            <Typography variant="overline" color="text.secondary">Risk</Typography>
            <Typography variant="h3" sx={{ lineHeight: 1 }}>{result.score}<Typography component="span" color="text.secondary">/100</Typography></Typography>
          </Box>
        </Stack>
        <LinearProgress variant="determinate" value={result.score ?? 0} color={view.tone} sx={{ height: 10, borderRadius: 5, mt: 2 }} />
        <Typography variant="caption" color="text.secondary">
          Riskier than {result.score}% of normal sign-ins · scored in {result.scoring_ms} ms by the {SCORER_NAMES[result.scorer ?? ""]} ·{" "}
          {Math.round(Number(result.budget) * 100)}% challenge budget
        </Typography>

        <Typography variant="overline" color="text.secondary" sx={{ display: "block", mt: 3 }}>Why</Typography>
        {result.reasons && result.reasons.length > 0 ? (
          <Stack spacing={1}>
            {result.reasons.map((reason) => (
              <Stack key={reason.code} direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                <Chip label={`+${reason.weight.toFixed(2)}`} size="small" variant="outlined" sx={{ minWidth: 58 }} />
                <Typography>{reason.text}</Typography>
              </Stack>
            ))}
          </Stack>
        ) : (
          <Typography color="text.secondary">Nothing unusual about this sign-in.</Typography>
        )}

        {result.trusted_since && (
          <Alert severity="info" variant="outlined" sx={{ mt: 3 }}>
            <b>Remembered.</b> This country, network and device were verified with a one-time code on{" "}
            {new Date(result.trusted_since).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}, so no code is
            needed this time. The risk score is unchanged, and trust lasts 30 days. It never applies after recent wrong
            passwords and never overrides a block.
          </Alert>
        )}

        {result.trust_paused && (
          <Alert severity="warning" variant="outlined" sx={{ mt: 3 }}>
            <b>Remembered, but not trusted right now:</b> {result.trust_paused}. A code is needed until that clears.
          </Alert>
        )}

        <Comparison result={result} />

        <Typography variant="overline" color="text.secondary" sx={{ display: "block", mt: 3 }}>What the engine saw</Typography>
        <Typography variant="body2" color="text.secondary">
          {context.country ? `${flag(context.country)} ${context.country}` : "unknown"} · AS{context.asn} · {context.ip} · {context.device_type} ·{" "}
          {context.browser} on {context.os} · {new Date(context.time).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })} ·{" "}
          {context.prior_logins} earlier sign-ins
        </Typography>

        <Divider sx={{ my: 3 }} />
        <Typography variant="overline" color="text.secondary">What {username} sees</Typography>
        <Alert severity={view.tone} sx={{ mt: 1, mb: result.outcome === "otp" ? 2 : 0 }}>
          {result.trusted_since ? "Signed in. This device and place were verified before, so no code this time." : view.user}
        </Alert>
        {result.outcome === "otp" && result.phone && <OtpStep code={result.phone} username={username} onDone={onSignedIn} />}
      </CardContent>
    </Card>
  );
}
