"""Unit tests to cover the DB module."""

import os

import pytest
from pgosm_flex import helpers
from pgosm_flex import main as pgosm_flex

pgosm_flex.setup_logger(debug=True)


def test_get_today_returns_str():
    expected = str
    actual = type(helpers.get_today())
    assert expected == actual


def test_verify_checksum_returns_none_when_valid_md5():
    txt_file = "checksum-test.txt"
    md5_file = f"{txt_file}.md5"

    path = os.getcwd()
    txt_content = "this is a test"
    md5_content = f"54b0c58c7ce9f2a8b551351102ee0938  {txt_file}"

    with open(txt_file, "w") as f:
        f.write(txt_content)

    with open(md5_file, "w") as f:
        f.write(md5_content)

    expected = None
    actual = helpers.verify_checksum(md5_file=md5_file, path=path)
    assert expected == actual


def test_verify_checksum_raises_SystemExit_invalid_md5():
    txt_file = "checksum-test.txt"
    md5_file = f"{txt_file}.md5"

    path = os.getcwd()
    txt_content = "data has been changed oh no"
    md5_content = f"54b0c58c7ce9f2a8b551351102ee0938  {txt_file}"

    with open(txt_file, "w") as f:
        f.write(txt_content)

    with open(md5_file, "w") as f:
        f.write(md5_content)

    with pytest.raises(SystemExit):
        helpers.verify_checksum(md5_file=md5_file, path=path)
