import type MonitorManager from "../components/monitors.js";
import type PaperMonitor from "./hyprpaper.js";
import { UserErr } from "../errors.js";

export default class AutoContinue {
  private timer: ReturnType<typeof setTimeout> | undefined;
  private pending: Promise<void> = Promise.resolve();
  private running = false;
  private enabled = false;
  private stopped = false;
  private interval = 300;

  constructor(
    private readonly monitors: MonitorManager,
    private readonly paper: PaperMonitor,
    private readonly onError: (error: unknown) => void,
  ) {}

  get status(): string {
    return this.enabled ? `on (${this.interval} seconds)` : "off";
  }

  configure(seconds: number | null): void {
    if (seconds !== null && (!Number.isSafeInteger(seconds) || seconds < 1 || seconds > 2147483)) {
      throw new UserErr("Interval must be an integer between 1 and 2147483 seconds");
    }
    if (this.stopped) throw new UserErr("Daemon is stopping");
    clearTimeout(this.timer);
    this.enabled = seconds !== null;
    if (seconds !== null) this.interval = seconds;
    this.schedule();
  }

  async stop(): Promise<void> {
    this.stopped = true;
    this.enabled = false;
    clearTimeout(this.timer);
    await this.pending;
  }

  private schedule(): void {
    if (!this.enabled || this.stopped || this.running) return;
    this.timer = setTimeout(() => {
      this.running = true;
      this.pending = this.advance().finally(() => {
        this.running = false;
        this.schedule();
      });
    }, this.interval * 1000);
  }

  private async advance(): Promise<void> {
    for (const monitor of this.monitors.monitors) {
      if (!this.enabled || this.stopped) break;
      const wallpapers = monitor.wallpapers.wallpapers;
      const current = wallpapers.findIndex((item) => item.current);
      const next = wallpapers[(current + 1) % wallpapers.length];
      if (!next || (wallpapers.length === 1 && next.current)) continue;
      try {
        await this.paper.apply(monitor.name, next.id);
      } catch (error) {
        this.onError(error);
      }
    }
  }
}
