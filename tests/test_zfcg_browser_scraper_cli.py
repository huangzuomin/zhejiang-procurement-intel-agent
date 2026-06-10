import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_zfcg_browser_scraper_exposes_two_target_columns() -> None:
    result = subprocess.run(
        ["node", "scripts/zfcg_browser_scraper.js", "--print-targets"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    targets = json.loads(result.stdout)

    assert [target["key"] for target in targets] == ["intention", "bid"]
    assert targets[0]["path"] == "政府采购公告 > 采购意向 > 采购意向公开"
    assert targets[0]["category_code"] == "110-600268"
    assert targets[1]["path"] == "政府采购公告 > 采购项目公告 > 招标公告"
    assert targets[1]["category_code"] == "110-684034"


def test_zfcg_browser_scraper_prefers_detail_buyer_over_author() -> None:
    js = """
    const scraper = require('./scripts/zfcg_browser_scraper.js');
    const text = '向采购人和采购代理机构提出质疑。 七、对本次采购提出询问、质疑、投诉，请按以下方式联系 1.采购人信息 名 称： 余姚市环境卫生管理中心 地 址： 余姚市谭家岭西路39号 项目联系人（询问）： 马先生 2.采购代理机构信息 名 称： 宁波求真工程设计咨询有限公司';
    console.log(scraper.extractBuyer(text));
    """
    result = subprocess.run(
        ["node", "-e", js],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "余姚市环境卫生管理中心"


def test_zfcg_browser_scraper_reads_colon_after_budget_unit_header() -> None:
    js = """
    const scraper = require('./scripts/zfcg_browser_scraper.js');
    const text = '项目基本情况 预算金额（元）： 3000000 最高限价（元）： 3000000 采购需求';
    console.log(scraper.parseBudget(text));
    """
    result = subprocess.run(
        ["node", "-e", js],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "3000000"


def test_zfcg_browser_scraper_accepts_known_urls_file() -> None:
    js = """
    const scraper = require('./scripts/zfcg_browser_scraper.js');
    const args = scraper.parseArgs(['--known-urls-file', 'data/known_urls.txt', '--no-details']);
    console.log(JSON.stringify({ knownUrlsFile: args.knownUrlsFile, details: args.details }));
    """
    result = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)

    payload = json.loads(result.stdout)
    assert payload["knownUrlsFile"] == "data/known_urls.txt"
    assert payload["details"] is False


def test_zfcg_browser_scraper_skips_detail_for_known_urls() -> None:
    js = """
    const scraper = require('./scripts/zfcg_browser_scraper.js');
    const item = { detail_url: 'https://zfcg.czt.zj.gov.cn/site/detail?articleId=known' };
    const args = { details: true, detailLimit: 10 };
    const knownUrls = new Set([item.detail_url]);
    console.log(scraper.shouldFetchDetail(item, args, knownUrls, 0));
    """
    result = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)

    assert result.stdout.strip() == "false"
