"use client";

import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import ChatBubbleOutlinedIcon from "@mui/icons-material/ChatBubbleOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import LoginIcon from "@mui/icons-material/Login";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import type { ResultsSummary } from "@/lib/results";
import { NAVY } from "./theme";

const SCORER_NAMES: Record<string, [string, string]> = {
  rforest: ["Random Forest", "supervised machine learning"],
  iforest: ["Isolation Forest", "anomaly detection"],
  freeman: ["Freeman et al.", "statistical model"],
  rules: ["Fixed rules", "fixed points per warning sign"],
};
const pct = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`;

// What the live demo actually decided for these three sign-ins.
const EXAMPLES = [
  { who: "alice · Norway · her usual Mac", risk: 10, label: "Allowed", color: "success" as const },
  { who: "alice · United States · new Android phone", risk: 91, label: "One-time code", color: "warning" as const },
  { who: "attacker · leaked password · 3 wrong codes", risk: 91, label: "Blocked", color: "error" as const },
];

const STEPS = [
  { icon: <BoltOutlinedIcon />, title: "Score every sign-in", text: "16 signals, such as a new country, a new device, an odd hour or one IP trying many accounts, become a 0–100 risk score in milliseconds." },
  { icon: <RuleOutlinedIcon />, title: "Decide in proportion", text: "Low risk goes straight through, medium risk gets a one-time code, high risk is blocked. Thresholds are set to a challenge budget, so real users are rarely bothered." },
  { icon: <ChatBubbleOutlinedIcon />, title: "Explain every decision", text: "Each decision comes with plain-English reasons, like “new country NO → US”, so an administrator can see why." },
];

export default function Landing({ results }: { results: ResultsSummary | null }) {
  const rf = results?.scorers.find((s) => s.scorer === "rforest");

  return (
    <main>
      <Box sx={{ bgcolor: NAVY, color: "white", backgroundImage: "radial-gradient(circle at 80% 0%, rgba(61,90,254,0.45), transparent 55%)" }}>
        <Box className="mx-auto grid max-w-7xl gap-12 px-4 py-20 md:grid-cols-2 md:items-center">
          <Box>
            <Chip label="Final-year research project · Risk-based authentication" size="small"
                  sx={{ bgcolor: "rgba(0,191,165,0.15)", color: "secondary.main", mb: 3 }} />
            <Typography variant="h2" component="h1" sx={{ fontSize: { xs: 38, md: 52 }, lineHeight: 1.1 }}>
              Stop account takeovers without getting in real users’ way
            </Typography>
            <Typography sx={{ mt: 3, fontSize: 18, color: "rgba(255,255,255,0.75)", maxWidth: 560 }}>
              A stolen password should not be enough. LightRBA scores every sign-in in real time and asks for more proof
              only when something looks wrong, which matters most for small web apps whose users have hardly any login history.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 4 }}>
              <Button component={Link} href="/demo" size="large" variant="contained" startIcon={<LoginIcon />}>
                Try the live demo
              </Button>
              <Button component={Link} href="/dashboard" size="large" variant="outlined" startIcon={<DashboardOutlinedIcon />}
                      sx={{ color: "white", borderColor: "rgba(255,255,255,0.35)" }}>
                Open the security dashboard
              </Button>
            </Stack>
          </Box>

          <Card sx={{ bgcolor: "rgba(255,255,255,0.04)", borderColor: "rgba(255,255,255,0.12)", color: "white" }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="overline" sx={{ color: "rgba(255,255,255,0.6)" }}>Decisions from the live demo</Typography>
              <Stack spacing={2} sx={{ mt: 1 }}>
                {EXAMPLES.map((example) => (
                  <Box key={example.who} sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(255,255,255,0.06)" }}>
                    <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", gap: 2 }}>
                      <Typography sx={{ fontWeight: 600 }}>{example.who}</Typography>
                      <Chip label={example.label} color={example.color} size="small" />
                    </Stack>
                    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mt: 1.5 }}>
                      <LinearProgress variant="determinate" value={example.risk} color={example.color}
                                      sx={{ flex: 1, height: 8, borderRadius: 4, bgcolor: "rgba(255,255,255,0.1)" }} />
                      <Typography variant="body2" sx={{ width: 64, textAlign: "right", color: "rgba(255,255,255,0.75)" }}>
                        risk {example.risk}
                      </Typography>
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {results && rf && (
        <Box className="mx-auto max-w-7xl px-4" sx={{ mt: -5 }}>
          <Card sx={{ boxShadow: "0 12px 40px rgba(15,23,42,0.08)" }}>
            <Box className="grid grid-cols-2 md:grid-cols-4">
              {[
                { value: rf.auc.toFixed(2), label: "ROC AUC on real attacker traffic" },
                { value: pct(rf.stopRate), label: `of real attacks stopped while challenging ${pct(rf.challengeRate, 1)} of real users` },
                { value: pct(results.rforestAt10.stopRate), label: `stopped at a ${pct(results.rforestAt10.challengeRate)} challenge rate` },
                { value: `${rf.latencyMs.toFixed(1)} ms`, label: "to score one sign-in, reasons included" },
              ].map((stat) => (
                <Box key={stat.label} sx={{ p: 3, borderRight: { md: "1px solid" }, borderColor: { md: "divider" }, "&:last-child": { borderRight: 0 } }}>
                  <Typography variant="h3" sx={{ color: "primary.main" }}>{stat.value}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{stat.label}</Typography>
                </Box>
              ))}
            </Box>
          </Card>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
            Random Forest on the held-out test period (Dec 2020 – Feb 2021): {results.legitLogins.toLocaleString()} real logins
            and {results.realAttacks.toLocaleString()} real attacker-IP attempts.
          </Typography>
        </Box>
      )}

      <Box className="mx-auto max-w-7xl px-4 py-20">
        <Typography variant="overline" color="primary">How it works</Typography>
        <Typography variant="h3" sx={{ mb: 4 }}>Score, decide, explain</Typography>
        <Box className="grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <Card key={step.title}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ width: 44, height: 44, borderRadius: 2, display: "grid", placeItems: "center", bgcolor: "rgba(61,90,254,0.1)", color: "primary.main" }}>
                  {step.icon}
                </Box>
                <Typography variant="overline" color="text.secondary" sx={{ display: "block", mt: 2 }}>Step {i + 1}</Typography>
                <Typography variant="h6">{step.title}</Typography>
                <Typography color="text.secondary" sx={{ mt: 1 }}>{step.text}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {results && (
        <Box sx={{ bgcolor: "white", borderTop: "1px solid", borderBottom: "1px solid", borderColor: "divider" }}>
          <Box className="mx-auto grid max-w-7xl gap-12 px-4 py-20 lg:grid-cols-5">
            <Box className="lg:col-span-2">
              <Typography variant="overline" color="primary">The cold-start problem</Typography>
              <Typography variant="h3">Most attacks hit accounts with no history</Typography>
              <Typography variant="h2" sx={{ color: "primary.main", mt: 3 }}>{pct(results.noHistoryShare)}</Typography>
              <Typography color="text.secondary">
                of real attacker attempts in the test period targeted accounts with no earlier login. Fixed rules and the
                statistical model give every new user the maximum score, so they spend the whole budget on new users at random.
                The Random Forest still stopped {pct(results.rforestNoHistoryStop)} of those attacks.
              </Typography>
            </Box>
            <Box className="lg:col-span-3">
              <Typography variant="overline" color="primary">Four approaches, same data</Typography>
              <Card sx={{ mt: 1 }}>
                <Table size="small" sx={{ "& th": { whiteSpace: "nowrap" } }}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Approach</TableCell>
                      <TableCell align="right">ROC AUC</TableCell>
                      <TableCell align="right">Attacks stopped</TableCell>
                      <TableCell align="right">Users challenged</TableCell>
                      <TableCell align="right">Time / sign-in</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {[...results.scorers].sort((a, b) => b.auc - a.auc).map((s) => (
                      <TableRow key={s.scorer} sx={s.scorer === "rforest" ? { bgcolor: "rgba(61,90,254,0.06)" } : undefined}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {SCORER_NAMES[s.scorer][0]}
                            {s.scorer === "rforest" && <Chip label="Best" size="small" color="primary" sx={{ ml: 1, height: 20 }} />}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">{SCORER_NAMES[s.scorer][1]}</Typography>
                        </TableCell>
                        <TableCell align="right">{s.auc.toFixed(3)}</TableCell>
                        <TableCell align="right">{pct(s.stopRate, 1)}</TableCell>
                        <TableCell align="right">{pct(s.challengeRate, 1)}</TableCell>
                        <TableCell align="right">{s.latencyMs < 1 ? `${(s.latencyMs * 1000).toFixed(0)} µs` : `${s.latencyMs.toFixed(1)} ms`}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
                Real attacker-IP attempts, thresholds set beforehand on a validation period for a 5% challenge budget.
              </Typography>
            </Box>
          </Box>
        </Box>
      )}

      <Box className="mx-auto max-w-7xl px-4 py-20">
        <Card sx={{ bgcolor: NAVY, color: "white", borderColor: NAVY }}>
          <CardContent sx={{ p: { xs: 3, md: 5 } }}>
            <Box className="grid gap-8 md:grid-cols-2 md:items-center">
              <Box>
                <Typography variant="h4">Try it yourself</Typography>
                <Typography sx={{ mt: 1.5, color: "rgba(255,255,255,0.75)" }}>
                  Pick a demo user, change where and how they sign in, and see the decision and its reasons.
                  Each user has a different history.
                </Typography>
                <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
                  <Button component={Link} href="/demo" variant="contained" color="secondary" size="large">Open the sign-in lab</Button>
                  <Button component={Link} href="/dashboard" size="large" sx={{ color: "white" }}>Watch the dashboard</Button>
                </Stack>
              </Box>
              <Stack spacing={1.5}>
                {[
                  ["alice", "20 earlier logins from Norway on a Mac: a regular"],
                  ["bob", "5 earlier logins from the UK on an iPhone: fairly new"],
                  ["charlie", "never logged in: the cold-start case"],
                ].map(([user, about]) => (
                  <Stack key={user} direction="row" spacing={2} sx={{ alignItems: "center", p: 1.5, borderRadius: 2, bgcolor: "rgba(255,255,255,0.06)" }}>
                    <Chip label={user} color="secondary" size="small" sx={{ minWidth: 72 }} />
                    <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.8)" }}>{about}</Typography>
                  </Stack>
                ))}
              </Stack>
            </Box>
          </CardContent>
        </Card>
      </Box>

      <Box component="footer" sx={{ borderTop: "1px solid", borderColor: "divider", py: 4 }}>
        <Typography variant="body2" color="text.secondary" className="mx-auto max-w-7xl px-4">
          Academic prototype from a final-year research project, not a production security product. Data: Wiefling, Jørgensen,
          Thunem and Lo Iacono (2022), Login Data Set for Risk-Based Authentication, CC BY 4.0.
        </Typography>
      </Box>
    </main>
  );
}
