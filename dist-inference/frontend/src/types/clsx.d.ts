declare module 'clsx' {
  interface Clsx {
    (...classes: (string | undefined | null | false | Record<string, boolean | undefined | null>)[]): string
  }
  const clsx: Clsx
  export = clsx
}
