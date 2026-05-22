"""
tests/unit/domain/test_rename_operation.py
"""
import time
import pytest
from src.domain.rename_operation import RenameOperation, RenameStatus


class TestRenameOperation:
    def _make_op(self):
        return RenameOperation(old_name="PC-001", new_name="PC-002", operator="CORP\\admin")

    def test_initial_status_pending(self):
        op = self._make_op()
        assert op.status == RenameStatus.PENDING

    def test_mark_started(self):
        op = self._make_op()
        op.mark_started()
        assert op.status == RenameStatus.RUNNING
        assert op.started_at is not None

    def test_mark_success(self):
        op = self._make_op()
        op.mark_started()
        op.mark_success()
        assert op.status == RenameStatus.SUCCESS
        assert op.completed_at is not None

    def test_mark_failed(self):
        op = self._make_op()
        op.mark_started()
        op.mark_failed("IS_DC", "Computer is a Domain Controller")
        assert op.status == RenameStatus.FAILED
        assert op.error_code == "IS_DC"
        assert "Domain Controller" in op.error_detail

    def test_duration_ms(self):
        op = self._make_op()
        op.mark_started()
        time.sleep(0.01)
        op.mark_success()
        assert op.duration_ms is not None
        assert op.duration_ms >= 0

    def test_duration_ms_none_if_not_started(self):
        op = self._make_op()
        assert op.duration_ms is None

    def test_operation_id_generated(self):
        op = self._make_op()
        assert op.operation_id
        assert len(op.operation_id) == 8

    def test_name_uppercased(self):
        op = RenameOperation(old_name="pc-001", new_name="pc-002", operator="admin")
        # RenameOperation doesn't auto-uppercase — that's Computer's job
        assert op.old_name == "pc-001"

    def test_unique_operation_ids(self):
        ops = [self._make_op() for _ in range(20)]
        ids = {op.operation_id for op in ops}
        assert len(ids) == 20  # all unique
