import { Interface } from "node:readline";
import { ParseErr } from "./errors";

export async function input(rl: Interface, prompt?: string): Promise<string> {
  return new Promise((res) => {
    rl.question(prompt !== undefined ? prompt : "", (answ) => res(answ));
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
