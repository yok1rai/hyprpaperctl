import { execFile } from "node:child_process";
import { ExecErr, ParseErr, OsErr } from "./errors.js";
import * as fs from "node:fs/promises";
import path from "node:path";

export type AnyDArray<T> = Array<T | AnyDArray<T>>;

export async function list(
    target: string,
    recursive = false,
): Promise<AnyDArray<string>> {
    try {
        const entries = await fs.readdir(target, { withFileTypes: true });
        entries.sort((a, b) => a.name.localeCompare(b.name));
        const items: AnyDArray<string> = [];
        for (const entry of entries) {
            if (recursive && entry.isDirectory()) {
                items.push([entry.name, await list(path.join(target, entry.name), true)]);
            } else {
                items.push(entry.name);
            }
        }
        return items;
    } catch (error) {
        if (error instanceof OsErr) throw error;
        throw new OsErr("Failed to list directory", `${target}: ${String(error)}`);
    }
}

export function execute(
    args: readonly string[],
    critic = false,
): Promise<string> {
    return new Promise((resolve, reject) => {
        const [command, ...commandArgs] = args;
        if (!command?.trim() || args.some(arg => arg.includes("\0"))) {
            reject(new ExecErr("Invalid command or arguments", command, critic));
            return;
        }
        try {
            execFile(command, commandArgs, { encoding: "utf8" }, (error, stdout, stderr) => {
                if (error) {
                    reject(new ExecErr(`Failed to execute ${command}`, stderr.trim() || error.message, critic));
                    return;
                }
                resolve(stdout);
            });
        } catch (error) {
            reject(new ExecErr(`Failed to execute ${command}`, String(error), critic));
        }
    });
}

export function sep(line: string): string[] {
    const words: string[] = [];
    let quote: "'" | '"' | null = null;
    let current = "";
    let started = false;

    for (let index = 0; index < line.length; index++) {
        const letter = line[index]!;
        if (letter === "\\" && quote !== "'") {
            const next = line[index + 1];
            if (next === undefined) throw new ParseErr("Escape sequence left open");
            if (quote === '"' && !['"', "\\", "$", "`", "\n"].includes(next)) {
                current += letter;
                started = true;
                continue;
            }
            index++;
            if (next !== "\n") {
                current += next;
                started = true;
            }
        } else if (quote !== null) {
            if (letter === quote) quote = null;
            else current += letter;
        } else if (letter === "'" || letter === '"') {
            quote = letter;
            started = true;
        } else if (/\s/.test(letter)) {
            if (started) {
                words.push(current);
                current = "";
                started = false;
            }
        } else {
            current += letter;
            started = true;
        }
    }

    if (quote !== null) throw new ParseErr("Quote left open");
    if (started) words.push(current);
    return words;
}
