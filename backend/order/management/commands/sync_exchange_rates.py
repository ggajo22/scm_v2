"""Management command: sync_exchange_rates (SPEC-ORDER-022).

Handles both the initial gap backfill (2026-06-19 onward) and ongoing
periodic synchronization of the ExchangeRate table -- no separate one-off
backfill command exists (REQ-XRATE-005).

Usage:
    python manage.py sync_exchange_rates --start 2026-06-19 --end 2026-08-14
    python manage.py sync_exchange_rates   # default range: next day after
                                            # latest stored date, through
                                            # today (UTC)
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

# D16 [HARD]: import the name directly into this module's namespace, not
# `from order import exchange_rates` -- tests patch
# "order.management.commands.sync_exchange_rates.fetch_usd_krw_rate"; the
# module-qualified form would make that patch a silent no-op and every test
# would hit the real network.
from order.exchange_rates import ExchangeRateFetchError, fetch_usd_krw_rate
from order.models import ExchangeRate


class Command(BaseCommand):
    help = (
        "Sync the ExchangeRate table from the external data source "
        "(fetch_usd_krw_rate). Handles both initial gap backfill and "
        "ongoing periodic sync via --start/--end (REQ-XRATE-005)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--start",
            type=str,
            default=None,
            help=(
                "Start date (YYYY-MM-DD). Defaults to the day after the "
                "most recent stored ExchangeRate.effective_date."
            ),
        )
        parser.add_argument(
            "--end",
            type=str,
            default=None,
            help="End date (YYYY-MM-DD). Defaults to today (UTC).",
        )

    def handle(self, *args, **options):
        start = self._resolve_start(options["start"])
        end = self._resolve_end(options["end"])

        # REQ-XRATE-010: start later than end -> no fetch, no write, exit 0.
        if start > end:
            return

        fetched, failures = self._fetch_range(start, end)
        created_count, skipped_count = self._write_batch(fetched)

        self.stdout.write(
            self.style.SUCCESS(
                f"{created_count} new record(s) saved, "
                f"{skipped_count} already existed and were skipped, "
                f"{len(failures)} failed."
            )
        )

        # REQ-XRATE-016: raise only after successful dates are already
        # written above -- failures never abort or roll back successes.
        if failures:
            failed_dates = [str(failed_date) for failed_date, _ in failures]
            raise CommandError(f"{len(failures)} date(s) failed to fetch: {failed_dates}")

    def _resolve_start(self, start_arg: str | None) -> date:
        if start_arg:
            return date.fromisoformat(start_arg)
        latest = (
            ExchangeRate.objects.order_by("-effective_date")
            .values_list("effective_date", flat=True)
            .first()
        )
        # REQ-XRATE-008: no --start and no existing record -> CommandError,
        # not an undefined default (guards against None + timedelta crash).
        if latest is None:
            raise CommandError(
                "No --start given and no ExchangeRate record exists to "
                "compute a default start date."
            )
        return latest + timedelta(days=1)

    def _resolve_end(self, end_arg: str | None) -> date:
        if end_arg:
            return date.fromisoformat(end_arg)
        # REQ-XRATE-009: timezone.localdate(), not datetime.date.today() --
        # this project's TIME_ZONE="UTC"/USE_TZ=True means date.today() (OS
        # local date) drifts a day ahead of the UTC date the rest of the
        # system uses, for KST-zone machines during 00:00-09:00 KST.
        return timezone.localdate()

    def _fetch_range(
        self, start: date, end: date
    ) -> tuple[list[tuple[date, Decimal]], list[tuple[date, ExchangeRateFetchError]]]:
        # Design decision E: this loop never touches the database -- the
        # transaction boundary (design decision E) starts only in
        # _write_batch, so a mid-range failure can never roll back dates
        # that already succeeded (REQ-XRATE-011, REQ-XRATE-014).
        fetched: list[tuple[date, Decimal]] = []
        failures: list[tuple[date, ExchangeRateFetchError]] = []
        current = start
        while current <= end:
            try:
                fetched.append(fetch_usd_krw_rate(current))
            except ExchangeRateFetchError as exc:
                failures.append((current, exc))
                # REQ-XRATE-016/017: report each failure individually, as
                # it happens, not just in a final summary.
                self.stderr.write(self.style.ERROR(f"  {current}: {exc}"))
            current += timedelta(days=1)
        return fetched, failures

    def _write_batch(self, fetched: list[tuple[date, Decimal]]) -> tuple[int, int]:
        # REQ-XRATE-024: collapse duplicate echoed publish dates via dict
        # keys -- several requested dates in one run (e.g. a Sat/Sun pair)
        # can echo the same published date, and bulk_create would violate
        # ExchangeRate.effective_date's unique=True if given duplicates.
        published: dict[date, Decimal] = {}
        for published_date, rate in fetched:
            published[published_date] = rate

        if not published:
            return 0, 0

        # @MX:NOTE: [AUTO] This atomic() block intentionally covers only the
        # existence-check + bulk_create, not the HTTP fetch loop above
        # (design decision E) -- this project's DB is a remote RDS instance
        # (us-west-2, SPEC-ORDER-021 design decision F), so holding a
        # transaction open across up to dozens of sequential external HTTP
        # calls would needlessly hold connections/locks, and would roll
        # back already-successful fetches on a later failure (REQ-XRATE-011,
        # REQ-XRATE-016).
        # REQ-XRATE-012/014: exactly two queries, scoped only to this
        # write step -- never spans the HTTP fetch loop above.
        with transaction.atomic():
            existing = set(
                ExchangeRate.objects.filter(effective_date__in=published.keys())
                .values_list("effective_date", flat=True)
            )
            # @MX:NOTE: [AUTO] Dates already present in `existing` are never
            # included in `to_create` -- this is the REQ-XRATE-013
            # "do not overwrite" policy (design decision D). It protects
            # values manually corrected via PUT /api/exchange-rates/{date}/
            # (SPEC-ORDER-009) from being silently reverted by the next
            # automated sync run, and is symmetric with REQ-XRATE-021
            # (no retroactive correction of the pre-existing 117 records).
            to_create = [
                ExchangeRate(effective_date=d, rate=r)
                for d, r in published.items()
                if d not in existing
            ]
            # Design decision G: ignore_conflicts=True defends against a
            # concurrent run racing on the same effective_date between the
            # existence check above and this insert.
            ExchangeRate.objects.bulk_create(to_create, ignore_conflicts=True)

        return len(to_create), len(published) - len(to_create)
