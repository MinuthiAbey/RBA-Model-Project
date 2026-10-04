"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { BarChart } from "@mui/x-charts/BarChart";
import { LineChart } from "@mui/x-charts/LineChart";
import { useState } from "react";
import type { ModelResults, Row } from "@/lib/results";

// Same colour for each model everywhere, matching the evaluation figures.
const MODELS = [
  { key: "rforest", name: "Random Forest", kind: "Supervised machine learning", color: "#2a78d6" },
  { key: "iforest", name: "Isolation Forest", kind: "Anomaly detection", color: "#1baf7a" },
  { key: "freeman", name: "Freeman et al.", kind: "Statistical model", color: "#eb6834" },
  { key: "rules", name: "Fixed rules", kind: "Points per warning sign", color: "#eda100" },
];
const BUCKETS = ["0", "1-2", "3-5", "6-10", "11-20", "21+"];
const CONTEXTS: Record<string, string> = {
  victim_has_no_history: "Victim has no history", new_country: "New country",
  home_country_new_device: "Home country, new device", home_country_known_device: "Home country, known device",
};
const FIGURE_TITLES: Record<string, string> = {
  roc_curves: "ROC curves", security_usability_tradeoff: "Security vs usability", cold_start_curves: "Cold start",
  cold_start_false_challenges: "False challenges by history", attacker_types: "Attack types",
  confusion_matrices: "Decisions", latency: "Speed",
};

