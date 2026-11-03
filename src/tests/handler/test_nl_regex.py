import pytest

from nonebot.consts import REGEX_MATCHED

ranking_pattern = r"^看看(.*)?榜\s*(.*)?$"
illust_pattern = r"^看看图\s*([1-9][0-9]*)$"


class FakeEvent:
    def __init__(self, text: str):
        self.text = text

    def get_plaintext(self) -> str:
        return self.text


@pytest.fixture
def checker_cls(nonebug_init, conf_env):
    from nonebot_plugin_pixivbot.handler.utils import NLRegexChecker
    return NLRegexChecker


@pytest.mark.asyncio
@pytest.mark.parametrize("text", [
    "看看周榜",
    "##看看周榜",
    "## 看看周榜",
])
async def test_ranking_with_optional_command_start(checker_cls, text):
    checker = checker_cls(ranking_pattern, command_starts={"##"})
    state = {}

    assert await checker(FakeEvent(text), state)
    assert state[REGEX_MATCHED].groups() == ("周", "")


@pytest.mark.asyncio
@pytest.mark.parametrize("text", [
    "看看图114514",
    "##看看图114514",
    "## 看看图114514",
])
async def test_group_index_is_unchanged(checker_cls, text):
    checker = checker_cls(illust_pattern, command_starts={"##"})
    state = {}

    assert await checker(FakeEvent(text), state)
    assert state[REGEX_MATCHED].group(1) == "114514"


@pytest.mark.asyncio
async def test_command_is_not_treated_as_natural_language(checker_cls):
    checker = checker_cls(ranking_pattern, command_starts={"##"})

    assert not await checker(FakeEvent("##pixivbot help"), {})
    assert not await checker(FakeEvent("随便说点什么"), {})


@pytest.mark.asyncio
async def test_prefix_that_is_also_a_word_prefix(checker_cls):
    # 先匹配原文，避免把“看看周榜”截成“看周榜”
    checker = checker_cls(ranking_pattern, command_starts={"看"})

    assert await checker(FakeEvent("看看周榜"), {})


@pytest.mark.asyncio
async def test_multiple_prefixes_and_empty_prefix(checker_cls):
    checker = checker_cls(ranking_pattern, command_starts={"", "#", "##"})

    assert await checker(FakeEvent("##看看周榜"), {})
    assert await checker(FakeEvent("看看周榜"), {})


@pytest.mark.asyncio
async def test_plain_text_with_surrounding_whitespace(checker_cls):
    checker = checker_cls(ranking_pattern, command_starts={"##"})

    assert await checker(FakeEvent("  ## 看看周榜  "), {})


@pytest.mark.asyncio
async def test_reads_command_start_from_driver(checker_cls):
    # nonebug 默认 COMMAND_START 为 {"/"}
    checker = checker_cls(ranking_pattern)

    assert await checker(FakeEvent("看看周榜"), {})
    assert await checker(FakeEvent("/看看周榜"), {})
