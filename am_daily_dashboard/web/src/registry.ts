/** Section registry — drives the sidebar, routing and the topbar crumb. */
import type { NavGroup, ViewDef } from "./types";
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
import { viewBigWinners } from "./views/bigWinners";
import { viewBigLosers } from "./views/bigLosers";
import { viewCrmCalendar } from "./views/crmCalendar";
import { viewAnniversary } from "./views/anniversary";
import {
  viewGamesNew,
  viewGamesSticky,
} from "./views/comingSoon";

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "manager",
    label: "Manager",
    accent: "manager",
    entries: [{ kind: "view", id: "dashboard" }, { kind: "view", id: "team" }],
  },
  {
    id: "home",
    pinned: true,
    entries: [{ kind: "view", id: "home" }],
  },
  {
    id: "performance",
    label: "Performance",
    accent: "performance",
    entries: [{ kind: "view", id: "goals" }, { kind: "view", id: "top10" }],
  },
  {
    id: "daily",
    label: "Daily Triggers",
    accent: "operations",
    entries: [
      { kind: "view", id: "tickets" },
      { kind: "view", id: "rd" },
      { kind: "view", id: "rdfirst" },
      { kind: "view", id: "bigwinners" },
      { kind: "view", id: "biglosers" },
      { kind: "view", id: "locks" },
      { kind: "view", id: "birthdays" },
      { kind: "view", id: "anniversary" },
    ],
  },
  {
    id: "declining",
    label: "Declining & Churn",
    accent: "gaps",
    entries: [{ kind: "view", id: "top20" }],
  },
  {
    id: "crm",
    label: "CRM",
    accent: "brand",
    entries: [{ kind: "view", id: "crmCalendar" }],
  },
  {
    id: "games",
    label: "Games",
    accent: "games",
    entries: [{ kind: "view", id: "gamesSticky" }, { kind: "view", id: "gamesNew" }],
  },
];

export const VIEWS: Record<string, ViewDef> = {
  dashboard:  { label: "Manager Dashboard", short: "Dashboard", icon: "gauge",
                group: "Manager", managerOnly: true, gated: true,
                sub: "Cross-AM roll-up, manager only" },
  team:       { label: "Team Goals", icon: "target", group: "Manager",
                managerOnly: true, gated: true,
                sub: "Your team as one book, manager only" },
  home:       { label: "Morning Brief", icon: "sunrise", group: "Morning Brief",
                sub: "Where to start today" },
  goals:      { label: "Elite Goals", icon: "target", group: "Performance",
                sub: "Personal goals progress" },
  top10:      { label: "Top 10 Purchasers", icon: "crown", group: "Performance",
                key: "top10", sub: "Yesterday's biggest spenders" },
  top20:      { label: "Top 20 Dropping", icon: "trend-down", group: "Declining & Churn",
                key: "decline", sub: `Same-weekday drops vs last ${day}` },
  bigwinners: { label: "Big Winners · ≥$20K · Last 3 Days", short: "Big Winners", icon: "trend-up",
                group: "Daily Triggers", key: "bigWinners",
                sub: "Players who won $20K+ on their peak day in the window" },
  biglosers:  { label: "Big Losers · ≥$5K · Last 3 Days", short: "Big Losers", icon: "trend-down",
                group: "Daily Triggers", key: "bigLosers",
                sub: "Players who lost $5K+ to the house on their peak day" },
  rd:         { label: "Pending Redemptions · Last 3 Days", short: "Pending Redemptions", icon: "banknote",
                group: "Daily Triggers", key: "rdOver5k",
                sub: "Locked withdrawals awaiting release" },
  rdfirst:    { label: "First-Time Locked RD · Last 3 Days", short: "First-Time RD", icon: "sparkles",
                group: "Daily Triggers", key: "rdFirstTime",
                sub: "First-ever redemption, under review" },
  tickets:    { label: "Open Tickets", icon: "ticket", group: "Daily Triggers",
                key: "zendesk", sub: "Open Zendesk tickets on your book" },
  locks:      { label: "Locked & Take A Break · Last 3 Days", short: "Lock & TAB", icon: "lock",
                group: "Daily Triggers", key: "locks",
                sub: "New locks and breaks due to end" },
  birthdays:  { label: "Birthdays · Last 3 Days", short: "Birthdays", icon: "gift",
                group: "Daily Triggers", key: "birthdays", sub: "A reason to reach out" },
  crmCalendar: { label: "CRM Calendar", icon: "calendar", group: "CRM",
                 sub: "Weekday offer playbook" },
  gamesSticky: { label: "Sticky Games", icon: "slots", group: "Games",
                 comingSoon: true, sub: "Habitual games and momentum" },
  gamesNew:    { label: "New Games", icon: "sparkles", group: "Games",
                 comingSoon: true, sub: "Titles gaining traction" },
  anniversary: { label: "1 Month Anniversary", short: "1M Anniversary", icon: "gift",
                 group: "Daily Triggers", key: "anniversary",
                 sub: "30-day managed milestone outreach" },
};

export const NAV_ORDER: string[] = NAV_GROUPS.flatMap((g) =>
  g.entries.filter((e): e is { kind: "view"; id: string } => e.kind === "view").map((e) => e.id)
);

export const VIEW_FN: Record<string, () => string> = {
  dashboard: viewDashboard, team: viewTeamGoals, home: viewHome, goals: viewGoals,
  top10: viewTop10, top20: viewTop20, bigwinners: viewBigWinners, biglosers: viewBigLosers,
  rd: viewPendingRd, rdfirst: viewFirstRd,
  tickets: viewTickets, locks: viewLocks, birthdays: viewBirthdays,
  crmCalendar: viewCrmCalendar, gamesSticky: viewGamesSticky, gamesNew: viewGamesNew,
  anniversary: viewAnniversary,
};

/** @deprecated use NAV_GROUPS */
export const GROUP_ORDER = [...new Set(NAV_GROUPS.map((g) => g.label).filter(Boolean))] as string[];
