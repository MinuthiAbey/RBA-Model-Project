import { readFile } from "node:fs/promises";
import path from "node:path";
import { FIGURES } from "@/lib/results";

// Serves the evaluation figures, which live outside the code folder.
export async function GET(_: Request, { params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  if (!/^[a-z_]+\.png$/.test(name)) return new Response("Not found", { status: 404 });
  try {
    const image = await readFile(path.join(FIGURES, name));
    return new Response(image, { headers: { "Content-Type": "image/png", "Cache-Control": "no-cache" } });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
