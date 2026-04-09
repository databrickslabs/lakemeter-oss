"""Test that photon multiplier fallback to 2.0 emits a warning."""
import logging
import pytest
from unittest.mock import patch
from app.routes.export.pricing import _get_photon_multiplier


class TestPhotonMultiplierWarning:
    def test_fallback_emits_warning(self, caplog):
        """When photon multiplier is not found, a warning should be logged."""
        with patch('app.routes.export.pricing.DBU_MULTIPLIERS', {}):
            with caplog.at_level(logging.WARNING, logger='app.routes.export.pricing'):
                result = _get_photon_multiplier('aws', 'JOBS_COMPUTE')
                assert result == 2.0
                assert 'Photon multiplier not found' in caplog.text
                assert 'aws:JOBS_COMPUTE:photon' in caplog.text

    def test_found_no_warning(self, caplog):
        """When photon multiplier is found, no warning should be logged."""
        mock_data = {'aws:JOBS_COMPUTE:photon': {'multiplier': 2.5}}
        with patch('app.routes.export.pricing.DBU_MULTIPLIERS', mock_data):
            with caplog.at_level(logging.WARNING, logger='app.routes.export.pricing'):
                result = _get_photon_multiplier('aws', 'JOBS_COMPUTE')
                assert result == 2.5
                assert 'Photon multiplier not found' not in caplog.text
