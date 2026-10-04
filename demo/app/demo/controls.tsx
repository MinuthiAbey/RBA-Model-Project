"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import type { LabOptions, Profile, Simulation } from "@/lib/types";
import { flag, hourLabel } from "./labels";

function Label({ text, changed }: { text: string; changed: boolean }) {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 0.75 }}>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>{text}</Typography>
      {changed && <Chip label="changed" size="small" color="warning" variant="outlined" sx={{ height: 20 }} />}
    </Stack>
  );
}

export default function Controls({ options, usual, sim, setSim, failures, setFailures, password, setPassword }: {
  options: LabOptions;
  usual: Profile["usual"];
  sim: Simulation;
  setSim: (sim: Simulation) => void;
  failures: number;
  setFailures: (n: number) => void;
  password: string;
  setPassword: (password: string) => void;
}) {
  const location = options.locations.find((l) => l.country === sim.country) ?? options.locations[0];
  const differs = (key: keyof Simulation) => (usual ? sim[key] !== (key === "ip" ? "usual" : usual[key]) : false);

  function chooseCountry(country: string) {
    const next = options.locations.find((l) => l.country === country)!;
    const asn = usual && usual.country === country ? usual.asn : next.asns[0];
    setSim({ ...sim, country, asn, ip: usual && usual.country === country ? sim.ip : "new" });
  }

  return (
    <Stack spacing={2.5}>
      <Box>
        <Label text="Country" changed={differs("country")} />
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
          <Label text="Network" changed={differs("asn")} />
          <TextField select fullWidth size="small" value={sim.asn} onChange={(e) => setSim({ ...sim, asn: Number(e.target.value) })}>
            {location.asns.map((asn, i) => (
              <MenuItem key={asn} value={asn}>AS{asn}{usual?.asn === asn ? " · usual" : i === 0 ? " · main" : ""}</MenuItem>
            ))}
          </TextField>
        </Box>
        <Box>
          <Label text="IP address" changed={sim.ip === "new" && !!usual} />
          <ToggleButtonGroup exclusive fullWidth size="small" value={sim.ip}
                             onChange={(_, ip) => ip && setSim({ ...sim, ip })}>
            <ToggleButton value="usual" disabled={!usual}>Usual</ToggleButton>
            <ToggleButton value="new">New</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      <Box>
        <Label text="Device" changed={differs("device")} />
        <TextField select fullWidth size="small" value={sim.device} onChange={(e) => setSim({ ...sim, device: e.target.value })}>
          {options.devices.map((d) => (
            <MenuItem key={d.key} value={d.key}>{d.label}{usual?.device === d.key ? "  · usual" : ""}</MenuItem>
          ))}
        </TextField>
      </Box>

      <Box>
        <Label text={`Time of day · ${hourLabel(sim.hour)}`} changed={differs("hour")} />
        <Box sx={{ px: 1 }}>
          <Slider value={sim.hour} min={0} max={23} step={1} onChange={(_, hour) => setSim({ ...sim, hour: hour as number })}
                  marks={usual?.hour != null ? [{ value: usual.hour, label: "usual" }] : []}
                  valueLabelDisplay="auto" valueLabelFormat={hourLabel} />
        </Box>
      </Box>

      <Box className="grid grid-cols-2 gap-4">
        <Box>
          <Label text="Wrong passwords first" changed={failures > 0} />
          <ToggleButtonGroup exclusive fullWidth size="small" value={failures} onChange={(_, n) => n !== null && setFailures(n)}>
            {[0, 3, 5].map((n) => <ToggleButton key={n} value={n}>{n}</ToggleButton>)}
          </ToggleButtonGroup>
        </Box>
        <Box>
          <Label text="Password" changed={password !== "demo1234"} />
          <TextField fullWidth size="small" type="text" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Box>
      </Box>
    </Stack>
  );
}

export function ResetButton({ onClick }: { onClick: () => void }) {
  return <Button onClick={onClick} size="small">Reset to usual</Button>;
}
