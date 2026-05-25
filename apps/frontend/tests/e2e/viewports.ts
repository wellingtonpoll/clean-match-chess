// Feature 006 / T025 — central viewport matrix metadata.

export const VIEWPORT_NAMES = [
  'mobile-iphone-se',
  'mobile-iphone-11-pro-max',
  'desktop-1280',
  'desktop-1920',
] as const

export type ViewportName = (typeof VIEWPORT_NAMES)[number]

export const VIEWPORT_SIZES: Record<ViewportName, { width: number; height: number }> = {
  'mobile-iphone-se': { width: 375, height: 667 },
  'mobile-iphone-11-pro-max': { width: 414, height: 896 },
  'desktop-1280': { width: 1280, height: 800 },
  'desktop-1920': { width: 1920, height: 1080 },
}
