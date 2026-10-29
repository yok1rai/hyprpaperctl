import { execute } from "../utils.js";
import { ParseErr } from "../errors.js";

export interface MonitorInfo {
    readonly id: number;
    readonly name: string;
    readonly width: number;
    readonly height: number;
}

export function isMonitorInfo(value: unknown): value is MonitorInfo {
    if (typeof value !== "object" || value === null) return false;
    const entry = value as Record<string, unknown>;
    return typeof entry.id === "number" && Number.isSafeInteger(entry.id) && entry.id >= 0 &&
        typeof entry.name === "string" && entry.name.length > 0 &&
        typeof entry.width === "number" && Number.isSafeInteger(entry.width) && entry.width > 0 &&
        typeof entry.height === "number" && Number.isSafeInteger(entry.height) && entry.height > 0;
}

export function parseMonitors(text: string): MonitorInfo[] {
    let value: unknown;
    try {
        value = JSON.parse(text);
    } catch (error) {
        throw new ParseErr("Invalid monitor JSON", String(error));
    }
    if (!Array.isArray(value) || !value.every(isMonitorInfo) ||
        new Set(value.map(item => item.name)).size !== value.length ||
        new Set(value.map(item => item.id)).size !== value.length) {
        throw new ParseErr("Invalid monitor data");
    }
    return value.map(({ id, name, width, height }) => ({ id, name, width, height }));
}

export async function getMonitors(): Promise<MonitorInfo[]> {
    return parseMonitors(await execute(["hyprctl", "-j", "monitors"]));
}
