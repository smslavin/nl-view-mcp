import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import type { WidgetSpec } from "./types";

const SERVER_URL = import.meta.env.VITE_MCP_SERVER_URL ?? "http://127.0.0.1:8010/mcp";

let clientPromise: Promise<Client> | null = null;

function getClient(): Promise<Client> {
  if (!clientPromise) {
    clientPromise = (async () => {
      const transport = new StreamableHTTPClientTransport(new URL(SERVER_URL));
      const client = new Client({ name: "nl-view-mcp-frontend", version: "0.0.1" });
      await client.connect(transport);
      return client;
    })();
  }
  return clientPromise;
}

/**
 * Calls the build_view tool, then reads the ui:// resource it returns.
 * Two MCP round trips (tools/call, then resources/read) to get from a plain
 * English instruction to a rendered widget spec.
 */
export async function buildView(instruction: string): Promise<WidgetSpec> {
  const client = await getClient();

  const toolResult = await client.callTool({
    name: "build_view",
    arguments: { instruction },
  });
  if (toolResult.isError) {
    throw new Error(`build_view failed: ${JSON.stringify(toolResult.content)}`);
  }
  const content = toolResult.content as Array<{ type: string; text?: string }>;
  const { uri } = JSON.parse(content[0]?.text ?? "{}") as { uri: string };

  const resource = await client.readResource({ uri });
  const first = resource.contents[0];
  const text = first && "text" in first ? first.text : undefined;
  if (typeof text !== "string") {
    throw new Error(`ui:// resource ${uri} returned no text content`);
  }
  return JSON.parse(text) as WidgetSpec;
}
