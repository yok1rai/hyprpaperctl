import { input, sep } from "./input";
import { ApplicationErrs } from "./errors";
import net from "node:net"; 
import { createInterface } from "node:readline";
import { stdin, stdout } from "node:process";
import { argv } from "node:process";

const rl = createInterface(stdin, stdout); 

function send(location: string, commands: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
        if (commands.length === 0) {
            reject(new ApplicationErrs("No argument given"));
            return;
        }

        const client = net.createConnection(location, () => {
            try {
                switch (commands[0]) {
                    case "list-monitors":
                        client.write("list-monitor\n");
                        break;

                    case "list-wallpapers":
                        if (commands.length < 2)
                            throw new ApplicationErrs(
                                "Usage: list-wallpapers <monitor>"
                            );

                        client.write(`list-wallpapers ${commands[1]}\n`);
                        break;

                    case "set-wallpapers":
                        if (commands.length < 3)
                            throw new ApplicationErrs(
                                "Usage: set-wallpapers <monitor> <wallpaper-id>"
                            );

                        client.write(
                            `set-wallpaper ${commands[1]} ${commands[2]}\n`
                        );
                        break;

                    case "change-directory":
                        if (commands.length < 3)
                            throw new ApplicationErrs(
                                "Usage: change-directory <monitor> <directory>"
                            );

                        client.write(
                            `change-directory ${commands[1]} ${commands[2]}\n`
                        );
                        break;

                    case "refresh-monitors":
                        client.write("refresh-monitors\n");
                        break;

                    case "refresh-wallpaper":
                        client.write("refresh-wallpapers\n");
                        break;

                    default:
                        throw new ApplicationErrs("Unknown command");
                }
            } catch (err) {
                client.destroy();
                reject(err);
            }
        });

        client.on("data", (data) => {
            resolve(data.toString());
            client.end();
        });

        client.on("error", (err) => {
            reject(err);
        });
    });
}

async function main() {
    let repl = false; 
    const args = argv.slice(2); 
    try {
        if (args.length === 0) {
            repl = true; 
        } 
        if (repl) {
            console.log("Welcome to the REPL mode!"); 
            const prompt = process.env.PROMPT ?? "> "; 
            while (true) {
                try {
                    const line = (await input(rl, prompt)).trim();
                    const commands = sep(line);
                    if (commands.length === 1 && commands[0]?.startsWith(".")) {
                        switch (commands[0]) {
                            case '.exit': 
                                console.log("goodbye!"); 
                                return; 
                            case '.help': 
                                console.log("will be implemented"); 
                                break; 
                            case '.version': 
                                console.log("v0.1.0"); 
                                break; 
                            default: 
                                console.error("invalid special command"); 
                                break; 
                        }
                        continue; 
                    }
                    const reply = await send("/tmp/wallpaperd.sock", commands); 
                    console.log(reply); 
                } catch (e) {
                    if (e instanceof ApplicationErrs)
                        console.log(e.message); 
                    else 
                        throw e; 
                }
            }
        } else {
            const reply = await send("/tmp/wallpaperd.sock", args); 
            console.log(reply); 
        }

    } catch (e){ 
        if (e instanceof ApplicationErrs) {
            console.log(e.message); 
        } else {
            throw e; 
        }
    } finally {
        rl.close(); 
    }
}

main().then(_ => {}).catch(e => console.error(e)); 
