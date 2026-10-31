export class ApplicationErrs extends Error {
  constructor(
    message?: string,
    public extra?: string,
    public crash?: boolean,
  ) {
    super(message);
    if (extra) this.extra = extra;
    if (crash) this.crash = crash;
    else this.crash = false;
  }
}

export class ParseErr extends ApplicationErrs {}
