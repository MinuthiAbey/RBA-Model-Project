import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import { loadModelResults } from "@/lib/results";
import ModelsView from "./models-view";

export const dynamic = "force-dynamic";

export default function ModelsPage() {
  const results = loadModelResults();
  if (!results) {
    return <Box className="mx-auto max-w-3xl px-4 py-16"><Alert severity="info">No model results yet.</Alert></Box>;
  }
  return <ModelsView results={results} />;
}
