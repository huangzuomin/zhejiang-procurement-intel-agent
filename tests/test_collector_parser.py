from procurement_intel.briefing import render_daily_brief
from procurement_intel.classifier import classify_notice
from procurement_intel.collector import DEFAULT_SOURCE_URLS, TARGET_MONITOR_URL, parse_notice_links
from procurement_intel.parser import parse_notice_detail
from procurement_intel.scorer import score_notice


LIST_HTML = """
<html>
  <body>
    <ul>
      <li><a href="/project/zcyNotice_view.aspx?Id=abc123" title="浙江某单位门户网站建设项目公开招标公告">公告一</a></li>
      <li><a href="https://zfcg.czt.zj.gov.cn/site/detail?articleId=def456">政务新媒体运营服务采购意向</a></li>
      <li><a href="/site/home">首页</a></li>
    </ul>
  </body>
</html>
"""


DETAIL_HTML = """
<html>
  <head>
    <title>浙江某单位门户网站建设项目公开招标公告</title>
    <meta name="PubDate" content="2026-06-08" />
  </head>
  <body>
    <h2>浙江某单位门户网站建设项目公开招标公告</h2>
    <div class="vF_detail_content">
      <p>发布时间：2026-06-08</p>
      <p>采购人信息 名称：浙江某单位</p>
      <p>预算金额：120.5万元</p>
      <p>提交投标文件截止时间：2026年06月30日 09:30</p>
      <p>采购需求：门户网站建设、专题页面设计、内容管理和一年运维服务。</p>
    </div>
  </body>
</html>
"""


def test_parses_public_notice_links_from_list_html() -> None:
    links = parse_notice_links(LIST_HTML, "https://zfcg.czt.zj.gov.cn/site/category", limit=10)

    assert len(links) == 2
    assert links[0].title == "浙江某单位门户网站建设项目公开招标公告"
    assert links[0].url == "https://zfcg.czt.zj.gov.cn/project/zcyNotice_view.aspx?Id=abc123"
    assert links[1].title == "政务新媒体运营服务采购意向"


def test_default_source_is_target_monitoring_site() -> None:
    assert DEFAULT_SOURCE_URLS[0] == TARGET_MONITOR_URL
    assert TARGET_MONITOR_URL == "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement"


def test_parses_notice_detail_into_notice_model() -> None:
    notice = parse_notice_detail(
        DETAIL_HTML,
        url="https://zfcg.czt.zj.gov.cn/project/zcyNotice_view.aspx?Id=abc123",
        fallback_title="列表页标题",
        notice_type="招标公告",
    )

    assert notice.title == "浙江某单位门户网站建设项目公开招标公告"
    assert notice.buyer == "浙江某单位"
    assert notice.budget == 1205000
    assert notice.deadline == "2026-06-30"
    assert notice.publish_date == "2026-06-08"
    assert "门户网站建设" in notice.content


def test_parse_notice_detail_ignores_style_and_reads_budget_unit_header() -> None:
    html = """
    <html>
      <body>
        <style>
          #template-center-mark .selectTdClass{background-color:#edf5fa !important}
          #template-center-mark table{border-collapse:collapse}
        </style>
        <div id="template-center-mark">
          <p>采购单位 杭州市余杭区中泰幼儿园</p>
          <p>采购项目名称 中泰幼儿园大型玩具及户外游戏材料采购</p>
          <p>预算金额（元）： 700000.00</p>
          <p>采购需求概况 标的名称：中泰幼儿园大型玩具及户外游戏材料采购</p>
        </div>
      </body>
    </html>
    """

    notice = parse_notice_detail(
        html,
        url="https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
        fallback_title="杭州市余杭区中泰幼儿园2026年6月政府采购意向",
    )

    assert "selectTdClass" not in notice.content
    assert notice.buyer == "杭州市余杭区中泰幼儿园"
    assert notice.budget == 700000


def test_fixture_notice_runs_through_intelligence_pipeline() -> None:
    notice = parse_notice_detail(
        DETAIL_HTML,
        url="https://zfcg.czt.zj.gov.cn/project/zcyNotice_view.aspx?Id=abc123",
        notice_type="招标公告",
    )

    classification = classify_notice(notice)
    card = score_notice(notice, classification, today="2026-06-08")
    brief = render_daily_brief("2026-06-08", [card], total_new_notices=1)

    assert classification.primary_category == "网站建设"
    assert card.opportunity_class == "A"
    assert "浙江某单位门户网站建设项目公开招标公告" in brief
