#!/usr/bin/env bun
/**
 * InvestmentMemoryUpdate.hook.ts - Windows-safe continuous memory updater (Stop)
 *
 * Trigger: Stop
 * Purpose: After each dialogue turn, update structured profile files with:
 * - goals
 * - thoughts
 * - preferences
 * - experience
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync } from 'fs';
import { createHash } from 'crypto';
import { join } from 'path';
import { getPaiDir } from './lib/paths';
import { getISOTimestamp } from './lib/time';

interface HookInput {
  session_id?: string;
  transcript_path?: string;
}

interface TranscriptEntry {
  type: 'user' | 'assistant' | string;
  message?: {
    content?: string | Array<{ type?: string; text?: string }>;
  };
}

interface LastTurn {
  userText: string;
  assistantText: string;
}

function readTextContent(entry: TranscriptEntry): string {
  const content = entry.message?.content;
  if (!content) return '';
  if (typeof content === 'string') return content.trim();
  if (Array.isArray(content)) {
    return content
      .filter((c) => c && c.type === 'text' && typeof c.text === 'string')
      .map((c) => c.text!.trim())
      .filter(Boolean)
      .join(' ')
      .trim();
  }
  return '';
}

function loadLastTurn(transcriptPath: string): LastTurn {
  if (!transcriptPath || !existsSync(transcriptPath)) {
    return { userText: '', assistantText: '' };
  }

  const lines = readFileSync(transcriptPath, 'utf-8').split('\n').filter(Boolean);
  const entries: TranscriptEntry[] = [];

  for (const line of lines) {
    try {
      const parsed = JSON.parse(line) as TranscriptEntry;
      if (parsed.type === 'user' || parsed.type === 'assistant') {
        entries.push(parsed);
      }
    } catch {
      // ignore malformed line
    }
  }

  let userIndex = -1;
  for (let i = entries.length - 1; i >= 0; i--) {
    if (entries[i].type === 'user') {
      userIndex = i;
      break;
    }
  }

  if (userIndex === -1) {
    return { userText: '', assistantText: '' };
  }

  const userText = readTextContent(entries[userIndex]);
  let assistantText = '';
  for (let i = entries.length - 1; i > userIndex; i--) {
    if (entries[i].type === 'assistant') {
      assistantText = readTextContent(entries[i]);
      if (assistantText) break;
    }
  }

  return { userText, assistantText };
}

function ensureFile(path: string, title: string): void {
  if (existsSync(path)) return;
  const initial = `# ${title}\n\n*Auto-updated by InvestmentMemoryUpdate hook after each dialogue.*\n\n`;
  writeFileSync(path, initial, 'utf-8');
}

function appendLine(path: string, line: string): void {
  appendFileSync(path, `${line}\n`, 'utf-8');
}

function sanitizeOneLine(text: string, maxLen = 280): string {
  const cleaned = text.replace(/\s+/g, ' ').trim();
  return cleaned.length > maxLen ? `${cleaned.slice(0, maxLen)}...` : cleaned;
}

function extractAssistantSummary(assistantText: string): string {
  if (!assistantText) return '';
  const summaryMatch = assistantText.match(/SUMMARY:\s*([^\n]+)/i);
  if (summaryMatch?.[1]) return sanitizeOneLine(summaryMatch[1], 220);
  return sanitizeOneLine(assistantText, 220);
}

function classify(userText: string): {
  goals: boolean;
  thoughts: boolean;
  preferences: boolean;
} {
  const t = userText.toLowerCase();
  const goals = /(目标|计划|路线图|希望|想要|打算|里程碑|长期|短期|goal|plan|roadmap|build|upgrade)/i.test(t);
  const thoughts = /(我认为|我觉得|看法|观点|判断|逻辑|哲学|thesis|belief|think|opinion)/i.test(t);
  const preferences = /(偏好|喜欢|不喜欢|希望你|请用|不要|优先|格式|语气|风格|频率|preference|prefer|format|style)/i.test(t);
  return { goals, thoughts, preferences };
}

function isDuplicateAndSave(statePath: string, fingerprint: string): boolean {
  if (existsSync(statePath)) {
    try {
      const prev = JSON.parse(readFileSync(statePath, 'utf-8')) as { last_fingerprint?: string };
      if (prev.last_fingerprint === fingerprint) {
        return true;
      }
    } catch {
      // ignore parse error
    }
  }

  writeFileSync(
    statePath,
    JSON.stringify({ last_fingerprint: fingerprint, updated_at: getISOTimestamp() }, null, 2),
    'utf-8'
  );
  return false;
}

async function readStdinWithTimeout(timeout = 5000): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = '';
    const timer = setTimeout(() => reject(new Error('timeout')), timeout);
    process.stdin.on('data', (chunk) => {
      data += chunk.toString();
    });
    process.stdin.on('end', () => {
      clearTimeout(timer);
      resolve(data);
    });
    process.stdin.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

async function main() {
  try {
    const raw = await readStdinWithTimeout();
    if (!raw.trim()) {
      process.exit(0);
    }

    const input = JSON.parse(raw) as HookInput;
    const paiDir = getPaiDir();
    const userDir = join(paiDir, 'skills', 'InvestmentCRO', 'USER');
    const stateDir = join(paiDir, 'MEMORY', 'STATE');
    if (!existsSync(userDir)) mkdirSync(userDir, { recursive: true });
    if (!existsSync(stateDir)) mkdirSync(stateDir, { recursive: true });

    const goalsFile = join(userDir, 'GOALS.md');
    const thoughtsFile = join(userDir, 'THOUGHTS.md');
    const preferencesFile = join(userDir, 'PREFERENCES.md');
    const experienceFile = join(userDir, 'EXPERIENCE.md');
    const stateFile = join(stateDir, 'investment-memory-state.json');

    ensureFile(goalsFile, 'Goals Memory');
    ensureFile(thoughtsFile, 'Thoughts Memory');
    ensureFile(preferencesFile, 'Preferences Memory');
    ensureFile(experienceFile, 'Experience Memory');

    const turn = loadLastTurn(input.transcript_path || '');
    if (!turn.userText) {
      process.exit(0);
    }

    const fingerprint = createHash('sha1')
      .update(`${input.session_id || ''}|${sanitizeOneLine(turn.userText, 500)}`)
      .digest('hex');

    if (isDuplicateAndSave(stateFile, fingerprint)) {
      process.exit(0);
    }

    const now = getISOTimestamp();
    const session = input.session_id || 'unknown-session';
    const userLine = sanitizeOneLine(turn.userText, 280);
    const assistantLine = extractAssistantSummary(turn.assistantText);

    const tags = classify(turn.userText);

    if (tags.goals) {
      appendLine(goalsFile, `- ${now} | ${session} | ${userLine}`);
    }
    if (tags.thoughts) {
      appendLine(thoughtsFile, `- ${now} | ${session} | ${userLine}`);
    }
    if (tags.preferences) {
      appendLine(preferencesFile, `- ${now} | ${session} | ${userLine}`);
    }

    // Always record experience to ensure every dialogue contributes memory.
    appendLine(
      experienceFile,
      `- ${now} | ${session} | user: ${userLine}${assistantLine ? ` | assistant: ${assistantLine}` : ''}`
    );

    process.exit(0);
  } catch {
    // Non-blocking by design
    process.exit(0);
  }
}

main();
