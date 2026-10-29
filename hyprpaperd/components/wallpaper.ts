import fs from "node:fs/promises";
import path from "node:path";
import { ComponentErr } from "../errors.js";

export const extensions = ["jpg", "jpeg", "webp", "png", "bmp"] as const;
export type WallpaperExtension = (typeof extensions)[number];

export interface Wallpaper {
    readonly id: number;
    readonly monitorName: string;
    readonly path: string;
    readonly name: string;
    readonly extension: WallpaperExtension;
    readonly current: boolean;
}

function isExtension(value: string): value is WallpaperExtension {
    return extensions.some(extension => extension === value);
}

export function isWallpaper(value: unknown): value is Wallpaper {
    if (typeof value !== "object" || value === null) return false;
    const entry = value as Record<string, unknown>;
    return typeof entry.id === "number" && Number.isSafeInteger(entry.id) && entry.id >= 0 &&
        typeof entry.monitorName === "string" && entry.monitorName.length > 0 &&
        typeof entry.path === "string" &&
        typeof entry.name === "string" &&
        typeof entry.current === "boolean" &&
        typeof entry.extension === "string" && isExtension(entry.extension);
}

export default class WallpaperManager {
    private items: Wallpaper[] = [];

    private constructor(
        private directory: string,
        public readonly monitorName: string,
    ) {}

    get targetDir(): string {
        return this.directory;
    }

    static async create(targetDir: string, monitorName: string): Promise<WallpaperManager> {
        if (!monitorName.trim()) throw new ComponentErr("Monitor name is required");
        const manager = new WallpaperManager(path.resolve(targetDir), monitorName);
        await manager.refresh();
        return manager;
    }

    get wallpapers(): readonly Wallpaper[] {
        return this.items.map(item => ({ ...item }));
    }

    get current(): Wallpaper | null {
        const current = this.items.find(item => item.current);
        return current ? { ...current } : null;
    }

    get lastWallpaper(): Wallpaper | null {
        const last = this.items.at(-1);
        return last ? { ...last } : null;
    }

    async refresh(): Promise<void> {
        this.items = await this.scan(this.directory);
    }

    async changeDirectory(targetDir: string): Promise<void> {
        const directory = path.resolve(targetDir);
        const items = await this.scan(directory);
        this.directory = directory;
        this.items = items;
    }

    private async scan(targetDir: string): Promise<Wallpaper[]> {
        try {
            const stat = await fs.stat(targetDir);
            if (!stat.isDirectory()) {
                throw new ComponentErr("Target is not a directory", targetDir, true);
            }
            const entries = await fs.readdir(targetDir, { withFileTypes: true });
            const selectedPath = this.current?.path;
            const items: Wallpaper[] = [];
            let id = 0;
            entries.sort((a, b) => a.name.localeCompare(b.name));
            for (const entry of entries) {
                const extension = path.extname(entry.name).slice(1).toLowerCase();
                if (!entry.isFile() || !isExtension(extension)) continue;
                const fullPath = path.join(targetDir, entry.name);
                items.push({
                    id: id++,
                    monitorName: this.monitorName,
                    path: fullPath,
                    name: entry.name,
                    extension,
                    current: fullPath === selectedPath,
                });
            }
            return items;
        } catch (error) {
            if (error instanceof ComponentErr) throw error;
            throw new ComponentErr("Failed to read wallpaper directory", String(error), true);
        }
    }

    select(wallpaperPath: string): Wallpaper {
        const resolved = path.resolve(wallpaperPath);
        const selected = this.items.find(item => item.path === resolved);
        if (!selected) {
            throw new ComponentErr("Wallpaper is not in the loaded directory", resolved);
        }
        if (selected.current) return { ...selected };
        this.items = this.items.map(item => ({ ...item, current: item.path === resolved }));
        return { ...selected, current: true };
    }
}
