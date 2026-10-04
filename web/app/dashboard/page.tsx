"use client";

import GppBadOutlinedIcon from "@mui/icons-material/GppBadOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import type { LoginRecord, OtpNotice, StreamMessage } from "@/lib/types";
import { FeedTable, KpiCard, OUTCOMES, RiskChart } from "./parts";

const SCORER_NAMES: Record<string, string> = {
  rforest: "Random Forest", iforest: "Isolation Forest", freeman: "Freeman (statistical)", rules: "Fixed rules",
};
const ALERT_SECONDS = 10;

export default function DashboardPage() {
  const [records, setRecords] = useState<LoginRecord[]>([]);
  const [otp, setOtp] = useState<OtpNotice | null>(null);
  const [info, setInfo] = useState<{ scorer: string; challenge_budget: number } | null>(null);
  const [live, setLive] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    fetch("/api/events").then((r) => r.json()).then((data) => {
      setRecords(data.records);
      setOtp(data.latestOtp);
      setInfo(data.info);
    });
    const source = new EventSource("/api/events/stream");
    source.onopen = () => setLive(true);
    source.onerror = () => setLive(false);
    source.onmessage = (event) => {
      const message = JSON.parse(event.data) as StreamMessage;
      if (message.type === "login") setRecords((current) => [message.record, ...current].slice(0, 2000));
      if (message.type === "otp") setOtp(message.notice);
    };
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      source.close();
      clearInterval(tick);
    };
  }, []);

  const count = (...outcomes: LoginRecord["outcome"][]) => records.filter((r) => outcomes.includes(r.outcome)).length;
  const lastBlock = records.find((r) => r.outcome === "block" || r.outcome === "otp_failed");
  const showAlert = lastBlock && now - new Date(lastBlock.time).getTime() < ALERT_SECONDS * 1000;

  return (
    <Box className="mx-auto max-w-7xl px-4 py-8">
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, mb: 3 }}>
        <Box>
          <Typography variant="h4">Security dashboard</Typography>
          <Typography color="text.secondary">Every sign-in to the demo, scored and decided in real time.</Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Chip label={live ? "Live" : "Connecting…"} color={live ? "success" : "default"} variant="outlined" />
          <Chip color="primary"
                label={info ? `${SCORER_NAMES[info.scorer] ?? info.scorer} · ${Math.round(info.challenge_budget * 100)}% challenge budget`
                            : "Risk engine offline"} />
        </Stack>
      </Stack>

      {showAlert && lastBlock && (
        <Alert severity="error" variant="filled" icon={<GppBadOutlinedIcon />} sx={{ mb: 3, fontSize: 17, alignItems: "center" }}
               action={lastBlock.score !== null ? <Typography sx={{ fontWeight: 700, pr: 1 }}>Risk {lastBlock.score}/100</Typography> : undefined}>
          {OUTCOMES[lastBlock.outcome].label}: sign-in for <b>{lastBlock.username}</b> from {lastBlock.ip} ({lastBlock.country ?? "unknown"})
        </Alert>
      )}

      <Box className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <KpiCard label="Allowed" value={count("allow")} tone="success" />
        <KpiCard label="One-time codes" value={count("otp")} tone="warning" />
        <KpiCard label="Blocked" value={count("block", "otp_failed")} tone="error" />
        <KpiCard label="Wrong passwords" value={count("wrong_password")} tone="default" />
        <Card className="col-span-2 lg:col-span-1" sx={{ border: "2px dashed", borderColor: "warning.main", bgcolor: "rgba(237,108,2,0.05)" }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>Latest one-time code · demo only</Typography>
            {otp ? (
              <>
                <Typography sx={{ fontFamily: "monospace", fontSize: 34, fontWeight: 700, letterSpacing: "0.2em", mt: 0.5 }}>{otp.code}</Typography>
                <Typography variant="body2" color="text.secondary">for {otp.username} · {new Date(otp.time).toLocaleTimeString()}</Typography>
              </>
            ) : (
              <Typography color="text.secondary" sx={{ mt: 1.5 }}>None issued yet</Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      <Box className="mb-6"><RiskChart records={records} /></Box>
      <FeedTable records={records} />
    </Box>
  );
}
