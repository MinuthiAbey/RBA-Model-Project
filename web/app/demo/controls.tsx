"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import type { LabOptions, Profile, Simulation } from "@/lib/types";
import { ConditionsFields, FieldLabel } from "../conditions";

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
  return (
    <Stack spacing={2.5}>
      <ConditionsFields options={options} usual={usual} sim={sim} setSim={setSim} />
      <Box className="grid grid-cols-2 gap-4">
        <Box>
          <FieldLabel text="Wrong passwords first" changed={failures > 0} />
          <ToggleButtonGroup exclusive fullWidth size="small" value={failures} onChange={(_, n) => n !== null && setFailures(n)}>
            {[0, 3, 5].map((n) => <ToggleButton key={n} value={n}>{n}</ToggleButton>)}
          </ToggleButtonGroup>
        </Box>
        <Box>
          <FieldLabel text="Password" changed={password !== "demo1234"} />
          <TextField fullWidth size="small" type="text" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Box>
      </Box>
    </Stack>
  );
}

export function ResetButton({ onClick }: { onClick: () => void }) {
  return <Button onClick={onClick} size="small">Reset to usual</Button>;
}
