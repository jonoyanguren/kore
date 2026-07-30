/** Kore mobile — shared config. */

export const API_BASE = (
  process.env.EXPO_PUBLIC_API_URL || 'https://kore.fly.dev'
).replace(/\/$/, '')

export const SECRET_KEY = 'kore_console_secret'
