/** Section registry — drives the sidebar, routing and the topbar crumb.
 *
 * No view may import this file: every view is imported here, so a reverse
 * import would be a cycle. `sidebar.ts` / `topbar.ts` / `render.ts` read
 * `GROUP_ORDER`, `VIEWS`, `NAV_ORDER` and `VIEW_FN` from here instead.
 */
import type { ViewDef } from "./types";
import { day } from "./payload";
import { viewDashboard } from "./views/dashboard";
import { viewTeamGoals } from "./views/team";
import { viewHome } from "./views/home";
import { viewGoals } from "./views/goals";
import { viewTop10 } from "./views/top10";
import { viewTop20 } from "./views/top20";
import { viewPendingRd } from "./views/pendingRd";
import { viewFirstRd } from "./views/firstRd";
import { viewTickets } from "./views/tickets";
import { viewLocks } from "./views/locks";
import { viewBirthdays } from "./views/birthdays";

export const GROUP_ORDER = ["Command", "Today", "Performance", "Risk", "Operations", "Care"];

export const VIEWS: Record<string, ViewDef> = {
  dashboard: { label: "Manager Dashboard", short: "Dashboard", icon: "gauge",
               group: "Command", managerOnly: true, gated: true,
               sub: "Cross-AM roll-up — manager only" },
  team:      { label: "Team Goals", icon: "target", group: "Command",
               managerOnly: true, gated: true,
               sub: "Your team as one book — manager only" },
  home:      { label: "Morning Brief", icon: "sunrise", group: "Today",
               sub: "Where to start today" },
  goals:     { label: "Elite Goals", icon: "target", group: "Performance",
               sub: "Month to date against target" },
  top10:     { label: "Top 10 Purchasers", icon: "crown", group: "Performance",
               key: "top10", sub: "Yesterday's biggest spenders" },
  top20:     { label: "Top 20 · WoW Gaps", icon: "trend-down", group: "Risk",
               key: "decline", sub: `Same-weekday drops vs last ${day}` },
  rd:        { label: "Pending Redemptions", icon: "banknote", group: "Operations",
               key: "rdOver5k", sub: "Locked withdrawals awaiting release" },
  rdfirst:   { label: "First-Time Locked RD", icon: "sparkles", group: "Operations",
               key: "rdFirstTime", sub: "First-ever redemption — under review" },
  tickets:   { label: "Open Tickets", icon: "ticket", group: "Operations",
               key: "zendesk", sub: "Open Zendesk tickets on your book" },
  locks:     { label: "Locked & Take A Break", icon: "lock", group: "Operations",
               key: "locks", sub: "New locks and breaks due to end" },
  birthdays: { label: "Birthdays · Last 3 Days", short: "Birthdays", icon: "gift",
               group: "Care", key: "birthdays", sub: "A reason to reach out" },
};

export const NAV_ORDER = ["dashboard", "team", "home", "goals", "top10", "top20",
                           "rd", "rdfirst", "tickets", "locks", "birthdays"];

export const VIEW_FN: Record<string, () => string> = {
  dashboard: viewDashboard, team: viewTeamGoals, home: viewHome, goals: viewGoals,
  top10: viewTop10, top20: viewTop20, rd: viewPendingRd, rdfirst: viewFirstRd,
  tickets: viewTickets, locks: viewLocks, birthdays: viewBirthdays,
};
