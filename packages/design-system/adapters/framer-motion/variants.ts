// Generated from tokens v1.0.0 - DO NOT EDIT.
export const easing = {
  standard: [0.22, 1.0, 0.36, 1.0] as const,
} as const;

export const duration = {
  fast: 0.2,  // seconds
  medium: 0.275,  // seconds
  slow: 0.35,  // seconds
} as const;

export const variants = {
  fadeIn: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: duration.medium, ease: easing.standard },
    },
  },
} as const;
