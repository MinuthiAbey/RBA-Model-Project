import { store } from "@/lib/store";
import type { StreamMessage } from "@/lib/types";

export const dynamic = "force-dynamic";

// Server-Sent Events: pushes each decision to open dashboards as it happens.
export async function GET() {
  const encoder = new TextEncoder();
  let cleanup = () => {};

  const stream = new ReadableStream({
    start(controller) {
      const send = (message: StreamMessage) => controller.enqueue(encoder.encode(`data: ${JSON.stringify(message)}\n\n`));
      const keepAlive = setInterval(() => controller.enqueue(encoder.encode(": ping\n\n")), 15_000);
      controller.enqueue(encoder.encode(": connected\n\n")); // first bytes, so the browser marks the stream open
      store.listeners.add(send);
      cleanup = () => {
        clearInterval(keepAlive);
        store.listeners.delete(send);
      };
    },
    cancel() {
      cleanup();
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive" },
  });
}
