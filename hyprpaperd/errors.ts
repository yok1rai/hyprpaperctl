export class ApplicationErrs extends Error {
    constructor(message?: string, public extra?: string, public crash?: boolean) {
        super(message);
        if (extra) 
            this.extra = extra; 
        if (crash)
            this.crash = crash; 
        else 
            this.crash = false; 
    }
}

export class OsErr extends ApplicationErrs {} 
export class ExecErr extends ApplicationErrs {}
export class ParseErr extends ApplicationErrs {}
export class ComponentErr extends ApplicationErrs {}
export class ServiceErr extends ApplicationErrs {} 
export class UserErr extends ApplicationErrs {}
