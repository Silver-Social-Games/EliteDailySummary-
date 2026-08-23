/** Offline-embedded brand logos (data URLs via esbuild png loader). */
import eliteClubLogo from "./assets/elite-club-logo.png";
import jackpotaLogo from "./assets/jackpota-logo.png";
import { esc } from "./format";

export type LogoKind = "elite" | "jackpota";

const SRC: Record<LogoKind, string> = {
  elite: eliteClubLogo,
  jackpota: jackpotaLogo,
};

export function logoImg(kind: LogoKind, heightPx: number, alt: string): string {
  const h = Math.max(16, Math.min(64, heightPx));
  return `<img class="logo-img logo-${kind}" src="${SRC[kind]}" alt="${esc(alt)}" height="${h}" loading="eager">`;
}
