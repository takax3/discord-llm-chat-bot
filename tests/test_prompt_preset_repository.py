from __future__ import annotations

import sqlite3

import pytest

from discordbot.domain.prompt_preset import PromptPreset
from discordbot.storage.database import CREATE_PROMPT_PRESETS_TABLE_SQL
from discordbot.storage.prompt_preset_repository import PromptPresetRepository


@pytest.fixture()
def repo() -> PromptPresetRepository:
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_PROMPT_PRESETS_TABLE_SQL)
    conn.commit()
    return PromptPresetRepository(connection=conn)


def test_save_and_get_by_name(repo: PromptPresetRepository) -> None:
    preset = PromptPreset(guild_id=1, name="hero", prompt="You are a hero.")
    repo.save(preset)
    result = repo.get_by_name(guild_id=1, name="hero")
    assert result == preset


def test_get_by_name_not_found(repo: PromptPresetRepository) -> None:
    assert repo.get_by_name(guild_id=1, name="missing") is None


def test_save_upsert(repo: PromptPresetRepository) -> None:
    repo.save(PromptPreset(guild_id=1, name="hero", prompt="v1"))
    repo.save(PromptPreset(guild_id=1, name="hero", prompt="v2"))
    result = repo.get_by_name(guild_id=1, name="hero")
    assert result is not None
    assert result.prompt == "v2"


def test_delete_existing(repo: PromptPresetRepository) -> None:
    repo.save(PromptPreset(guild_id=1, name="hero", prompt="You are a hero."))
    deleted = repo.delete(guild_id=1, name="hero")
    assert deleted is True
    assert repo.get_by_name(guild_id=1, name="hero") is None


def test_delete_nonexistent(repo: PromptPresetRepository) -> None:
    deleted = repo.delete(guild_id=1, name="ghost")
    assert deleted is False


def test_list_presets_empty(repo: PromptPresetRepository) -> None:
    assert repo.list_presets(guild_id=1) == []


def test_list_presets_sorted(repo: PromptPresetRepository) -> None:
    repo.save(PromptPreset(guild_id=1, name="zebra", prompt="z"))
    repo.save(PromptPreset(guild_id=1, name="alpha", prompt="a"))
    repo.save(PromptPreset(guild_id=1, name="mango", prompt="m"))
    names = [p.name for p in repo.list_presets(guild_id=1)]
    assert names == ["alpha", "mango", "zebra"]


def test_list_presets_isolated_by_guild(repo: PromptPresetRepository) -> None:
    repo.save(PromptPreset(guild_id=1, name="hero", prompt="guild 1"))
    repo.save(PromptPreset(guild_id=2, name="hero", prompt="guild 2"))
    assert len(repo.list_presets(guild_id=1)) == 1
    assert repo.list_presets(guild_id=1)[0].prompt == "guild 1"
    assert len(repo.list_presets(guild_id=2)) == 1
    assert repo.list_presets(guild_id=2)[0].prompt == "guild 2"


def test_get_by_name_guild_isolated(repo: PromptPresetRepository) -> None:
    repo.save(PromptPreset(guild_id=1, name="hero", prompt="guild 1"))
    assert repo.get_by_name(guild_id=2, name="hero") is None
