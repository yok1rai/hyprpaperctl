import fs from "node:fs/promises";
import type net from "node:net";
import MonitorManager from "./components/monitors.js";
import PaperMonitor from "./services/hyprpaper.js";
import { ApplicationErrs } from "./errors.js";
import { socketPath, run, createserver } from "./socket/server.js";

function logError(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  const extra =
    error instanceof ApplicationErrs && error.extra ? `: ${error.extra}` : "";
  console.error(`[${new Date().toISOString()}] ${message}${extra}`);
}

export async function startDaemon(targetDir: string, address = socketPath) {
  const monitorM = await MonitorManager.create(targetDir);
  const paperM = await PaperMonitor.create(monitorM);
  const server = await createserver();
  const clients = new Set<net.Socket>();
  let stopping: Promise<void> | undefined;

  const stop = (): Promise<void> => {
    stopping ??= (async () => {
      const closed = server.listening
        ? new Promise<void>((resolve, reject) => {
            server.close((error) => (error ? reject(error) : resolve()));
          })
        : Promise.resolve();
      for (const client of clients) client.destroy();
      await closed;
    })();
    return stopping;
  };

  const handleError = (error: unknown): void => {
    logError(error);
    if (error instanceof ApplicationErrs && error.crash) {
      process.exitCode = 1;
      void stop().catch(logError);
    }
  };

  server.on("connection", (client) => {
    clients.add(client);
    client.once("close", () => clients.delete(client));
  });
  await run(server, monitorM, paperM, handleError);

  try {
    await new Promise<void>((resolve, reject) => {
      const onError = (error: Error) => {
        server.off("listening", onListening);
        reject(error);
      };
      const onListening = () => {
        server.off("error", onError);
        resolve();
      };
      server.once("error", onError);
      server.once("listening", onListening);
      server.listen(address);
    });
    await fs.chmod(address, 0o600);
  } catch (error) {
    await stop();
    throw error;
  }

  console.log(`[${new Date().toISOString()}] Listening on ${address}`);
  return { server, monitorM, paperM, stop };
}

async function main(): Promise<void> {
  const targetDir = process.argv[2];
  if (!targetDir?.trim() || process.argv.length !== 3) {
    throw new Error("Usage: bun run start <wallpaper-directory>");
  }
  const daemon = await startDaemon(targetDir);
  const shutdown = () => {
    void daemon.stop().catch((error) => {
      logError(error);
      process.exitCode = 1;
    });
  };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
  daemon.server.once("close", () => {
    process.off("SIGINT", shutdown);
    process.off("SIGTERM", shutdown);
  });
}

if (import.meta.main) {
  void main().catch((error) => {
    logError(error);
    process.exitCode = 1;
  });
}
