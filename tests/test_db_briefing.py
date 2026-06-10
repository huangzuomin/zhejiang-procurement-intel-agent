from procurement_intel.classifier import classify_notice
from procurement_intel.db_briefing import build_brief_from_db
from procurement_intel.models import Notice
from procurement_intel.scorer import score_notice
from procurement_intel.storage import SQLiteStore

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_am_brief_reads_sqlite_and_omits_d_noise(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    store = SQLiteStore(db_path)
    store.initialize()
    _seed_card(store, _notice("门户网站建设项目公开招标公告", "门户网站建设、内容管理和运维服务。", "bid"))
    _seed_card(store, _notice("融媒体建设项目采购意向", "融媒体建设、新媒体内容运营。", "intention"))
    _seed_card(store, _notice("教学一体机采购公告", "教学一体机和教室设备。", "bid"))

    message = build_brief_from_db(db_path, today="2026-06-10", mode="am")

    assert "浙江政采情报日报" in message
    assert "A 1 / B 1 / C 0 / D 1" in message
    assert "门户网站建设项目公开招标公告" in message
    assert "融媒体建设项目采购意向" in message
    assert "教学一体机采购公告" not in message


def test_am_brief_uses_dingtalk_markdown_links_and_action_sections(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    store = SQLiteStore(db_path)
    store.initialize()
    _seed_card(store, _notice("门户网站建设项目公开招标公告", "门户网站建设、内容管理和运维服务。", "bid"))
    for index in range(1, 8):
        _seed_card(store, _notice(f"融媒体建设项目采购意向{index}", "融媒体建设、新媒体内容运营。", "intention"))

    message = build_brief_from_db(db_path, today="2026-06-10", mode="am")

    assert "今日结论:" in message
    assert "A类｜立即响应" in message
    assert "B类｜提前跟进" in message
    assert "今日建议:" in message
    assert "[详情](https://zfcg.czt.zj.gov.cn/site/detail?articleId=" in message
    assert "另有 2 条 B 类线索已压缩" in message
    assert "融媒体建设项目采购意向6" not in message
    assert _bare_urls_outside_markdown_links(message) == []


def test_pm_brief_only_includes_unpushed_focus_items(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    store = SQLiteStore(db_path)
    store.initialize()
    morning_id = _seed_card(store, _notice("上午已推送A类项目", "门户网站建设服务。", "bid"))
    _seed_card(store, _notice("下午新增B类项目", "融媒体建设、新媒体内容运营。", "intention"))
    store.record_push_event(
        notice_id=morning_id,
        brief_date="2026-06-10",
        brief_mode="am",
        status="success",
        pushed_at="2026-06-10T09:00:00",
    )

    message = build_brief_from_db(db_path, today="2026-06-10", mode="pm", since_brief="am")

    assert "浙江政采情报增量" in message
    assert "下午新增" in message
    assert "下午新增B类项目" in message
    assert "上午已推送A类项目" not in message


def test_pm_brief_without_new_focus_is_status_only(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    store = SQLiteStore(db_path)
    store.initialize()
    morning_id = _seed_card(store, _notice("上午已推送A类项目", "门户网站建设服务。", "bid"))
    store.record_push_event(
        notice_id=morning_id,
        brief_date="2026-06-10",
        brief_mode="am",
        status="success",
        pushed_at="2026-06-10T09:00:00",
    )

    message = build_brief_from_db(db_path, today="2026-06-10", mode="pm", since_brief="am")

    assert "下午无新增重点机会" in message
    assert "上午已推送A类项目" not in message


def test_run_brief_from_db_cli_writes_outputs(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    output_dir = tmp_path / "brief"
    store = SQLiteStore(db_path)
    store.initialize()
    _seed_card(store, _notice("门户网站建设项目公开招标公告", "门户网站建设服务。", "bid"))

    result = subprocess.run(
        [
            "python3",
            "scripts/run_brief_from_db.py",
            "--mode",
            "am",
            "--today",
            "2026-06-10",
            "--db-path",
            str(db_path),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert Path(payload["paths"]["daily_brief"]).exists()
    assert Path(payload["paths"]["summary"]).exists()
    assert "门户网站建设项目公开招标公告" in Path(payload["paths"]["daily_brief"]).read_text(encoding="utf-8")


def test_run_brief_from_db_cli_records_am_push_success_for_focus_items(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    am_output_dir = tmp_path / "am"
    pm_output_dir = tmp_path / "pm"
    store = SQLiteStore(db_path)
    store.initialize()
    _seed_card(store, _notice("门户网站建设项目公开招标公告", "门户网站建设服务。", "bid"))

    am_result = subprocess.run(
        [
            "python3",
            "scripts/run_brief_from_db.py",
            "--mode",
            "am",
            "--today",
            "2026-06-10",
            "--db-path",
            str(db_path),
            "--output-dir",
            str(am_output_dir),
            "--record-push-success",
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    am_payload = json.loads(am_result.stdout)
    assert am_payload["recorded_push_count"] == 1

    pm_result = subprocess.run(
        [
            "python3",
            "scripts/run_brief_from_db.py",
            "--mode",
            "pm",
            "--today",
            "2026-06-10",
            "--since-brief",
            "am",
            "--db-path",
            str(db_path),
            "--output-dir",
            str(pm_output_dir),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    pm_payload = json.loads(pm_result.stdout)
    assert Path(pm_payload["paths"]["daily_brief"]).exists()
    pm_brief = Path(pm_payload["paths"]["daily_brief"]).read_text(encoding="utf-8")
    assert "下午无新增重点机会" in pm_brief
    assert "门户网站建设项目公开招标公告" not in pm_brief


def _notice(title: str, content: str, source_column: str) -> Notice:
    return Notice(
        title=title,
        url=f"https://zfcg.czt.zj.gov.cn/site/detail?articleId={title}",
        notice_type="招标公告" if source_column == "bid" else "采购意向公开",
        publish_date="2026-06-10",
        region="浙江",
        buyer="浙江某单位",
        budget=600000,
        deadline="2026-06-30" if source_column == "bid" else None,
        content=content,
        source_column=source_column,
    )


def _seed_card(store: SQLiteStore, notice: Notice) -> int:
    notice_id = store.upsert_notice(notice, fetch_run_id="seed", seen_at="2026-06-10T08:00:00")
    card = score_notice(notice, classify_notice(notice), today="2026-06-10")
    store.upsert_opportunity_card(notice_id, card, scored_at="2026-06-10T08:00:00")
    return notice_id


def _bare_urls_outside_markdown_links(message: str) -> list[str]:
    without_markdown_links = re.sub(r"\[[^\]]+\]\(https?://[^)]+\)", "", message)
    return re.findall(r"https?://\S+", without_markdown_links)
