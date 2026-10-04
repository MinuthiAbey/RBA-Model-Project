"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { BarChart } from "@mui/x-charts/BarChart";
import { useState } from "react";
import type { LoginRecord } from "@/lib/types";
import { theme } from "../theme";

type Tone = "success" | "warning" | "error" | "default";

// Every outcome has a text label; colour only reinforces it.
export const OUTCOMES: Record<LoginRecord["outcome"], { label: string; tone: Tone; filled: boolean }> = {
  allow: { label: "Allowed", tone: "success", filled: true },
  otp: { label: "One-time code", tone: "warning", filled: true },
  block: { label: "Blocked", tone: "error", filled: true },
  wrong_password: { label: "Wrong password", tone: "default", filled: false },
  otp_passed: { label: "Code passed", tone: "success", filled: false },
  otp_failed: { label: "Code failed · blocked", tone: "error", filled: true },
  signed_up: { label: "New account", tone: "success", filled: false },
};

const toneColour = (tone: Tone) => (tone === "default" ? theme.palette.text.secondary : theme.palette[tone].main);

export function DecisionChip({ outcome }: { outcome: LoginRecord["outcome"] }) {
  const { label, tone, filled } = OUTCOMES[outcome];
  return <Chip label={label} color={tone} size="small" variant={filled ? "filled" : "outlined"} />;
}

export function KpiCard({ label, value, tone }: { label: string; value: number; tone: Tone }) {
  return (
    <Card sx={{ borderTop: `4px solid ${toneColour(tone)}` }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{label}</Typography>
        <Typography variant="h3" sx={{ mt: 1, fontVariantNumeric: "tabular-nums" }}>{value}</Typography>
      </CardContent>
    </Card>
  );
}

export function RiskChart({ records }: { records: LoginRecord[] }) {
  const scored = records
    .filter((r) => r.score !== null && (r.outcome === "allow" || r.outcome === "otp" || r.outcome === "block"))
    .slice(0, 50)
    .reverse();
  const positions = scored.map((_, i) => i); // one band per sign-in, even when two happen in the same second

  return (
    <Card>
      <CardContent>
        <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", gap: 1 }}>
          <Box>
            <Typography variant="h6">Risk score of recent sign-ins</Typography>
            <Typography variant="body2" color="text.secondary">Last {scored.length} scored sign-ins, oldest on the left</Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            {(["allow", "otp", "block"] as const).map((o) => <DecisionChip key={o} outcome={o} />)}
          </Stack>
        </Stack>
        {scored.length === 0 ? (
          <Typography color="text.secondary" sx={{ py: 10, textAlign: "center" }}>No scored sign-ins yet.</Typography>
        ) : (
          <BarChart height={260} hideLegend skipAnimation borderRadius={4}
                    xAxis={[{
                      scaleType: "band", data: positions, tickLabelInterval: () => false, disableTicks: true,
                      colorMap: { type: "ordinal", values: positions, colors: scored.map((r) => toneColour(OUTCOMES[r.outcome].tone)) },
                      valueFormatter: (i: number) => `${scored[i].username} · ${new Date(scored[i].time).toLocaleTimeString()} · ${OUTCOMES[scored[i].outcome].label}`,
                    }]}
                    yAxis={[{ min: 0, max: 100 }]}
                    series={[{ data: scored.map((r) => r.score), label: "Risk", valueFormatter: (v: number | null) => `${v}/100` }]} />
        )}
      </CardContent>
    </Card>
  );
}

function RiskCell({ score, outcome }: { score: number | null; outcome: LoginRecord["outcome"] }) {
  if (score === null) return <Typography color="text.disabled">—</Typography>;
  const tone = OUTCOMES[outcome].tone;
  return (
    <Box sx={{ minWidth: 90 }}>
      <Typography sx={{ fontWeight: 700 }}>{score}</Typography>
      <LinearProgress variant="determinate" value={score} color={tone === "default" ? "inherit" : tone}
                      sx={{ height: 5, borderRadius: 3, mt: 0.5 }} />
    </Box>
  );
}

export function FeedTable({ records }: { records: LoginRecord[] }) {
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(10);
  const shown = records.slice(page * perPage, page * perPage + perPage);

  return (
    <Card>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              {["Time", "User", "From", "Device", "History", "Risk", "Decision", "Why"].map((h) => <TableCell key={h}>{h}</TableCell>)}
            </TableRow>
          </TableHead>
          <TableBody>
            {records.length === 0 && (
              <TableRow><TableCell colSpan={8} align="center" sx={{ py: 6, color: "text.secondary" }}>Waiting for sign-ins…</TableCell></TableRow>
            )}
            {shown.map((r) => {
              const [device, ...details] = r.device.split(" · ");
              return (
                <TableRow key={r.id} hover sx={{ verticalAlign: "top" }}>
                  <TableCell sx={{ whiteSpace: "nowrap", color: "text.secondary" }}>{new Date(r.time).toLocaleTimeString()}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{r.username || "—"}</TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {r.ip}
                    <Chip label={r.country ?? "??"} size="small" variant="outlined" sx={{ ml: 1, height: 20 }} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600, textTransform: "capitalize" }}>{device}</Typography>
                    <Typography variant="caption" color="text.secondary">{details.join(" · ")}</Typography>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{r.priorLogins} {r.priorLogins === 1 ? "login" : "logins"}</TableCell>
                  <TableCell><RiskCell score={r.score} outcome={r.outcome} /></TableCell>
                  <TableCell><DecisionChip outcome={r.outcome} /></TableCell>
                  <TableCell sx={{ color: "text.secondary", maxWidth: 380 }}>
                    {r.explanation.replace(/^Risk \d+\/100 \(\w+\):? ?/, "") || "nothing unusual"}
                    {r.scoringMs !== null && <Typography variant="caption" sx={{ display: "block", color: "text.disabled" }}>scored in {r.scoringMs} ms</Typography>}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination component="div" count={records.length} page={Math.min(page, Math.max(0, Math.ceil(records.length / perPage) - 1))}
                       onPageChange={(_, next) => setPage(next)} rowsPerPage={perPage} rowsPerPageOptions={[10, 25, 50]}
                       onRowsPerPageChange={(e) => { setPerPage(Number(e.target.value)); setPage(0); }} />
    </Card>
  );
}
