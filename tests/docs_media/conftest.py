"""Shared fixtures for docs media validation tests."""

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_SITE_DIR = REPO_ROOT / "docs-site"
DOCS_DIR = DOCS_SITE_DIR / "docs"
STATIC_IMG_DIR = DOCS_SITE_DIR / "static" / "img"
GUIDES_IMG_DIR = STATIC_IMG_DIR / "guides"
GIFS_DIR = STATIC_IMG_DIR / "gifs"
VIDEO_DIR = DOCS_SITE_DIR / "static" / "video"


@pytest.fixture
def docs_dir():
    return DOCS_DIR


@pytest.fixture
def static_img_dir():
    return STATIC_IMG_DIR


@pytest.fixture
def guides_img_dir():
    return GUIDES_IMG_DIR