const num = (value: string | undefined) => Number(value ?? 0);
const pct = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`;
const find = (rows: Row[], match: Record<string, string>) => rows.find((r) => Object.entries(match).every(([k, v]) => r[k] === v));
const percentAxis = [{ min: 0, max: 1, valueFormatter: (v: number) => pct(v) }];

function ChartCard({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6">{title}</Typography>
        {note && <Typography variant="body2" color="text.secondary">{note}</Typography>}
        {children}
      </CardContent>
    </Card>
  );
}

function Overview({ results }: { results: ModelResults }) {
  const real = (scorer: string) => find(results.overall, { scorer, attack_set: "real_attack_ip" });
  const budgets = ["0.01", "0.05", "0.1", "0.2"];
  return (
    <Stack spacing={3}>
      <Box className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {MODELS.map((m) => {
          const row = real(m.key);
          const latency = num(find(results.latency, { scorer: m.key })?.p50_us);
          return (
            <Card key={m.key} sx={{ borderTop: `4px solid ${m.color}` }}>
              <CardContent>
                <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
                  <Typography variant="h6">{m.name}</Typography>
                  {m.key === "rforest" && <Chip label="Best" color="primary" size="small" />}
                </Stack>
                <Typography variant="body2" color="text.secondary">{m.kind}</Typography>
                <Typography variant="h3" sx={{ mt: 2 }}>{num(row?.roc_auc).toFixed(2)}</Typography>
                <Typography variant="body2" color="text.secondary">ROC AUC on real attacks</Typography>
                <Typography sx={{ mt: 2 }}><b>{pct(num(row?.attack_stop_rate))}</b> of attacks stopped</Typography>
                <Typography><b>{pct(num(row?.legit_challenge_rate), 1)}</b> of real users challenged</Typography>
                <Typography><b>{latency < 1000 ? `${latency.toFixed(0)} µs` : `${(latency / 1000).toFixed(1)} ms`}</b> per sign-in</Typography>
              </CardContent>
            </Card>
          );
        })}
      </Box>
      <ChartCard title="Attacks stopped at each challenge budget" note="Budget = share of real users each model may ask for a code.">
        <BarChart height={300} xAxis={[{ scaleType: "band", data: budgets.map((b) => pct(Number(b))) }]} yAxis={percentAxis}
                  series={MODELS.map((m) => ({
                    label: m.name, color: m.color, valueFormatter: (v: number | null) => pct(v ?? 0, 1),
                    data: budgets.map((b) => num(find(results.operatingPoints, { scorer: m.key, target_legit_challenge_rate: b })?.real_attack_ip_stop_rate)),
                  }))} />
      </ChartCard>
      <ChartCard title="How well each model separates attacks from normal sign-ins" note="ROC AUC: 1.0 is perfect, 0.5 is a coin flip.">
        <Table size="small" sx={{ mt: 1 }}>
          <TableHead>
            <TableRow><TableCell>Model</TableCell><TableCell align="right">Real attacks</TableCell>
              <TableCell align="right">Real attacks, correct password</TableCell><TableCell align="right">Simulated attacks</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {MODELS.map((m) => (
              <TableRow key={m.key}>
                <TableCell sx={{ fontWeight: 600 }}>{m.name}</TableCell>
                {["real_attack_ip", "real_attack_ip_password_correct", "simulated"].map((set) => (
                  <TableCell key={set} align="right">{num(find(results.overall, { scorer: m.key, attack_set: set })?.roc_auc).toFixed(3)}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ChartCard>
    </Stack>
  );
}

function bucketSeries(results: ModelResults, population: string) {
  return MODELS.map((m) => ({
    label: m.name, color: m.color, curve: "linear" as const, valueFormatter: (v: number | null) => pct(v ?? 0, 1),
    data: BUCKETS.map((b) => num(find(results.coldStart, { scorer: m.key, population, bucket: b })?.rate)),
  }));
}

function ColdStart({ results }: { results: ModelResults }) {
  const xAxis = [{ scaleType: "point" as const, data: BUCKETS, label: "Previous sign-ins by the user", height: 56, tickLabelInterval: () => true }];
  return (
    <Stack spacing={3}>
      <ChartCard title="Real attacks stopped, by sign-in history" note="5% challenge budget. Most real attacks hit accounts with no history. Freeman and fixed rules overlap.">
        <LineChart height={320} xAxis={xAxis} yAxis={percentAxis} series={bucketSeries(results, "real_attack_ip")} />
      </ChartCard>
      <ChartCard title="Real users challenged, by sign-in history" note="Where each model spends its challenge budget.">
        <LineChart height={320} xAxis={xAxis} yAxis={[{ min: 0, valueFormatter: (v: number) => pct(v) }]} series={bucketSeries(results, "legit")} />
      </ChartCard>
    </Stack>
  );
}

function groupedBars(rows: Row[], column: string, groups: string[], labels: string[]) {
  return {
    xAxis: [{ scaleType: "band" as const, data: labels }],
    series: MODELS.map((m) => ({
      label: m.name, color: m.color, valueFormatter: (v: number | null) => pct(v ?? 0, 1),
      data: groups.map((g) => num(find(rows, { scorer: m.key, [column]: g })?.attack_stop_rate)),
    })),
  };
}

function Attacks({ results }: { results: ModelResults }) {
  const contexts = Object.keys(CONTEXTS).filter((c) => results.attackContext.some((r) => r.context === c));
  return (
    <Stack spacing={3}>
      <ChartCard title="Real attacks stopped, by how closely they matched the victim" note="5% challenge budget.">
        <BarChart height={300} yAxis={percentAxis} {...groupedBars(results.attackContext, "context", contexts, contexts.map((c) => CONTEXTS[c]))} />
      </ChartCard>
      <Box className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Simulated attacks, by attacker type" note="Built from real sign-ins; never used for training.">
          <BarChart height={280} yAxis={percentAxis} {...groupedBars(results.attackerType, "attacker_type", ["naive", "vpn", "targeted"], ["Naive", "VPN", "Targeted"])} />
        </ChartCard>
        <ChartCard title="Confirmed account takeovers" note={`${results.labelledAto[0]?.n ?? 0} real cases, stopped at a 5% budget.`}>
          <Table size="small" sx={{ mt: 1 }}>
            <TableBody>
              {MODELS.map((m) => {
                const row = find(results.labelledAto, { scorer: m.key });
                return (
                  <TableRow key={m.key}>
                    <TableCell sx={{ fontWeight: 600 }}>{m.name}</TableCell>
                    <TableCell align="right">{pct(num(row?.ato_stop_rate), 1)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ChartCard>
      </Box>
    </Stack>
  );
}

function Data({ results }: { results: ModelResults }) {
  const total = (column: string) => results.splitStats.reduce((sum, r) => sum + num(r[column]), 0);
  const stats = [
    { label: "Users sampled", value: results.sampleStats.reduce((sum, r) => sum + num(r.sample_users), 0) },
    { label: "Sign-in attempts", value: total("logins") },
    { label: "Real attacker attempts", value: total("attack_ip") },
    { label: "Confirmed takeovers", value: total("ato") },
  ];
  const importance = [...results.importance].sort((a, b) => num(b.importance) - num(a.importance));
  return (
    <Stack spacing={3}>
      <Box className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}><CardContent>
            <Typography variant="h4">{s.value.toLocaleString()}</Typography>
            <Typography variant="body2" color="text.secondary">{s.label}</Typography>
          </CardContent></Card>
        ))}
      </Box>
      <ChartCard title="Train, validation and test periods" note="Split by time, so every model is tested on sign-ins from after it was trained.">
        <Table size="small" sx={{ mt: 1 }}>
          <TableHead>
            <TableRow><TableCell>Period</TableCell><TableCell>From</TableCell><TableCell>To</TableCell>
              <TableCell align="right">Normal sign-ins</TableCell><TableCell align="right">Failed passwords</TableCell>
              <TableCell align="right">Attacker attempts</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {results.splitStats.map((r) => (
              <TableRow key={r.period}>
                <TableCell sx={{ fontWeight: 600, textTransform: "capitalize" }}>{r.period}</TableCell>
                <TableCell>{r.first.slice(0, 10)}</TableCell><TableCell>{r.last.slice(0, 10)}</TableCell>
                <TableCell align="right">{num(r.legit_success).toLocaleString()}</TableCell>
                <TableCell align="right">{num(r.legit_failed).toLocaleString()}</TableCell>
                <TableCell align="right">{num(r.attack_ip).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ChartCard>
      <Box className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Sign-ins per user" note="The sample matches the full dataset.">
          <BarChart height={300} xAxis={[{ scaleType: "band", data: results.sampleStats.map((r) => r.logins_per_user) }]}
                    yAxis={[{ valueFormatter: (v: number) => `${v}%` }]}
                    series={[{ label: "Sample", color: "#2a78d6", data: results.sampleStats.map((r) => num(r.sample_pct)) },
                             { label: "Full dataset", color: "#94a3b8", data: results.sampleStats.map((r) => num(r.population_pct)) }]} />
        </ChartCard>
        <ChartCard title="What the Random Forest relies on" note="Feature importance.">
          <BarChart height={360} layout="horizontal" hideLegend
                    yAxis={[{ scaleType: "band", data: importance.map((r) => r.feature.replaceAll("_", " ")), width: 150 }]}
                    series={[{ data: importance.map((r) => num(r.importance)), color: "#2a78d6", label: "Importance", valueFormatter: (v: number | null) => (v ?? 0).toFixed(3) }]} />
        </ChartCard>
      </Box>
    </Stack>
  );
}

function Figures({ results }: { results: ModelResults }) {
  return (
    <Box className="grid gap-6 lg:grid-cols-2">
      {results.figures.map((file) => (
        <Card key={file}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>{FIGURE_TITLES[file.replace(".png", "")] ?? file}</Typography>
            <img src={`/api/figures/${file}`} alt={FIGURE_TITLES[file.replace(".png", "")] ?? file} style={{ width: "100%", height: "auto" }} />
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}

export default function ModelsView({ results }: { results: ModelResults }) {
  const [tab, setTab] = useState(0);
  const views = [Overview, ColdStart, Attacks, Data, Figures];
  const View = views[tab];
  return (
    <Box className="mx-auto max-w-7xl px-4 py-10">
      <Typography variant="h3">Models</Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }}>
        Four ways of scoring sign-in risk, tested on the same real data from a period none of them was trained on.
      </Typography>
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mt: 3, mb: 3, borderBottom: 1, borderColor: "divider" }}>
        {["Overview", "Cold start", "Attacks", "Data", "Figures"].map((label) => <Tab key={label} label={label} />)}
      </Tabs>
      <View results={results} />
    </Box>
  );
}
