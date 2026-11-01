/**
 * One client for the LeadRoute API.
 * A missing field is an error, not an empty queue that looks like there are no leads.
 */

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export type LeadCard = {
  personId: string;
  name: string;
  company: string;
  channel: string;
  channelLabel: string;
  receivedAtIsrael: string;
  score: number;
  band: string;
  status: string;
  statusLabel: string;
  owner: string | null;
};

export type Condition = {
  key: string;
  label: string;
  passed: boolean;
  evidence: string;
};

export type Factor = {
  key: string;
  label: string;
  points: number;
};

export type Extraction = {
  language: string;
  languageLabel: string;
  intent: string;
  intentLabel: string;
  statedRole: string | null;
  statedRoleLabel: string | null;
  statedProblem: string | null;
  statedProblemLabel: string | null;
  statedProblemQuote: string | null;
  instructionOverrideAttempt: boolean;
  quotes: string[];
};

export type Message = {
  inboundId: string;
  channel: string;
  channelLabel: string;
  direction: string;
  source: string | null;
  fromName: string;
  subject: string | null;
  body: string;
  receivedAtIsrael: string;
  analysisMode: string | null;
  analysisModeLabel: string | null;
  analysisFailed: boolean | null;
  injection: boolean | null;
  extraction: Extraction | null;
};

export type SalesDecision = {
  decision: string;
  decisionLabel: string;
  decidedAtIsrael: string;
};

export type DraftCompose = {
  to: string | null;
  subject: string | null;
  gmailUrl: string | null;
  zohoUrl: string | null;
};

export type LeadDetail = {
  personId: string;
  name: string;
  company: string;
  status: string;
  statusLabel: string;
  owner: string | null;
  score: number;
  band: string;
  analysisMode: string;
  analysisModeLabel: string;
  rationale: string;
  draft: string | null;
  draftHtml: string | null;
  compose: DraftCompose;
  draftState: string;
  draftStateLabel: string;
  draftDirection: string;
  draftFeedback: { rating: "up" | "down" | null; comment: string | null };
  writerLearningWeek: string | null;
  salesDecision: SalesDecision | null;
  factors: Factor[];
  conditions: Condition[];
  messages: Message[];
  nowIsrael: string;
};

export type RecordLink = {
  id: string;
  personId: string | null;
  label: string;
};

export type CountLine = {
  actual: number | null;
  target: number | null;
  unknown: boolean;
  records: RecordLink[];
};

export type KpiPack = {
  weekStart: string;
  weekEnd: string;
  qls: CountLine;
  meetingsBooked: CountLine;
  meetingsHeld: CountLine;
  opportunities: CountLine;
  bySource: { source: string; line: CountLine }[];
  expansionMeetingsBooked: CountLine;
  expansionMeetingsHeld: CountLine;
  expansionOpportunities: CountLine;
};

export type EngineRow = {
  engine: string;
  mentioned: boolean;
  citedOwned: boolean;
  competitors: string[];
  lookalikes: string[];
  wrongClaim: boolean;
};

export type Gap = {
  promptId: string;
  prompt: string;
  cluster: string;
  priority: number;
  score: number;
  missCount: number;
  competitorWithoutOwnedCount: number;
  wrongClaimCount: number;
  engines: EngineRow[];
};

export type Brief = {
  mode: string;
  label: string;
  blocked: boolean;
  blockReasons: string[];
  promptId: string;
  title: string;
  directAnswer: string;
  directAnswerWords: number;
  sections: { heading: string; body: string }[];
  faq: { question: string; answer: string }[];
  schemaOrgType: string;
  removedSentences: number;
  briefFingerprint: string;
  feedbackRating: "up" | "down" | null;
  feedbackComment: string | null;
};

export type VisibilityOverview = {
  promptCount: number;
  engineCount: number;
  answerRows: number;
  topGapScore: number;
  topPromptId: string;
  topPrompt: string;
  stargoMissTotal: number;
  competitorGapTotal: number;
  wrongClaimTotal: number;
  mentionRatePct: number;
  ownedCiteRatePct: number;
};

export type Visibility = {
  overview: VisibilityOverview;
  gaps: Gap[];
  brief: Brief;
  visibilityLearningWeek: string | null;
};

export type Options = {
  channels: string[];
  sources: string[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string") {
    throw new ApiError(`Response field ${key} was not text`);
  }
  return value;
}

function optionalString(record: Record<string, unknown>, key: string): string | null {
  if (!(key in record)) {
    return null;
  }
  const value = record[key];
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  throw new ApiError(`Response field ${key} was not text`);
}

