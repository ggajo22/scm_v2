"""Tests for the sync_orders management command.

CLI entry point for the incremental Shopify order sync (scheduler path).
The command owns no sync logic of its own -- it delegates to sync_store()
-- so these tests pin the contract that matters to a scheduler: which
stores get synced, that one store's failure cannot abort the other, and
that a failure surfaces as a non-zero exit.
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

_SYNC_STORE_TARGET = "order.management.commands.sync_orders.sync_store"


def _ok(synced=0, updated=0):
    return {
        "synced_count": synced,
        "updated_count": updated,
        "error": None,
        "updated_at_min": None,
    }


@pytest.mark.django_db
def test_syncs_both_stores_by_default():
    with patch(_SYNC_STORE_TARGET, return_value=_ok(2, 1)) as mock_sync:
        call_command("sync_orders")

    assert [c.args[0] for c in mock_sync.call_args_list] == ["gimssine", "etoile"]


@pytest.mark.django_db
def test_store_option_syncs_only_that_store():
    with patch(_SYNC_STORE_TARGET, return_value=_ok()) as mock_sync:
        call_command("sync_orders", "--store", "gimssine")

    mock_sync.assert_called_once()
    assert mock_sync.call_args.args[0] == "gimssine"


@pytest.mark.django_db
def test_one_store_raising_does_not_abort_the_other_and_exits_nonzero():
    def side_effect(store_type):
        if store_type == "gimssine":
            raise RuntimeError("shopify 500")
        return _ok(3, 0)

    with patch(_SYNC_STORE_TARGET, side_effect=side_effect) as mock_sync:
        with pytest.raises(CommandError, match="gimssine"):
            call_command("sync_orders")

    # etoile must still have been attempted after gimssine blew up.
    assert [c.args[0] for c in mock_sync.call_args_list] == ["gimssine", "etoile"]


@pytest.mark.django_db
def test_error_returned_in_result_dict_also_exits_nonzero():
    # sync_store() reports some failures via the result dict rather than
    # raising; the scheduler must see those as failures too.
    failing = {
        "synced_count": 0,
        "updated_count": 0,
        "error": "HTTP 429",
        "updated_at_min": None,
    }
    with patch(_SYNC_STORE_TARGET, return_value=failing):
        with pytest.raises(CommandError, match="gimssine, etoile"):
            call_command("sync_orders")


@pytest.mark.django_db
def test_successful_run_does_not_raise():
    with patch(_SYNC_STORE_TARGET, return_value=_ok(1, 4)):
        call_command("sync_orders")
