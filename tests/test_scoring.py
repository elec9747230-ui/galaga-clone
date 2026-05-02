import pytest

from game.scoring import Scoring, load_highscore, save_highscore


def test_scoring_initial_state():
    s = Scoring()
    assert s.score == 0
    assert s.lives == 3
    assert s.wave == 1
    assert s.shots_fired == 0
    assert s.hits == 0
    assert s.enemies_killed == 0


def test_add_kill_normal():
    s = Scoring()
    s.add_kill("normal")
    assert s.score == 50
    assert s.enemies_killed == 1


def test_add_kill_dive():
    s = Scoring()
    s.add_kill("dive")
    assert s.score == 100


def test_add_kill_boss():
    s = Scoring()
    s.add_kill("boss")
    assert s.score == 150


def test_add_kill_bonus():
    s = Scoring()
    s.add_kill("bonus")
    assert s.score == 200


def test_add_kill_unknown_type_raises():
    s = Scoring()
    with pytest.raises(ValueError):
        s.add_kill("alien_overlord")


def test_lose_life_decrements():
    s = Scoring(lives=3)
    s.lose_life()
    assert s.lives == 2


def test_lose_life_clamps_at_zero():
    s = Scoring(lives=0)
    s.lose_life()
    assert s.lives == 0


def test_gain_life_increments():
    s = Scoring(lives=3)
    s.gain_life()
    assert s.lives == 4


def test_add_shot_increments():
    s = Scoring()
    s.add_shot()
    s.add_shot()
    assert s.shots_fired == 2


def test_accuracy_with_zero_shots():
    s = Scoring()
    assert s.accuracy() == 0.0


def test_accuracy_normal():
    s = Scoring(shots_fired=10, hits=3)
    assert s.accuracy() == pytest.approx(0.30)


def test_save_and_load_highscore(tmp_path):
    path = tmp_path / "hs.json"
    save_highscore(12345, path)
    assert load_highscore(path) == 12345


def test_load_highscore_missing_file_returns_zero(tmp_path):
    assert load_highscore(tmp_path / "nope.json") == 0


def test_load_highscore_corrupt_file_returns_zero(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json")
    assert load_highscore(path) == 0
