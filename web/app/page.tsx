import { loadResults } from "@/lib/results";
import Landing from "./landing";

export const dynamic = "force-dynamic";

export default function HomePage() {
  return <Landing results={loadResults()} />;
}
