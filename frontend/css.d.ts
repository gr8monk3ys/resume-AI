// TypeScript 6 (TS2882) requires a module declaration for side-effect CSS
// imports. This file must stay a non-module (no import/export) so the
// wildcard declaration registers globally.
declare module '*.css'
