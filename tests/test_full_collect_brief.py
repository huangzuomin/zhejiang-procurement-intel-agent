import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full_collect_brief_is_dingtalk_readable_and_filters_deadline_noise() -> None:
    js = r"""
    const { generateBrief } = require('./scripts/full_collect_and_brief.js');
    const notices = [
      {
        title: '嘉兴市主城区旅游标识标牌提升项目公开招标公告',
        detail_url: 'https://zfcg.czt.zj.gov.cn/site/detail?articleId=a',
        opportunity_class: 'A',
        buyer: '嘉兴市南湖区文化和旅游局',
        budget: 800000,
        deadline: '2026-06-30',
        project_name: '嘉兴市主城区旅游标识标牌提升项目',
        classification_reasons: ['标识标牌', '宣传服务']
      },
      {
        title: '融媒体建设项目采购意向',
        detail_url: 'https://zfcg.czt.zj.gov.cn/site/detail?articleId=b',
        opportunity_class: 'B',
        buyer: '杭州城西科创服务中心',
        budget: 300000,
        deadline: null,
        project_name: '杭州城西科创大走廊融媒体建设项目',
        classification_reasons: ['融媒体', '新媒体']
      },
      {
        title: '教学一体机采购项目公开招标公告',
        detail_url: 'https://zfcg.czt.zj.gov.cn/site/detail?articleId=c',
        opportunity_class: 'D',
        buyer: '某学校',
        budget: 1000000,
        deadline: '2026-07-01',
        project_name: '教学一体机采购项目',
        classification_reasons: []
      }
    ];
    const brief = generateBrief({
      scrapePayload: { notices },
      intentionsCount: 1,
      bidsCount: 2,
      enrichedCount: 3,
      mode: 'am',
      today: '2026-06-10',
      newCount: 0,
      newNotices: []
    });
    console.log(brief);
    """
    result = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)
    brief = result.stdout

    assert "概览：共3条，详情3条，A 1 / B 1 / C 0 / D 1，A/B 2条" in brief
    assert "https://zfcg.czt.zj.gov.cn" not in brief
    assert "匹配：标识标牌、宣传服务" in brief
    assert "| 维度 | 数据 |" not in brief
    assert "教学一体机采购项目公开招标公告" not in brief
    assert "近期截止" in brief
    assert "嘉兴市主城区旅游标识标牌提升项目公开招标公告" in brief


def test_full_collect_brief_no_focus_mode_omits_d_class_items() -> None:
    js = r"""
    const { generateBrief } = require('./scripts/full_collect_and_brief.js');
    const notices = [
      { title: '幼儿园家具采购意向', opportunity_class: 'D', deadline: null, classification_reasons: [] },
      { title: '教学一体机采购公告', opportunity_class: 'D', deadline: '2026-07-01', classification_reasons: [] }
    ];
    const brief = generateBrief({
      scrapePayload: { notices },
      intentionsCount: 1,
      bidsCount: 1,
      enrichedCount: 2,
      mode: 'am',
      today: '2026-06-10',
      newCount: 0,
      newNotices: []
    });
    console.log(brief);
    """
    result = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)
    brief = result.stdout

    assert "今日无媒体/数字化重点机会" in brief
    assert "幼儿园家具采购意向" not in brief
    assert "教学一体机采购公告" not in brief
    assert "近期截止" not in brief


def test_pm_no_new_brief_does_not_repeat_morning_focus_items() -> None:
    js = r"""
    const { generateBrief } = require('./scripts/full_collect_and_brief.js');
    const notices = [
      { title: '上午已推送的A类项目', opportunity_class: 'A', buyer: '某采购人', budget: 800000, deadline: '2026-06-30', classification_reasons: ['宣传服务'] },
      { title: '上午已推送的B类项目', opportunity_class: 'B', buyer: '某采购人', budget: 300000, deadline: null, classification_reasons: ['融媒体'] }
    ];
    const brief = generateBrief({
      scrapePayload: { notices },
      intentionsCount: 1,
      bidsCount: 1,
      enrichedCount: 2,
      mode: 'pm',
      today: '2026-06-10',
      newCount: 0,
      newNotices: []
    });
    console.log(brief);
    """
    result = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)
    brief = result.stdout

    assert "下午无新增公告，今日数据不变" in brief
    assert "上午已推送的A类项目" not in brief
    assert "上午已推送的B类项目" not in brief
    assert "近期截止" not in brief
