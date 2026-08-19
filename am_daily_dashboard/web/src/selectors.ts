/** Reads of the payload that depend on which AM is currently selected. */
import type { Dict } from "./types";
import { AGENTS } from "./payload";
import { app } from "./state";

export function agentBlock(): Dict {
  return AGENTS.find((a) => a.agentName === app.agent) || AGENTS[0] || {};
}

export function rowsFor(key: string): Dict[] {
  return agentBlock()[key] || [];
}
