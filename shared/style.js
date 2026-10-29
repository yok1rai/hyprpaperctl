export function termLink(text, url) {
    return `\x1b]8;;${url}\x1b\\${text}\x1b]8;;\x1b\\`;
}
