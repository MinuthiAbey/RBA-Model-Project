"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import type { LabOptions, Profile, Simulation } from "@/lib/types";
import { flag, hourLabel } from "./labels";

export function FieldLabel({ text, changed }: { text: string; changed: boolean }) {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 0.75 }}>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>{text}</Typography>
      {changed && <Chip label="changed" size="small" color="warning" variant="outlined" sx={{ height: 20 }} />}
    </Stack>
  );
}

// The conditions a user's sign-in normally has; a brand-new user gets a plain default.
export function usualSimulation(profile: Profile | undefined, options: LabOptions): Simulation {
  const usual = profile?.usual;
  if (!usual) return { country: options.locations[0].country, asn: options.locations[0].asns[0], ip: "new", device: options.devices[0].key, hour: new Date().getHours() };
  return { country: usual.country, asn: usual.asn, ip: "usual", device: usual.device ?? options.devices[0].key, hour: usual.hour ?? new Date().getHours() };
}

// Where, how and when a sign-in happens. Fields that differ from the user's usual sign-in are marked.
export function ConditionsFields({ options, usual, sim, setSim }: {
  options: LabOptions;
  usual: Profile["usual"] | undefined;
  sim: Simulation;
  setSim: (sim: Simulation) => void;
}) {
  const location = options.locations.find((l) => l.country === sim.country) ?? options.locations[0];
  const differs = (key: keyof Simulation) => (usual ? sim[key] !== (key === "ip" ? "usual" : usual[key]) : false);

  function chooseCountry(country: string) {
    const next = options.locations.find((l) => l.country === country)!;
    const home = usual?.country === country;
    setSim({ ...sim, country, asn: home ? usual!.asn : next.asns[0], ip: home ? sim.ip : "new" });
  }

  return (
    <Stack spacing={2.5}>
      <Box>
        <FieldLabel text="Country" changed={differs("country")} />
        <TextField select fullWidth size="small" value={sim.country} onChange={(e) => chooseCountry(e.target.value)}>
          {options.locations.map((l) => (
            <MenuItem key={l.country} value={l.country}>
              {flag(l.country)}&nbsp;&nbsp;{l.name}{usual?.country === l.country ? "  · usual" : ""}
            </MenuItem>
          ))}
        </TextField>
      </Box>
      <Box className="grid grid-cols-2 gap-4">
        <Box>
          <FieldLabel text="Network" changed={differs("asn")} />
          <TextField select fullWidth size="small" value={sim.asn} onChange={(e) => setSim({ ...sim, asn: Number(e.target.value) })}>
            {location.asns.map((asn, i) => (
              <MenuItem key={asn} value={asn}>AS{asn}{usual?.asn === asn ? " · usual" : i === 0 ? " · main" : ""}</MenuItem>
            ))}
          </TextField>
        </Box>
        <Box>
          <FieldLabel text="IP address" changed={sim.ip === "new" && !!usual} />
          <ToggleButtonGroup exclusive fullWidth size="small" value={sim.ip} onChange={(_, ip) => ip && setSim({ ...sim, ip })}>
            <ToggleButton value="usual" disabled={!usual}>Usual</ToggleButton>
            <ToggleButton value="new">New</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>
      <Box>
        <FieldLabel text="Device" changed={differs("device")} />
        <TextField select fullWidth size="small" value={sim.device} onChange={(e) => setSim({ ...sim, device: e.target.value })}>
          {options.devices.map((d) => (
            <MenuItem key={d.key} value={d.key}>{d.label}{usual?.device === d.key ? "  · usual" : ""}</MenuItem>
          ))}
        </TextField>
      </Box>
      <Box>
        <FieldLabel text={`Time of day · ${hourLabel(sim.hour)}`} changed={differs("hour")} />
        <Box sx={{ px: 1 }}>
          <Slider value={sim.hour} min={0} max={23} step={1} onChange={(_, hour) => setSim({ ...sim, hour: hour as number })}
                  marks={usual?.hour != null ? [{ value: usual.hour, label: "usual" }] : []}
                  valueLabelDisplay="auto" valueLabelFormat={hourLabel} />
        </Box>
      </Box>
    </Stack>
  );
}

// Side panel for the sign-in and sign-up pages: sign in with chosen conditions, or with this browser's real ones.
export function ConditionsCard({ options, profile, username, sim, setSim, simulated, setSimulated }: {
  options: LabOptions;
  profile: Profile | undefined;
  username: string;
  sim: Simulation;
  setSim: (sim: Simulation) => void;
  simulated: boolean;
  setSimulated: (on: boolean) => void;
}) {
  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 1 }}>
          <Typography variant="h6">Conditions</Typography>
          <FormControlLabel control={<Switch checked={simulated} onChange={(e) => setSimulated(e.target.checked)} />}
                            label={simulated ? "Chosen" : "This browser"} />
        </Stack>
        {!simulated ? (
          <Typography color="text.secondary">Signing in from this browser and connection as they really are.</Typography>
        ) : (
          <>
            {profile?.usual ? (
              <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Typography variant="body2" color="text.secondary">Compared with {username}&apos;s usual sign-in</Typography>
                <Button size="small" onClick={() => setSim(usualSimulation(profile, options))}>Use usual</Button>
              </Stack>
            ) : (
              <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
                {username && profile ? `${username} has no sign-in history yet, so everything is new.` : "Choose where, how and when this sign-in happens."}
              </Alert>
            )}
            <ConditionsFields options={options} usual={profile?.usual} sim={sim} setSim={setSim} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