function requiredNumber(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number") {
    throw new ApiError(`Response field ${key} was not a number`);
  }
  return value;
}

function optionalNumber(record: Record<string, unknown>, key: string): number | null {
  const value = record[key];
  if (value === null) {
    return null;
  }
  if (typeof value !== "number") {
    throw new ApiError(`Response field ${key} was not a number`);
  }
  return value;
}

function requiredBoolean(record: Record<string, unknown>, key: string): boolean {
  const value = record[key];
  if (typeof value !== "boolean") {
    throw new ApiError(`Response field ${key} was not yes or no`);
  }
  return value;
}

function asArray(value: unknown, key: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new ApiError(`Response field ${key} was not a list`);
  }
  return value;
}

async function readBody(response: Response): Promise<unknown> {
  if (!response.ok) {
    let detail = response.statusText || "Request failed";
    try {
      const body = (await response.json()) as unknown;
      if (isRecord(body)) {
        const raw = body.detail;
        if (typeof raw === "string") {
          detail = raw;
        } else if (Array.isArray(raw)) {
          detail = raw.map((item) => String(item)).join("; ");
        }
      }
    } catch {
      detail = response.statusText || "Request failed";
    }
    throw new ApiError(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<unknown>;
}

function parseLeadCard(value: unknown): LeadCard {
  if (!isRecord(value)) {
    throw new ApiError("A lead row was not an object");
  }
  return {
    personId: requiredString(value, "person_id"),
    name: requiredString(value, "name"),
    company: requiredString(value, "company"),
    channel: requiredString(value, "channel"),
    channelLabel: requiredString(value, "channel_label"),
    receivedAtIsrael: requiredString(value, "received_at_israel"),
    score: requiredNumber(value, "score"),
    band: requiredString(value, "band"),
    status: requiredString(value, "status"),
    statusLabel: requiredString(value, "status_label"),
    owner: optionalString(value, "owner"),
  };
}

function parseExtraction(value: unknown): Extraction | null {
  if (value === null) {
    return null;
  }
  if (!isRecord(value)) {
    throw new ApiError("Extraction was not an object");
  }
  const quotes = asArray(value.quotes ?? [], "quotes").map((quote) => {
    if (typeof quote !== "string") {
      throw new ApiError("A quote was not text");
    }
    return quote;
  });
  return {
    language: requiredString(value, "language"),
    languageLabel: requiredString(value, "language_label"),
    intent: requiredString(value, "intent"),
    intentLabel: requiredString(value, "intent_label"),
    statedRole: optionalString(value, "stated_role"),
    statedRoleLabel: optionalString(value, "stated_role_label"),
    statedProblem: optionalString(value, "stated_problem"),
    statedProblemLabel: optionalString(value, "stated_problem_label"),
    statedProblemQuote: optionalString(value, "stated_problem_quote"),
    instructionOverrideAttempt: requiredBoolean(value, "instruction_override_attempt"),
    quotes,
  };
}

function optionalBoolean(record: Record<string, unknown>, key: string): boolean | null {
  const value = record[key];
  if (value === null) {
    return null;
  }
  if (typeof value !== "boolean") {
    throw new ApiError(`Response field ${key} was not yes or no`);
  }
  return value;
}

function parseSalesDecision(value: unknown): SalesDecision | null {
  if (value === null) {
    return null;
  }
  if (!isRecord(value)) {
    throw new ApiError("Sales decision was not an object");
  }
  return {
    decision: requiredString(value, "decision"),
    decisionLabel: requiredString(value, "decision_label"),
    decidedAtIsrael: requiredString(value, "decided_at_israel"),
  };
}

function parseMessage(value: unknown): Message {
  if (!isRecord(value)) {
    throw new ApiError("A message was not an object");
  }
  return {
    inboundId: requiredString(value, "inbound_id"),
    channel: requiredString(value, "channel"),
    channelLabel: requiredString(value, "channel_label"),
    direction: requiredString(value, "direction"),
    source: optionalString(value, "source"),
    fromName: requiredString(value, "from_name"),
    subject: optionalString(value, "subject"),
    body: requiredString(value, "body"),
    receivedAtIsrael: requiredString(value, "received_at_israel"),
    analysisMode: optionalString(value, "analysis_mode"),
    analysisModeLabel: optionalString(value, "analysis_mode_label"),
    analysisFailed: optionalBoolean(value, "analysis_failed"),
    injection: optionalBoolean(value, "injection"),
    extraction: parseExtraction(value.extraction ?? null),
  };
}

function parseCountLine(value: unknown): CountLine {
  if (!isRecord(value)) {
    throw new ApiError("A KPI line was not an object");
  }
  const records = asArray(value.records, "records").map((row) => {
    if (!isRecord(row)) {
      throw new ApiError("A drill-down row was not an object");
    }
    return {
      id: requiredString(row, "id"),
      personId: optionalString(row, "person_id"),
      label: requiredString(row, "label"),
    };
  });
  return {
    actual: optionalNumber(value, "actual"),
    target: optionalNumber(value, "target"),
    unknown: requiredBoolean(value, "unknown"),
    records,
  };
}

export async function fetchLeads(): Promise<LeadCard[]> {
  const body = await readBody(await fetch("/api/leads"));
  if (!isRecord(body)) {
    throw new ApiError("Lead list was not an object");
  }
  return asArray(body.leads, "leads").map(parseLeadCard);
}

function parseOptionalThumbRating(
  record: Record<string, unknown>,
  key: string,
): "up" | "down" | null {
  const raw = record[key];
  if (raw === null || raw === undefined) {
    return null;
  }
  if (raw === "up" || raw === "down") {
    return raw;
  }
  throw new ApiError(`Response field ${key} was not a valid rating`);
}

function parseDraftFeedback(value: unknown): {
  rating: "up" | "down" | null;
  comment: string | null;
} {
  if (value === null || value === undefined) {
    return { rating: null, comment: null };
  }
  if (!isRecord(value)) {
    throw new ApiError("Draft feedback was not an object");
  }
  const raw = value.rating;
  let rating: "up" | "down" | null = null;
  if (raw !== null && raw !== undefined) {
    if (raw === "up" || raw === "down") {
      rating = raw;
    } else {
      throw new ApiError("Draft feedback rating was invalid");
    }
  }
  return { rating, comment: optionalString(value, "comment") };
}

function parseCompose(value: unknown): DraftCompose {
  if (!isRecord(value)) {
    return { to: null, subject: null, gmailUrl: null, zohoUrl: null };
  }
  return {
    to: optionalString(value, "to"),
    subject: optionalString(value, "subject"),
    gmailUrl: optionalString(value, "gmail_url"),
    zohoUrl: optionalString(value, "zoho_url"),
  };
}

export async function fetchLead(personId: string): Promise<LeadDetail> {
  const body = await readBody(await fetch(`/api/leads/${encodeURIComponent(personId)}`));
  if (!isRecord(body)) {
    throw new ApiError("Lead detail was not an object");
  }
  const breakdown = body.breakdown;
  if (!isRecord(breakdown)) {
    throw new ApiError("Score breakdown was missing");
  }
  const factors = asArray(breakdown.factors, "factors").map((factor) => {
    if (!isRecord(factor)) {
      throw new ApiError("A score factor was not an object");
    }
    return {
      key: requiredString(factor, "key"),
      label: requiredString(factor, "label"),
      points: requiredNumber(factor, "points"),
    };
  });
  const conditions = asArray(body.conditions, "conditions").map((condition) => {
    if (!isRecord(condition)) {
      throw new ApiError("A condition was not an object");
    }
    return {
      key: requiredString(condition, "key"),
      label: requiredString(condition, "label"),
      passed: requiredBoolean(condition, "passed"),
      evidence: requiredString(condition, "evidence"),
    };
  });
  return {
    personId: requiredString(body, "person_id"),
    name: requiredString(body, "name"),
    company: requiredString(body, "company"),
    status: requiredString(body, "status"),
    statusLabel: requiredString(body, "status_label"),
    owner: optionalString(body, "owner"),
    score: requiredNumber(body, "score"),
    band: requiredString(body, "band"),
    analysisMode: requiredString(body, "analysis_mode"),
    analysisModeLabel: requiredString(body, "analysis_mode_label"),
    rationale: requiredString(body, "rationale"),
    draft: optionalString(body, "draft"),
    draftHtml: optionalString(body, "draft_html"),
    compose: parseCompose(body.compose),
    draftState: requiredString(body, "draft_state"),
    draftStateLabel: requiredString(body, "draft_state_label"),
    draftDirection: requiredString(body, "draft_direction"),
    draftFeedback: isRecord(body.draft_feedback)
      ? parseDraftFeedback(body.draft_feedback)
      : { rating: null, comment: null },
    writerLearningWeek: optionalString(body, "writer_learning_week"),
    salesDecision: parseSalesDecision(body.sales_decision),
    factors,
    conditions,
    messages: asArray(body.messages, "messages").map(parseMessage),
    nowIsrael: requiredString(body, "now_israel"),
  };
}

export async function postDraftFeedback(
  personId: string,
  rating: "up" | "down",
  comment?: string,
): Promise<{ rating: string }> {
  const body = await readBody(
    await fetch(`/api/leads/${encodeURIComponent(personId)}/draft-feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rating,
        comment: comment?.trim() ? comment.trim() : null,
      }),
    }),
  );
  if (!isRecord(body)) {
    throw new ApiError("Draft feedback response was not an object");
  }
  return { rating: requiredString(body, "rating") };
}

export async function postDecision(
  personId: string,
  decision: "accepted" | "rejected",
  decidedAt: string,
): Promise<{ note: string; status: string; statusLabel: string }> {
  const body = await readBody(
    await fetch(`/api/leads/${encodeURIComponent(personId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, decided_at: decidedAt }),
    }),
  );
  if (!isRecord(body)) {
    throw new ApiError("Decision response was not an object");
  }
  return {
    note: requiredString(body, "note"),
    status: requiredString(body, "status"),
    statusLabel: requiredString(body, "status_label"),
  };
}

export async function postInbound(input: {
  fromName: string;
  fromEmail: string;
  linkedinUrl: string;
  channel: string;
  text: string;
  receivedAt: string;
  source: string;
}): Promise<{ personId: string; status: string; statusLabel: string }> {
  const body = await readBody(
    await fetch("/api/inbound", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_name: input.fromName,
        from_email: input.fromEmail || null,
        linkedin_url: input.linkedinUrl || null,
        channel: input.channel,
        text: input.text,
        received_at: input.receivedAt || null,
        source: input.source || null,
      }),
    }),
  );
  if (!isRecord(body)) {
    throw new ApiError("Paste response was not an object");
  }
  return {
    personId: requiredString(body, "person_id"),
    status: requiredString(body, "status"),
    statusLabel: requiredString(body, "status_label"),
  };
}

