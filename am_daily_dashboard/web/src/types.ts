/** Shared shapes for the AM Brief board.
 *
 * Payload rows are deliberately loose. They arrive as JSON built by
 * generate_am_daily_dashboard.py and goals.py, where each section has its own
 * ad hoc row shape and new fields are added often. Inventing a strict
 * interface per section here would be a second, drifting copy of the Python
 * contract; the payload-shape guarantees are tested where they are built
 * (test_goals.py, verify_brief.py) and where they are rendered (tests_js).
 */
export type Dict = Record<string, any>;

/** One sidebar section: nav entry, routing and topbar copy. */
export interface ViewDef {
  label: string;
  /** Sidebar label when the full label is too long for the rail. */
  short?: string;
  icon: string;
  group: string;
  /** Payload key whose row count becomes the nav badge. */
  key?: string;
  /** Topbar strapline. */
  sub?: string;
  /** Hidden entirely from per-AM files. */
  managerOnly?: boolean;
  /** Needs the manager passcode before it renders. */
  gated?: boolean;
  /** Placeholder nav item — no CSV export, shows coming-soon view. */
  comingSoon?: boolean;
}

/** One row in the sidebar: either a section label or a view link. */
export type NavEntry =
  | { kind: "section"; label: string }
  | { kind: "view"; id: string };

export interface NavGroup {
  id: string;
  /** Omit for pinned Morning Brief (no group header). */
  label?: string;
  accent?: "manager" | "performance" | "operations" | "gaps" | "brand" | "outreach";
  pinned?: boolean;
  entries: NavEntry[];
}

export interface AppState {
  view: string;
  agent: string;
  unlocked: boolean;
  gateError: string;
  collapsed: boolean;
  mobileOpen: boolean;
  ticket: Dict | null;
  calOpen: boolean;
  calMonth: string;
}

export interface PaginateResult {
  slice: Dict[];
  pager: string;
  from: number;
  to: number;
  total: number;
}

export interface TableOpts {
  /** Column that gets the tone dot prefixed. */
  markerCol?: number;
  empty?: string;
  tableClass?: string;
  frameClass?: string;
  totalRowIndex?: number;
}

export interface SortOption {
  value: string;
  label: string;
}

export interface TableCardOpts {
  rows: Dict[];
  stateKey: string;
  headers: string[];
  align?: string[];
  /** One row's cells, already HTML — not a whole `<tr>`. */
  renderRow: (row: Dict) => string[];
  markerCol?: number;
  empty?: string;
  tableClass?: string;
  /** Size the table to its content instead of the panel width. */
  compact?: boolean;
  /** Optional class on the outer card wrapper. */
  cardClass?: string;
  /** Default true; off for sections where a search box is noise. */
  showSearch?: boolean;
  /** Extra row fields the search box should match on. */
  extraKeys?: string[];
  sortOptions?: SortOption[];
  sortFn?: (rows: Dict[], sortBy: string) => Dict[];
  defaultSort?: string;
}
