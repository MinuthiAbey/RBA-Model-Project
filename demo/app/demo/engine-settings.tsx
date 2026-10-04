"use client";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import type { LabOptions } from "@/lib/types";

export const SCORER_NAMES: Record<string, string> = {
  rforest: "Random Forest", iforest: "Isolation Forest", freeman: "Freeman model", rules: "Fixed rules",
};

// Which model decides, and how many legitimate sign-ins it may challenge (operating points chosen on validation data).
export default function EngineSettings({ options, scorer, setScorer, budget, setBudget }: {
  options: LabOptions;
  scorer: string;
  setScorer: (scorer: string) => void;
  budget: string;
  setBudget: (budget: string) => void;
}) {
  const budgets = options.budgets.filter((b) => Number(b) >= 0.05);
  return (
    <Card>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" } }}>
          <Typography variant="h6" sx={{ flexShrink: 0 }}>Engine</Typography>
          <TextField select size="small" label="Model" value={scorer} onChange={(e) => setScorer(e.target.value)} sx={{ minWidth: 190 }}>
            {options.scorers.map((name) => <MenuItem key={name} value={name}>{SCORER_NAMES[name] ?? name}</MenuItem>)}
          </TextField>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>Challenge budget</Typography>
            <ToggleButtonGroup exclusive size="small" value={budget} onChange={(_, b) => b && setBudget(b)}>
              {budgets.map((b) => <ToggleButton key={b} value={b} sx={{ px: 1.5 }}>{Math.round(Number(b) * 100)}%</ToggleButton>)}
            </ToggleButtonGroup>
          </Stack>
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
          The share of normal sign-ins each model may challenge. A bigger budget catches more attacks but asks more real users for a code.
        </Typography>
      </CardContent>
    </Card>
  );
}
