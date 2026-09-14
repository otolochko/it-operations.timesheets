'use client';

import * as React from 'react';
import { PanelCard } from '@/components/PanelCard';
import type { TimesheetCell } from '@/lib/api';
import { formatSecondsWithMode } from '@/lib/format';
import { useHoursFormat } from '@/lib/HoursFormatContext';
import { tokens } from '@/lib/theme/tokens';

export interface DashboardChartsProps {
  cells: TimesheetCell[];
}

interface AuthorTotal {
  accountId: string;
  displayName: string;
  totalSeconds: number;
}

interface ChartSeries {
  key: string;
  label: string;
  authorIds: Set<string>;
  color: string;
}

const STACKED_AUTHOR_LIMIT = 6;
const RANKING_LIMIT = 8;
const CHART_COLORS = [
  tokens.chart1,
  tokens.chart2,
  tokens.chart3,
  tokens.chart4,
  tokens.chart5,
  tokens.chart6,
];

function getAuthorTotals(cells: TimesheetCell[]): AuthorTotal[] {
  const totals = new Map<string, AuthorTotal>();

  for (const cell of cells) {
    const current = totals.get(cell.author_account_id);
    if (current) {
      current.totalSeconds += cell.total_seconds;
    } else {
      totals.set(cell.author_account_id, {
        accountId: cell.author_account_id,
        displayName: cell.author_display_name,
        totalSeconds: cell.total_seconds,
      });
    }
  }

  return Array.from(totals.values()).sort(
    (a, b) => b.totalSeconds - a.totalSeconds || a.displayName.localeCompare(b.displayName),
  );
}

function getSeries(authors: AuthorTotal[]): ChartSeries[] {
  const visibleAuthors = authors.slice(0, STACKED_AUTHOR_LIMIT);
  const series: ChartSeries[] = visibleAuthors.map((author, index) => ({
    key: author.accountId,
    label: author.displayName,
    authorIds: new Set([author.accountId]),
    color: CHART_COLORS[index],
  }));

  if (authors.length > STACKED_AUTHOR_LIMIT) {
    series.push({
      key: 'others',
      label: `Others (${authors.length - STACKED_AUTHOR_LIMIT})`,
      authorIds: new Set(authors.slice(STACKED_AUTHOR_LIMIT).map((author) => author.accountId)),
      color: tokens.chartOther,
    });
  }

  return series;
}

function formatPeriod(period: string): string {
  return new Date(`${period}T00:00:00`).toLocaleDateString('en', {
    month: 'short',
    day: 'numeric',
  });
}

function niceMaximum(hours: number): number {
  if (hours <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(hours));
  const normalized = hours / magnitude;
  const rounded = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return rounded * magnitude;
}

