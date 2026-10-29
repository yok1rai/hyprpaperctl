import { execute } from "../utils.js";
import { ServiceErr } from "../errors.js";
import type MonitorManager from "../components/monitors.js";
import type { Wallpaper } from "../components/wallpaper.js";

export type PaperCommand = (args: readonly string[]) => Promise<string>;

export default class PaperMonitor {
    private pending: Promise<unknown> = Promise.resolve();

    private constructor(
        private readonly monitors: MonitorManager,
        private readonly run: PaperCommand,
    ) {}

    static async create(monitors: MonitorManager, run: PaperCommand = execute): Promise<PaperMonitor> {
        const paper = new PaperMonitor(monitors, run);
        await paper.listActive();
        return paper;
    }

    async listActive(): Promise<string> {
        return this.command("listactive");
    }

    apply(monitorName: string, wallpaperId: number): Promise<Wallpaper> {
        const operation = this.pending.then(async () => {
            const monitor = this.monitors.get(monitorName);
            const wallpaper = monitor.wallpapers.wallpapers.find(item => item.id === wallpaperId);
            if (!wallpaper) {
                throw new ServiceErr("Wallpaper not found", `${monitorName}: ${wallpaperId}`);
            }
            if (/[\0\r\n,]/.test(monitor.name) || /[\0\r\n,]/.test(wallpaper.path)) {
                throw new ServiceErr("Monitor name or wallpaper path contains an unsupported IPC delimiter");
            }
            const response = await this.command("wallpaper", `${monitor.name},${wallpaper.path}`);
            if (response.trim().toLowerCase() !== "ok") {
                throw new ServiceErr("Hyprpaper rejected wallpaper", response);
            }
            return monitor.wallpapers.select(wallpaper.path);
        });
        this.pending = operation.catch(() => {});
        return operation;
    }

    private async command(request: string, argument?: string): Promise<string> {
        const args = ["hyprctl", "hyprpaper", request];
        if (argument !== undefined) args.push(argument);
        try {
            return await this.run(args);
        } catch (error) {
            throw new ServiceErr("Hyprpaper command failed", String(error));
        }
    }
}
