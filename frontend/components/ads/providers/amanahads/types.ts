export type AdSize =
  | "LEADERBOARD"
  | "MEDIUM_RECTANGLE"
  | "MOBILE_BANNER"
  | "LARGE_RECTANGLE"
  | "HALF_PAGE";

export type AdType = "BANNER" | "VIDEO" | "INTERSTITIAL" | "REWARDED";

export const amanahAdDimensions: Record<AdSize, { width: number; height: number }> = {
  LEADERBOARD: { width: 728, height: 90 },
  MEDIUM_RECTANGLE: { width: 300, height: 250 },
  MOBILE_BANNER: { width: 320, height: 50 },
  LARGE_RECTANGLE: { width: 336, height: 280 },
  HALF_PAGE: { width: 300, height: 600 },
};
