import WallpaperManager from "./wallpaper.js";
import { getMonitors } from "../services/hyprctl.js";
import type { MonitorInfo } from "../services/hyprctl.js";
import { ComponentErr } from "../errors.js";

export interface Monitor extends MonitorInfo {
  readonly wallpapers: WallpaperManager;
}

export default class MonitorManager {
  private items: Monitor[] = [];

  private constructor(
    public readonly targetDir: string,
    private readonly loadMonitors: () => Promise<MonitorInfo[]>,
  ) {}

  static async create(
    targetDir: string,
    loadMonitors = getMonitors,
  ): Promise<MonitorManager> {
    const manager = new MonitorManager(targetDir, loadMonitors);
    await manager.refresh();
    return manager;
  }

  get monitors(): readonly Monitor[] {
    return this.items.map((item) => ({ ...item }));
  }

  get(name: string): Monitor {
    const monitor = this.items.find((item) => item.name === name);
    if (!monitor) throw new ComponentErr("Monitor not found", name);
    return { ...monitor };
  }

  async refresh(): Promise<void> {
    const monitors = await this.loadMonitors();
    const items = await Promise.all(
      monitors.map(async (monitor) => {
        const existing = this.items.find((item) => item.name === monitor.name);
        const wallpapers =
          existing?.wallpapers ??
          (await WallpaperManager.create(this.targetDir, monitor.name));
        return { ...monitor, wallpapers };
      }),
    );
    this.items = items;
  }
}
