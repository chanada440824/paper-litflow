"""parse_filename_metadata: 文件名元数据解析测试。"""

from paper_litflow.pdf_utils import parse_filename_metadata


def test_full_author_year_title():
    assert parse_filename_metadata("张三 - 2020 - 智能建筑研究.pdf") == (
        "张三",
        "2020",
        "智能建筑研究",
    )


def test_full_with_page_suffix():
    assert parse_filename_metadata("张三 - 2020 - 智能建筑研究_28-77.pdf") == (
        "张三",
        "2020",
        "智能建筑研究",
    )


def test_author_title_only():
    assert parse_filename_metadata("张三 - 智能建筑研究.pdf") == ("张三", "", "智能建筑研究")


def test_title_only():
    assert parse_filename_metadata("智能建筑研究.pdf") == ("", "", "智能建筑研究")


def test_extra_spaces_around_separators():
    assert parse_filename_metadata(" 张三  -  2021  -  协作学习研究.pdf") == (
        "张三",
        "2021",
        "协作学习研究",
    )


def test_latin_and_suffix_digits():
    assert parse_filename_metadata("（美）John Smith - 2022 - Learning Spaces_1-10.pdf") == (
        "（美）John Smith",
        "2022",
        "Learning Spaces",
    )