function StackedTimeChart({
  cells,
  authors,
}: {
  cells: TimesheetCell[];
  authors: AuthorTotal[];
}) {
  const { format } = useHoursFormat();
  const periods = Array.from(new Set(cells.map((cell) => cell.period_start))).sort();
  const series = getSeries(authors);
  const secondsByPeriodAndAuthor = new Map<string, Map<string, number>>();

  for (const cell of cells) {
    const periodValues = secondsByPeriodAndAuthor.get(cell.period_start) ?? new Map();
    periodValues.set(
      cell.author_account_id,
      (periodValues.get(cell.author_account_id) ?? 0) + cell.total_seconds,
    );
    secondsByPeriodAndAuthor.set(cell.period_start, periodValues);
  }

  const periodTotals = periods.map((period) =>
    Array.from(secondsByPeriodAndAuthor.get(period)?.values() ?? []).reduce(
      (sum, seconds) => sum + seconds,
      0,
    ),
  );
  const maxHours = niceMaximum(Math.max(...periodTotals, 0) / 3600);

  const width = 840;
  const height = 300;
  const margin = { top: 12, right: 12, bottom: 42, left: 50 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const bandWidth = plotWidth / Math.max(periods.length, 1);
  const barWidth = Math.max(4, Math.min(48, bandWidth * 0.64));
  const labelStep = Math.max(1, Math.ceil(periods.length / 7));
  const tickCount = 4;

  return (
    <PanelCard title="Logged time trend">
      <p className="mb-4 text-xs text-text-muted">Hours per period, stacked by author</p>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-auto w-full min-w-[42rem]"
          role="img"
          aria-label="Logged time by period and author"
        >
          {Array.from({ length: tickCount + 1 }, (_, index) => {
            const value = (maxHours / tickCount) * index;
            const y = margin.top + plotHeight - (plotHeight * index) / tickCount;
            return (
              <g key={value}>
                <line
                  x1={margin.left}
                  x2={width - margin.right}
                  y1={y}
                  y2={y}
                  stroke={tokens.border}
                  strokeWidth="1"
                />
                <text
                  x={margin.left - 10}
                  y={y + 4}
                  textAnchor="end"
                  fill={tokens.textMuted}
                  fontSize="11"
                >
                  {Number.isInteger(value) ? value : value.toFixed(1)}h
                </text>
              </g>
            );
          })}

          {periods.map((period, periodIndex) => {
            const x = margin.left + periodIndex * bandWidth + (bandWidth - barWidth) / 2;
            const periodValues = secondsByPeriodAndAuthor.get(period) ?? new Map();
            let stackedSeconds = 0;

            return (
              <g key={period}>
                {series.map((item) => {
                  const seconds = Array.from(item.authorIds).reduce(
                    (sum, accountId) => sum + (periodValues.get(accountId) ?? 0),
                    0,
                  );
                  if (seconds === 0) return null;

                  const segmentHeight = (seconds / 3600 / maxHours) * plotHeight;
                  const y = margin.top + plotHeight - segmentHeight - (stackedSeconds / 3600 / maxHours) * plotHeight;
                  stackedSeconds += seconds;

                  return (
                    <rect
                      key={item.key}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={segmentHeight}
                      rx="2"
                      fill={item.color}
                    >
                      <title>{`${period} · ${item.label}: ${formatSecondsWithMode(seconds, format)}`}</title>
                    </rect>
                  );
                })}
                {(periodIndex % labelStep === 0 || periodIndex === periods.length - 1) ? (
                  <text
                    x={x + barWidth / 2}
                    y={height - 14}
                    textAnchor="middle"
                    fill={tokens.textMuted}
                    fontSize="11"
                  >
                    {formatPeriod(period)}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
        {series.map((item) => (
          <div key={item.key} className="flex min-w-0 items-center gap-2 text-xs text-text-muted">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: item.color }}
            />
            <span className="max-w-36 truncate" title={item.label}>{item.label}</span>
          </div>
        ))}
      </div>
    </PanelCard>
  );
}

function AuthorRanking({ authors }: { authors: AuthorTotal[] }) {
  const { format } = useHoursFormat();
  const visibleAuthors = authors.slice(0, RANKING_LIMIT);
  const maximum = visibleAuthors[0]?.totalSeconds ?? 1;

  return (
    <PanelCard title="Hours by author">
      <p className="mb-4 text-xs text-text-muted">
        Top {visibleAuthors.length} of {authors.length} selected authors
      </p>
      <div className="flex flex-col gap-4">
        {visibleAuthors.map((author, index) => {
          const formattedTotal = formatSecondsWithMode(author.totalSeconds, format);
          return (
            <div
              key={author.accountId}
              role="meter"
              aria-label={`${author.displayName}: ${formattedTotal}`}
              aria-valuemin={0}
              aria-valuemax={maximum}
              aria-valuenow={author.totalSeconds}
            >
              <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
                <span className="truncate font-medium text-text-primary" title={author.displayName}>
                  {author.displayName}
                </span>
                <span className="shrink-0 tabular-nums text-text-muted">{formattedTotal}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-surface-raised">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.max(2, (author.totalSeconds / maximum) * 100)}%`,
                    backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </PanelCard>
  );
}

export function DashboardCharts({ cells }: DashboardChartsProps) {
  const authors = React.useMemo(() => getAuthorTotals(cells), [cells]);
  if (cells.length === 0 || authors.length === 0) return null;

  return (
    <section
      aria-label="Timesheet charts"
      className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]"
    >
      <StackedTimeChart cells={cells} authors={authors} />
      <AuthorRanking authors={authors} />
    </section>
  );
}
