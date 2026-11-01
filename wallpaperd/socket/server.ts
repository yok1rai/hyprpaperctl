import type AutoContinue from "../services/auto-continue.js";
import net from "node:net";
import { sep } from "../utils";
import { ParseErr, UserErr } from "../errors";
import MonitorManager from "../components/monitors";
import PaperMonitor from "../services/hyprpaper";

export const socketPath = "/tmp/wallpaperd.sock";

export async function createserver(): Promise<net.Server> {
  return net.createServer(() => {
    console.log(`[${new Date()}] Client Connected`);
  });
}

export type ErrorHandler = (error: unknown) => void;

export async function run(
  server: net.Server,
  monitorM: MonitorManager,
  paperM: PaperMonitor,
  onError: ErrorHandler,
  autoContinue: AutoContinue,
): Promise<void> {
  server.on("error", onError);

  server.on("connection", (socket) => {
    socket.on("data", async (data) => {
      try {
        let line: string[];

        try {
          line = sep(data.toString().trim());
        } catch (error) {
          if (error instanceof ParseErr) {
            throw new UserErr(error.message);
          }

          throw error;
        }

        if (line.length === 0) {
          throw new UserErr("No command");
        }

        switch (line[0]) {
          case "auto-continue": {
            if (line.length > 2 || (line[1] !== undefined && line[1] !== "off" && !/^\d+$/.test(line[1]))) {
              throw new UserErr("Usage: auto-continue [<seconds>|off]");
            }
            if (line[1] !== undefined) {
              autoContinue.configure(line[1] === "off" ? null : Number(line[1]));
            }
            socket.end(`OK: Auto-continue ${autoContinue.status}\n`);
            break;
          }

          case "list-monitor": {
            const monitors = monitorM.monitors;

            if (monitors.length === 0) {
              throw new UserErr("There are no monitors");
            }

            const response = monitors
              .map((monitor) => {
                const current = monitorM
                  .get(monitor.name)
                  .wallpapers.current;

                return [
                  `ID: ${monitor.id}`,
                  `NAME: ${monitor.name}`,
                  `WIDTH/HEIGHT: ${monitor.width}px/${monitor.height}px`,
                  `Current Wallpaper: ${current?.name ?? "No Wallpaper"}`,
                ].join("\n");
              })
              .join("\n\n");

            socket.end(`${response}\n`);
            break;
          }

          case "list-wallpapers": {
            const monitorName = line[1];

            if (line.length !== 2 || !monitorName) {
              throw new UserErr(
                "Usage: list-wallpapers <monitor>",
              );
            }

            const monitor = monitorM.get(monitorName);
            const wallpapers = monitor.wallpapers.wallpapers;

            if (wallpapers.length === 0) {
              throw new UserErr(
                `There are no wallpapers for ${monitorName}`,
              );
            }

            const response = wallpapers
              .map((wallpaper) =>
                [
                  `ID: ${wallpaper.id}`,
                  `NAME: ${wallpaper.name}`,
                  `PATH: ${wallpaper.path}`,
                  `Current: ${wallpaper.current ? "Yes" : "No"}`,
                ].join("\n"),
              )
              .join("\n\n");

            socket.end(`${response}\n`);
            break;
          }

          case "set-wallpaper": {
            const monitorName = line[1];
            const idText = line[2];

            if (
              line.length !== 3 ||
              !monitorName ||
              !idText ||
              !/^\d+$/.test(idText)
            ) {
              throw new UserErr(
                "Usage: set-wallpaper <monitor> <wallpaper-id>",
              );
            }

            const id = Number(idText);

            if (!Number.isSafeInteger(id)) {
              throw new UserErr("Invalid Wallpaper ID");
            }

            const wallpaper = await paperM.apply(
              monitorName,
              id,
            );

            console.log(
              `[${new Date()}] ${wallpaper.name} applied to ${monitorName}`,
            );

            socket.end(
              `OK: ${wallpaper.name} applied to ${monitorName}\n`,
            );

            break;
          }

          case "change-directory": {
            const monitorName = line[1];
            const targetDir = line[2];

            if (
              line.length !== 3 ||
              !monitorName ||
              !targetDir?.trim()
            ) {
              throw new UserErr(
                "Usage: change-directory <monitor> <directory>",
              );
            }

            const monitor = monitorM.get(monitorName);

            await monitor.wallpapers.changeDirectory(targetDir);

            console.log(
              `[${new Date()}] ${monitorName} directory changed to ${monitor.wallpapers.targetDir}`,
            );

            socket.end(
              `OK: ${monitorName} wallpaper directory changed to ${monitor.wallpapers.targetDir}\n`,
            );

            break;
          }

          case "refresh-monitors": {
            await monitorM.refresh();

            console.log(`[${new Date()}] Monitors refreshed`);

            socket.end("OK: Monitors refreshed\n");
            break;
          }

          case "refresh-wallpapers": {
            for (const monitor of monitorM.monitors) {
              await monitor.wallpapers.refresh();
            }

            console.log(`[${new Date()}] Wallpapers refreshed`);

            socket.end("OK: Wallpapers refreshed\n");
            break;
          }

          default:
            throw new UserErr("Unknown command");
        }
      } catch (error) {
        if (error instanceof UserErr) {
          console.error(
            `[${new Date()}] ${error.message}`,
          );

          if (!socket.destroyed && socket.writable) {
            socket.end(`ERROR: ${error.message}\n`);
          }

          return;
        }

        onError(error);

        if (!socket.destroyed && socket.writable) {
          socket.end("ERROR: Internal server error\n");
        }
      }
    });

    socket.on("error", onError);
  });
}
