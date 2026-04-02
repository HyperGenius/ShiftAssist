# backend/tests/unit/test_shift_assignment_service.py
"""shift_assignment_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.models import ShiftRequirement, ShiftRequirementAssignment, Worker
from app.models.schemas import ShiftAssignmentsSave, WorkerAssignmentItem
from app.services import shift_assignment_service

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
REQ_ID = uuid.uuid4()
WORKER_ID_1 = uuid.uuid4()
WORKER_ID_2 = uuid.uuid4()


def _make_assignment(
    *,
    assignment_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    requirement_id: uuid.UUID | None = None,
    worker_id: uuid.UUID | None = None,
    is_manual_override: bool = False,
) -> ShiftRequirementAssignment:
    """テスト用ShiftRequirementAssignmentオブジェクトを生成するヘルパー."""
    a = ShiftRequirementAssignment()
    a.id = assignment_id or uuid.uuid4()
    a.tenant_id = tenant_id
    a.requirement_id = requirement_id or REQ_ID
    a.worker_id = worker_id or WORKER_ID_1
    a.is_manual_override = is_manual_override
    a.created_at = datetime(2026, 1, 1)
    return a


def _make_requirement(
    *,
    req_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
) -> ShiftRequirement:
    """テスト用ShiftRequirementオブジェクトを生成するヘルパー."""
    r = ShiftRequirement()
    r.id = req_id or REQ_ID
    r.tenant_id = tenant_id
    r.department_id = uuid.uuid4()
    r.shift_date = datetime(2099, 12, 31).date()
    r.required_headcount = 2
    r.created_at = datetime(2026, 1, 1)
    r.updated_at = datetime(2026, 1, 1)
    return r


def _make_worker(
    *,
    worker_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
) -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = worker_id or WORKER_ID_1
    w.tenant_id = tenant_id
    w.name = "テストワーカー"
    w.department_id = uuid.uuid4()
    w.skill_rank = "rank_a"
    w.is_special = False
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


# ---------------------------------------------------------------------------
# upsert_assignments
# ---------------------------------------------------------------------------


class TestUpsertAssignments:
    """upsert_assignments の正常系・異常系テスト."""

    def test_upsert_assignments_creates_new(self) -> None:
        """正常系: 新しいアサインを作成して返す."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": []})
        session.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())

        data = ShiftAssignmentsSave(
            worker_ids=[WORKER_ID_1, WORKER_ID_2],
            is_manual_override=False,
        )

        req = _make_requirement()
        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            with patch.object(shift_assignment_service, "_validate_workers"):
                result = shift_assignment_service.upsert_assignments(
                    session, TENANT_ID, REQ_ID, data
                )

        session.commit.assert_called_once()
        assert session.add.call_count == 2
        assert len(result) == 2
        assert all(isinstance(r, WorkerAssignmentItem) for r in result)

    def test_upsert_assignments_with_override_flag(self) -> None:
        """正常系: is_manual_override=True でアサインを作成する."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": []})
        session.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())

        data = ShiftAssignmentsSave(
            worker_ids=[WORKER_ID_1],
            is_manual_override=True,
        )

        req = _make_requirement()
        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            with patch.object(shift_assignment_service, "_validate_workers"):
                shift_assignment_service.upsert_assignments(
                    session, TENANT_ID, REQ_ID, data
                )

        # セッションにaddされたアサインオブジェクトを確認
        added_assignments = [
            call_args[0][0]
            for call_args in session.add.call_args_list
            if isinstance(call_args[0][0], ShiftRequirementAssignment)
        ]
        assert len(added_assignments) == 1
        assert added_assignments[0].is_manual_override is True

    def test_upsert_assignments_empty_clears_all(self) -> None:
        """正常系: worker_ids が空の場合、既存アサインを全削除して空リストを返す."""
        existing = [
            _make_assignment(worker_id=WORKER_ID_1),
            _make_assignment(worker_id=WORKER_ID_2),
        ]
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": existing})

        data = ShiftAssignmentsSave(worker_ids=[], is_manual_override=False)

        req = _make_requirement()
        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            with patch.object(shift_assignment_service, "_validate_workers"):
                result = shift_assignment_service.upsert_assignments(
                    session, TENANT_ID, REQ_ID, data
                )

        assert result == []
        assert session.delete.call_count == 2
        session.add.assert_not_called()

    def test_upsert_assignments_replaces_existing(self) -> None:
        """正常系: 既存アサインを削除してから新規アサインを追加する."""
        existing = [_make_assignment(worker_id=WORKER_ID_1)]
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": existing})
        session.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())

        data = ShiftAssignmentsSave(
            worker_ids=[WORKER_ID_2],
            is_manual_override=False,
        )

        req = _make_requirement()
        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            with patch.object(shift_assignment_service, "_validate_workers"):
                with patch.object(
                    shift_assignment_service, "_validate_business_rules"
                ):
                    shift_assignment_service.upsert_assignments(
                        session, TENANT_ID, REQ_ID, data
                    )

        session.delete.assert_called_once_with(existing[0])
        session.add.assert_called_once()

    def test_upsert_assignments_requirement_not_found_raises_404(self) -> None:
        """異常系: ShiftRequirementが存在しない場合、404例外を送出する."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"first.return_value": None})

        data = ShiftAssignmentsSave(worker_ids=[WORKER_ID_1], is_manual_override=False)

        with pytest.raises(HTTPException) as exc_info:
            shift_assignment_service.upsert_assignments(
                session, TENANT_ID, uuid.uuid4(), data
            )

        assert exc_info.value.status_code == 404

    def test_upsert_assignments_worker_not_found_raises_404(self) -> None:
        """異常系: Workerが存在しない場合、404例外を送出する."""
        session = MagicMock()
        req = _make_requirement()

        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            session.exec.return_value = MagicMock(**{"all.return_value": []})

            data = ShiftAssignmentsSave(
                worker_ids=[uuid.uuid4()],  # 存在しないワーカー
                is_manual_override=False,
            )

            with pytest.raises(HTTPException) as exc_info:
                shift_assignment_service.upsert_assignments(
                    session, TENANT_ID, REQ_ID, data
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# list_assignments_for_requirement
# ---------------------------------------------------------------------------


class TestListAssignmentsForRequirement:
    """list_assignments_for_requirement の正常系・異常系テスト."""

    def test_list_assignments_returns_items(self) -> None:
        """正常系: アサイン一覧を返す."""
        assignments = [
            _make_assignment(worker_id=WORKER_ID_1),
            _make_assignment(worker_id=WORKER_ID_2),
        ]
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": assignments})

        req = _make_requirement()
        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            result = shift_assignment_service.list_assignments_for_requirement(
                session, TENANT_ID, REQ_ID
            )

        assert len(result) == 2
        assert all(isinstance(r, WorkerAssignmentItem) for r in result)

    def test_list_assignments_empty_returns_empty_list(self) -> None:
        """正常系: アサインが存在しない場合、空リストを返す."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": []})

        req = _make_requirement()
        with patch.object(
            shift_assignment_service,
            "_validate_requirement",
            return_value=req,
        ):
            result = shift_assignment_service.list_assignments_for_requirement(
                session, TENANT_ID, REQ_ID
            )

        assert result == []

    def test_list_assignments_requirement_not_found_raises_404(self) -> None:
        """異常系: ShiftRequirementが存在しない場合、404例外を送出する."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"first.return_value": None})

        with pytest.raises(HTTPException) as exc_info:
            shift_assignment_service.list_assignments_for_requirement(
                session, TENANT_ID, uuid.uuid4()
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# _validate_business_rules（ビジネスルール検証）
# ---------------------------------------------------------------------------


class TestValidateBusinessRules:
    """_validate_business_rules の正常系・異常系テスト."""

    def test_skips_validation_when_worker_ids_empty(self) -> None:
        """正常系: worker_ids が空の場合、検証をスキップして例外を送出しない."""
        session = MagicMock()
        req = _make_requirement()
        # Should not raise
        shift_assignment_service._validate_business_rules(
            session, TENANT_ID, req, []
        )

    def test_skips_validation_when_manual_override(self) -> None:
        """正常系: is_manual_override=True の場合、_validate_business_rules は呼ばれない."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": []})
        session.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())

        data = ShiftAssignmentsSave(
            worker_ids=[WORKER_ID_1],
            is_manual_override=True,
        )

        req = _make_requirement()
        with patch.object(
            shift_assignment_service, "_validate_requirement", return_value=req
        ):
            with patch.object(shift_assignment_service, "_validate_workers"):
                with patch.object(
                    shift_assignment_service,
                    "_validate_business_rules",
                ) as mock_validate:
                    shift_assignment_service.upsert_assignments(
                        session, TENANT_ID, REQ_ID, data
                    )

        mock_validate.assert_not_called()

    def test_raises_400_when_violations_found(self) -> None:
        """異常系: ビジネスルール違反がある場合、400例外を送出する."""
        from app.models.rule_schemas import ValidationViolationItem

        session = MagicMock()
        req = _make_requirement()

        violation = ValidationViolationItem(
            code="WORK_INTERVAL",
            severity="error",
            message="テストワーカー の勤務間隔が中9日を満たしていません",
            worker_ids=[str(WORKER_ID_1)],
        )

        worker = _make_worker(worker_id=WORKER_ID_1)
        session.exec.return_value = MagicMock(**{"all.return_value": [worker]})

        with patch(
            "app.services.shift_validation_service.validate_shift_assignments",
            return_value=[violation],
        ):
            with pytest.raises(HTTPException) as exc_info:
                shift_assignment_service._validate_business_rules(
                    session, TENANT_ID, req, [WORKER_ID_1]
                )

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert "violations" in detail
        assert len(detail["violations"]) == 1
        assert detail["violations"][0]["code"] == "WORK_INTERVAL"

    def test_no_exception_when_no_violations(self) -> None:
        """正常系: ビジネスルール違反がない場合、例外を送出しない."""
        session = MagicMock()
        req = _make_requirement()

        worker = _make_worker(worker_id=WORKER_ID_1)
        session.exec.return_value = MagicMock(**{"all.return_value": [worker]})

        with patch(
            "app.services.shift_validation_service.validate_shift_assignments",
            return_value=[],
        ):
            # Should not raise
            shift_assignment_service._validate_business_rules(
                session, TENANT_ID, req, [WORKER_ID_1]
            )

    def test_warnings_do_not_trigger_400(self) -> None:
        """正常系: warningのみの場合は400エラーにならない."""
        from app.models.rule_schemas import ValidationViolationItem

        session = MagicMock()
        req = _make_requirement()

        warning = ValidationViolationItem(
            code="CONSECUTIVE_HOLIDAYS",
            severity="warning",
            message="連続して休日枠にアサインされています",
            worker_ids=[str(WORKER_ID_1)],
        )

        worker = _make_worker(worker_id=WORKER_ID_1)
        session.exec.return_value = MagicMock(**{"all.return_value": [worker]})

        with patch(
            "app.services.shift_validation_service.validate_shift_assignments",
            return_value=[warning],
        ):
            # Should not raise (warnings don't block save)
            shift_assignment_service._validate_business_rules(
                session, TENANT_ID, req, [WORKER_ID_1]
            )
