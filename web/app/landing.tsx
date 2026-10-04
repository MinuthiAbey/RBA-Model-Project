"use client";

import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import ChatBubbleOutlinedIcon from "@mui/icons-material/ChatBubbleOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import type { ResultsSummary } from "@/lib/results";
import { NAVY } from "./theme";

const pct = (value: number) => `${Math.round(value * 100)}%`;

// What the live demo decided for these three sign-ins.
const EXAMPLES = [
  { who: "alice · Norway · her usual Mac", risk: 10, label: "Allowed", color: "success" as const },
  { who: "alice · United States · new Android phone", risk: 91, label: "One-time code", color: "warning" as const },
  { who: "attacker · leaked password · 3 wrong codes", risk: 91, label: "Blocked", color: "error" as const },
];

const FEATURES = [
  { icon: <BoltOutlinedIcon />, title: "Score", text: "Every sign-in gets a 0–100 risk score in milliseconds." },
  { icon: <RuleOutlinedIcon />, title: "Decide", text: "Allow it, ask for a one-time code, or block it." },
  { icon: <ChatBubbleOutlinedIcon />, title: "Explain", text: "Each decision comes with plain-English reasons." },
];

export default function Landing({ results }: { results: ResultsSummary | null }) {
  const rf = results?.scorers.find((s) => s.scorer === "rforest");
  const stats = results && rf ? [
    { value: rf.auc.toFixed(2), label: "ROC AUC on real attacks" },
    { value: pct(rf.stopRate), label: "of attacks stopped" },
    { value: `${(rf.challengeRate * 100).toFixed(1)}%`, label: "of real users challenged" },
    { value: `${rf.latencyMs.toFixed(1)} ms`, label: "to score a sign-in" },
  ] : [];

  return (
    <main>
      <Box sx={{ bgcolor: NAVY, color: "white", backgroundImage: "radial-gradient(circle at 80% 0%, rgba(61,90,254,0.45), transparent 55%)" }}>
        <Box className="mx-auto grid max-w-7xl gap-12 px-4 py-20 md:grid-cols-2 md:items-center">
          <Box>
            <Typography variant="h2" component="h1" sx={{ fontSize: { xs: 38, md: 52 }, lineHeight: 1.1 }}>
              Stop account takeovers without getting in real users’ way
            </Typography>
            <Typography sx={{ mt: 3, fontSize: 18, color: "rgba(255,255,255,0.75)", maxWidth: 520 }}>
              A stolen password isn’t enough. LightRBA scores every sign-in and asks for more proof only when something looks wrong.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 4 }}>
              <Button component={Link} href="/demo" size="large" variant="contained">Try the live demo</Button>
              <Button component={Link} href="/signup" size="large" variant="outlined" sx={{ color: "white", borderColor: "rgba(255,255,255,0.35)" }}>
                Create an account
              </Button>
            </Stack>
          </Box>
          <Stack spacing={2}>
            {EXAMPLES.map((example) => (
              <Box key={example.who} sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", gap: 2 }}>
                  <Typography sx={{ fontWeight: 600 }}>{example.who}</Typography>
                  <Chip label={example.label} color={example.color} size="small" />
                </Stack>
                <LinearProgress variant="determinate" value={example.risk} color={example.color}
                                sx={{ mt: 1.5, height: 8, borderRadius: 4, bgcolor: "rgba(255,255,255,0.1)" }} />
              </Box>
            ))}
          </Stack>
        </Box>
      </Box>

      <Box className="mx-auto max-w-7xl px-4 py-16">
        {stats.length > 0 && (
          <Card sx={{ mb: 6 }}>
            <Box className="grid grid-cols-2 md:grid-cols-4">
              {stats.map((stat) => (
                <Box key={stat.label} sx={{ p: 3 }}>
                  <Typography variant="h3" sx={{ color: "primary.main" }}>{stat.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{stat.label}</Typography>
                </Box>
              ))}
            </Box>
            <Box sx={{ px: 3, pb: 2 }}>
              <Button component={Link} href="/models" endIcon={<ArrowForwardIcon />}>Compare the models</Button>
            </Box>
          </Card>
        )}
        <Box className="grid gap-6 md:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                  <Box sx={{ width: 44, height: 44, borderRadius: 2, display: "grid", placeItems: "center", bgcolor: "rgba(61,90,254,0.1)", color: "primary.main" }}>
                    {feature.icon}
                  </Box>
                  <Typography variant="h6">{feature.title}</Typography>
                </Stack>
                <Typography color="text.secondary" sx={{ mt: 1.5 }}>{feature.text}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>
    </main>
  );
}
