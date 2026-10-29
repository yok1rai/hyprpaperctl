import fs from "node:fs/promises";
import net from "node:net";
import { sep } from "../utils";
import { ParseErr, UserErr } from "../errors";
import MonitorManager from "../components/monitors";
import PaperMonitor from "../services/hyprpaper";

export const socketPath = "/tmp/hyprpaperd.sock"; 

export async function createserver(): Promise<net.Server> {
    if (await fs.exists(socketPath))
        await fs.unlink(socketPath)
    return net.createServer(_ => {
        console.log(`[${new Date()}] Client Connected`); 
    }); 
}

export type ErrorHandler = (error: unknown) => void;

export async function run(
    server: net.Server,
    monitorM: MonitorManager,
    paperM: PaperMonitor,
    onError: ErrorHandler,
): Promise<void> {
    server.on("error", onError);
    server.on("connection", socket => {
        socket.on("data", async data => {
            try {
                let line: string[];
                try {
                    line = sep(data.toString().trim());
                } catch (error) {
                    if (error instanceof ParseErr) throw new UserErr(error.message);
                    throw error;
                }
                if (line.length === 0)
                    throw new UserErr("No command");
                switch (line[0]) {
                    case "list-monitor": {
                        const monitors = monitorM.monitors; 
                        if (monitors.length === 0)
                            throw new UserErr("There are no monitors");
                        monitors.forEach(monitor => {
                            const currentW = monitorM.get(monitor.name).wallpapers.current
                            console.log(`ID: ${monitor.id}`); 
                            console.log(`NAME: ${monitor.name}`); 
                            console.log(`WIDTH/HEIGHT: ${monitor.width}px/${monitor.height}px`); 
                            console.log(`Current Wallpaper: ${currentW ? currentW : 'No Wallpaper'}`);
                            console.log(); 
                        })
                        break; 
                    }
                    case 'list-wallpapers': {
                        const monitors = monitorM.monitors; 
                        const wallpapers = monitorM.monitors[0]?.wallpapers.wallpapers ?? []; 

                        if (wallpapers.length === 0)
                            throw new UserErr("There are no wallpapers");
                        wallpapers.forEach(wallpaper => {
                            const InMonitor = monitors.filter(
                                monitor => monitor.wallpapers.current?.path === wallpaper.path)
                                    .map(monitor => monitor.name); 

                            console.log(`ID: ${wallpaper.id}`);
                            console.log(`NAME: ${wallpaper.name}`); 
                            console.log(`PATH: ${wallpaper.path}`);
                            console.log(`Current: ${InMonitor ? InMonitor : 'None'}`)
                        })
                        break;
                    }
                    case 'set-wallpaper': {
                        const monitorName = line[1]; 
                        const idText = line[2]; 

                        if (
                            line.length !== 3 || 
                            !monitorName ||
                            !idText || 
                            !/^\d+$/.test(idText)
                        )
                            throw new UserErr("Usage: set-wallpaper <monitor> <wallpaper-id>")
                        const id = Number(idText); 
                        if (!Number.isSafeInteger(id))
                            throw new UserErr("Invalid Wallpaper ID"); 
                        const wallpaper = await paperM.apply(monitorName, id); 
                        console.log(`[${new Date()}] ${wallpaper.name} applied to ${monitorName}`); 
                        break; 
                    }
                    case 'refresh-monitors': {
                        await monitorM.refresh(); 
                        console.log(`[${new Date()}] Monitors refreshed`); 
                        break; 
                    }
                    case 'refresh-wallpapers': {
                        for (const monitor of monitorM.monitors)
                            await monitor.wallpapers.refresh();
                        console.log(`[${new Date()}]Wallpapers Refreshed`)
                        break;
                    }
                    default: 
                        throw new UserErr(`Unknown command`); 
                }
            } catch (error) {
                if (error instanceof UserErr) {
                    console.error(`[${new Date()}] ${error.message}`);
                    if (!socket.destroyed && socket.writable) {
                        socket.write(`ERROR: ${error.message}\n`);
                    }
                } else {
                    onError(error);
                }
            }
        });
        socket.on("error", onError);
    });
}