export async function fetchKpi(): Promise<KpiPack> {
  const body = await readBody(await fetch("/api/kpi"));
  if (!isRecord(body)) {
    throw new ApiError("KPI pack was not an object");
  }
  const bySourceRaw = body.by_source;
  if (!isRecord(bySourceRaw)) {
    throw new ApiError("KPI sources were missing");
  }
  const bySource = Object.keys(bySourceRaw).map((source) => ({
    source,
    line: parseCountLine(bySourceRaw[source]),
  }));
  return {
    weekStart: requiredString(body, "week_start"),
    weekEnd: requiredString(body, "week_end"),
    qls: parseCountLine(body.qls),
    meetingsBooked: parseCountLine(body.meetings_booked),
    meetingsHeld: parseCountLine(body.meetings_held),
    opportunities: parseCountLine(body.opportunities),
    bySource,
    expansionMeetingsBooked: parseCountLine(body.expansion_meetings_booked),
    expansionMeetingsHeld: parseCountLine(body.expansion_meetings_held),
    expansionOpportunities: parseCountLine(body.expansion_opportunities),
  };
}

function parseEngine(value: unknown): EngineRow {
  if (!isRecord(value)) {
    throw new ApiError("An engine row was not an object");
  }
  const names = (key: string): string[] =>
    asArray(value[key], key).map((item) => {
      if (typeof item !== "string") {
        throw new ApiError(`A ${key} entry was not text`);
      }
      return item;
    });
  return {
    engine: requiredString(value, "engine"),
    mentioned: requiredBoolean(value, "mentioned"),
    citedOwned: requiredBoolean(value, "cited_owned"),
    competitors: names("competitors"),
    lookalikes: names("lookalikes"),
    wrongClaim: requiredBoolean(value, "wrong_claim"),
  };
}

