"use client";

import AccessTimeIcon from "@mui/icons-material/AccessTime";
import DevicesOutlinedIcon from "@mui/icons-material/DevicesOutlined";
import HistoryIcon from "@mui/icons-material/History";
import LanOutlinedIcon from "@mui/icons-material/LanOutlined";
import PlaceOutlinedIcon from "@mui/icons-material/PlaceOutlined";
import RouterOutlinedIcon from "@mui/icons-material/RouterOutlined";
import VerifiedUserOutlinedIcon from "@mui/icons-material/VerifiedUserOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { LabOptions, Profile } from "@/lib/types";
import { countryName, flag, hourLabel } from "./labels";

function Row({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", py: 0.75 }}>
      <Box sx={{ color: "primary.main", display: "flex" }}>{icon}</Box>
      <Typography variant="body2" color="text.secondary" sx={{ width: 96, flexShrink: 0 }}>{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>{value}</Typography>
    </Stack>
  );
}

// The user's "safe" profile: what a normal sign-in looks like for them, as the engine has learned it.
export default function ProfileCard({ profile, options }: { profile: Profile; options: LabOptions }) {
  const usual = profile.usual;
  if (!usual) {
    return (
      <Alert severity="info" variant="outlined">
        <b>No sign-in history yet.</b> Every country, network and device is new for this user. This is the cold-start case.
      </Alert>
    );
  }
  const device = options.devices.find((d) => d.key === usual.device)?.label ?? `${usual.browser} · ${usual.os}`;
  const seen = profile.seen_countries.map((c) => `${flag(c)} ${c}`).join("  ");

  return (
    <Box sx={{ p: 2, borderRadius: 2, bgcolor: "rgba(46,125,50,0.06)", border: "1px solid rgba(46,125,50,0.25)" }}>
      <Typography variant="overline" sx={{ color: "success.main" }}>Usual sign-in</Typography>
      <Row icon={<PlaceOutlinedIcon fontSize="small" />} label="Location" value={`${flag(usual.country)} ${countryName(options, usual.country)}`} />
      <Row icon={<LanOutlinedIcon fontSize="small" />} label="Network" value={`AS${usual.asn}`} />
      <Row icon={<RouterOutlinedIcon fontSize="small" />} label="IP address" value={usual.ip} />
      <Row icon={<DevicesOutlinedIcon fontSize="small" />} label="Device" value={device} />
      <Row icon={<AccessTimeIcon fontSize="small" />} label="Usual time" value={usual.hour === null ? "varies" : `around ${hourLabel(usual.hour)}`} />
      <Row icon={<HistoryIcon fontSize="small" />} label="History" value={`${profile.logins} sign-ins · seen from ${seen}`} />
      {profile.trusted.map((t) => (
        <Row key={`${t.country}-${t.asn}-${t.device}`} icon={<VerifiedUserOutlinedIcon fontSize="small" />} label="Remembered"
             value={`${flag(t.country)} ${t.country} · AS${t.asn} · ${options.devices.find((d) => d.key === t.device)?.label ?? "device"}`} />
      ))}
    </Box>
  );
}