function parseOverview(value: unknown): VisibilityOverview {
  if (!isRecord(value)) {
    throw new ApiError("Visibility overview was not an object");
  }
  return {
    promptCount: requiredNumber(value, "prompt_count"),
    engineCount: requiredNumber(value, "engine_count"),
    answerRows: requiredNumber(value, "answer_rows"),
    topGapScore: requiredNumber(value, "top_gap_score"),
    topPromptId: requiredString(value, "top_prompt_id"),
    topPrompt: requiredString(value, "top_prompt"),
    stargoMissTotal: requiredNumber(value, "stargo_miss_total"),
    competitorGapTotal: requiredNumber(value, "competitor_gap_total"),
    wrongClaimTotal: requiredNumber(value, "wrong_claim_total"),
    mentionRatePct: requiredNumber(value, "mention_rate_pct"),
    ownedCiteRatePct: requiredNumber(value, "owned_cite_rate_pct"),
  };
}

export async function saveLeadDraft(
  personId: string,
  draft: string,
): Promise<{
  draft: string;
  draftState: string;
  draftStateLabel: string;
  draftHtml: string | null;
  compose: DraftCompose;
}> {
  const body = await readBody(
    await fetch(`/api/leads/${encodeURIComponent(personId)}/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft }),
    }),
  );
  if (!isRecord(body)) {
    throw new ApiError("Save draft response was not an object");
  }
  return {
    draft: requiredString(body, "draft"),
    draftState: requiredString(body, "draft_state"),
    draftStateLabel: requiredString(body, "draft_state_label"),
    draftHtml: optionalString(body, "draft_html"),
    compose: parseCompose(body.compose),
  };
}

export async function fetchVisibility(): Promise<Visibility> {
  const body = await readBody(await fetch("/api/visibility"));
  if (!isRecord(body) || !isRecord(body.brief)) {
    throw new ApiError("Visibility response was not an object");
  }
  const brief = body.brief;
  const sections = asArray(brief.sections, "sections").map((section) => {
    if (!isRecord(section)) {
      throw new ApiError("A brief section was not an object");
    }
    return {
      heading: requiredString(section, "heading"),
      body: requiredString(section, "body"),
    };
  });
  const faq = asArray(brief.faq, "faq").map((item) => {
    if (!isRecord(item)) {
      throw new ApiError("An FAQ row was not an object");
    }
    return {
      question: requiredString(item, "question"),
      answer: requiredString(item, "answer"),
    };
  });
  const gaps = asArray(body.gaps, "gaps").map((gap) => {
    if (!isRecord(gap)) {
      throw new ApiError("A gap row was not an object");
    }
    return {
      promptId: requiredString(gap, "prompt_id"),
      prompt: requiredString(gap, "prompt"),
      cluster: requiredString(gap, "cluster"),
      priority: requiredNumber(gap, "priority"),
      score: requiredNumber(gap, "score"),
      missCount: requiredNumber(gap, "miss_count"),
      competitorWithoutOwnedCount: requiredNumber(gap, "competitor_without_owned_count"),
      wrongClaimCount: requiredNumber(gap, "wrong_claim_count"),
      engines: asArray(gap.engines, "engines").map(parseEngine),
    };
  });
  return {
    overview: parseOverview(body.overview),
    gaps,
    brief: {
      mode: requiredString(brief, "mode"),
      label: requiredString(brief, "label"),
      blocked: requiredBoolean(brief, "blocked"),
      blockReasons: asArray(brief.block_reasons, "block_reasons").map((reason) => {
        if (typeof reason !== "string") {
          throw new ApiError("A block reason was not text");
        }
        return reason;
      }),
      promptId: requiredString(brief, "prompt_id"),
      title: requiredString(brief, "title"),
      directAnswer: requiredString(brief, "direct_answer"),
      directAnswerWords: requiredNumber(brief, "direct_answer_words"),
      sections,
      faq,
      schemaOrgType: requiredString(brief, "schema_org_type"),
      removedSentences: requiredNumber(brief, "removed_sentences"),
      briefFingerprint: requiredString(brief, "brief_fingerprint"),
      feedbackRating: parseOptionalThumbRating(brief, "feedback_rating"),
      feedbackComment: optionalString(brief, "feedback_comment"),
    },
    visibilityLearningWeek: optionalString(body, "visibility_learning_week"),
  };
}

export async function postVisibilityFeedback(input: {
  promptId: string;
  briefFingerprint: string;
  briefSnapshot: Record<string, unknown>;
  rating: "up" | "down";
  comment?: string;
}): Promise<{ rating: string }> {
  const body = await readBody(
    await fetch("/api/visibility/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_id: input.promptId,
        brief_fingerprint: input.briefFingerprint,
        brief_snapshot: input.briefSnapshot,
        rating: input.rating,
        comment: input.comment?.trim() ? input.comment.trim() : null,
      }),
    }),
  );
  if (!isRecord(body)) {
    throw new ApiError("Visibility feedback response was not an object");
  }
  return { rating: requiredString(body, "rating") };
}

export async function fetchOptions(): Promise<Options> {
  const body = await readBody(await fetch("/api/options"));
  if (!isRecord(body)) {
    throw new ApiError("Options were not an object");
  }
  const strings = (key: string): string[] =>
    asArray(body[key], key).map((item) => {
      if (typeof item !== "string") {
        throw new ApiError(`Option ${key} was not text`);
      }
      return item;
    });
  return { channels: strings("channels"), sources: strings("sources") };
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "The request failed";
}
