import json
import os
import tempfile
import zipfile

import numpy as np
import pytest

from anemoi.utils.checkpoints import _edit_metadata
from anemoi.utils.checkpoints import has_metadata
from anemoi.utils.checkpoints import load_metadata
from anemoi.utils.checkpoints import remove_metadata
from anemoi.utils.checkpoints import replace_metadata
from anemoi.utils.checkpoints import save_metadata


@pytest.fixture
def sample_checkpoint():
    """Create a sample PyTorch checkpoint file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        checkpoint_path = tmp.name

    # Create a mock PyTorch checkpoint structure
    with zipfile.ZipFile(checkpoint_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add some dummy model files
        zipf.writestr("model/data.pkl", b"fake pytorch data")
        zipf.writestr("model/tensors.pt", b"fake tensor data")
        zipf.writestr("model/version", b"3")

        # Add initial metadata
        metadata = {"version": "1.0", "model_info": {"layers": 10, "parameters": 1000000}}
        zipf.writestr("model/anemoi-metadata/metadata.json", json.dumps(metadata))

    yield checkpoint_path

    # Cleanup
    if os.path.exists(checkpoint_path):
        os.unlink(checkpoint_path)


@pytest.fixture
def sample_checkpoint_with_arrays():
    """Create a checkpoint with supporting arrays."""
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        checkpoint_path = tmp.name

    with zipfile.ZipFile(checkpoint_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("model/data.pkl", b"fake pytorch data")
        zipf.writestr("model/tensors.pt", b"fake tensor data")
        zipf.writestr("model/version", b"3")

        # Add metadata with supporting arrays
        metadata = {
            "version": "1.0",
            "supporting_arrays_paths": {
                "means": {"path": "model/anemoi-metadata/means.numpy", "shape": [10], "dtype": "float64"},
                "stds": {"path": "model/anemoi-metadata/stds.numpy", "shape": [10], "dtype": "float64"},
            },
        }
        zipf.writestr("model/anemoi-metadata/metadata.json", json.dumps(metadata))

        # Add supporting arrays
        means_array = np.random.random(10).astype(np.float64)
        stds_array = np.random.random(10).astype(np.float64)
        zipf.writestr("model/anemoi-metadata/means.numpy", means_array.tobytes())
        zipf.writestr("model/anemoi-metadata/stds.numpy", stds_array.tobytes())

    yield checkpoint_path, means_array, stds_array

    if os.path.exists(checkpoint_path):
        os.unlink(checkpoint_path)


class TestEditMetadata:
    """Test cases for _edit_metadata function."""

    def test_edit_metadata_basic_functionality(self, sample_checkpoint):
        """Test basic functionality of _edit_metadata."""
        original_metadata = load_metadata(sample_checkpoint, name="metadata.json")

        def update_callback(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
            data["test_field"] = "test_value"
            data["version"] = "2.0"
            with open(file_path, "w") as f:
                json.dump(data, f)

        _edit_metadata(sample_checkpoint, "metadata.json", update_callback)

        # Verify the metadata was updated
        updated_metadata = load_metadata(sample_checkpoint, name="metadata.json")
        assert updated_metadata["test_field"] == "test_value"
        assert updated_metadata["version"] == "2.0"
        assert updated_metadata["model_info"] == original_metadata["model_info"]

    def test_edit_metadata_with_supporting_arrays(self, sample_checkpoint):
        """Test _edit_metadata with supporting arrays."""
        new_means = np.array([1.0, 2.0, 3.0])
        new_stds = np.array([0.1, 0.2, 0.3])
        supporting_arrays = {"means": new_means, "stds": new_stds}

        def update_callback(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
            data["has_arrays"] = True
            with open(file_path, "w") as f:
                json.dump(data, f)

        _edit_metadata(sample_checkpoint, "metadata.json", update_callback, supporting_arrays)

        # Verify arrays were added
        with zipfile.ZipFile(sample_checkpoint, "r") as zipf:
            assert "model/anemoi-metadata/means.numpy" in zipf.namelist()
            assert "model/anemoi-metadata/stds.numpy" in zipf.namelist()

            # Verify array contents
            means_data = np.frombuffer(zipf.read("model/anemoi-metadata/means.numpy"), dtype=new_means.dtype)
            stds_data = np.frombuffer(zipf.read("model/anemoi-metadata/stds.numpy"), dtype=new_stds.dtype)

            np.testing.assert_array_equal(means_data, new_means)
            np.testing.assert_array_equal(stds_data, new_stds)

    def test_edit_metadata_preserves_other_files(self, sample_checkpoint):
        """Test that _edit_metadata preserves all other files in the ZIP."""
        with zipfile.ZipFile(sample_checkpoint, "r") as zipf:
            original_files = set(zipf.namelist())

        def dummy_callback(file_path):
            pass

        _edit_metadata(sample_checkpoint, "metadata.json", dummy_callback)

        with zipfile.ZipFile(sample_checkpoint, "r") as zipf:
            updated_files = set(zipf.namelist())

        # All original files should still be present
        assert original_files == updated_files

        # Verify non-metadata files are unchanged
        with zipfile.ZipFile(sample_checkpoint, "r") as zipf:
            assert zipf.read("model/data.pkl") == b"fake pytorch data"
            assert zipf.read("model/tensors.pt") == b"fake tensor data"
            assert zipf.read("model/version") == b"3"

    def test_edit_metadata_file_not_found(self, sample_checkpoint):
        """Test _edit_metadata raises error when target file not found."""

        def dummy_callback(file_path):
            pass

        with pytest.raises(ValueError, match="Could not find 'nonexistent.json'"):
            _edit_metadata(sample_checkpoint, "nonexistent.json", dummy_callback)

    def test_edit_metadata_callback_exception_handling(self, sample_checkpoint):
        """Test that callback exceptions are properly propagated."""

        def failing_callback(file_path):
            raise RuntimeError("Callback failed")

        with pytest.raises(RuntimeError, match="Callback failed"):
            _edit_metadata(sample_checkpoint, "metadata.json", failing_callback)

        # Original file should be unchanged
        original_metadata = {"version": "1.0", "model_info": {"layers": 10, "parameters": 1000000}}
        current_metadata = load_metadata(sample_checkpoint, name="metadata.json")
        assert current_metadata == original_metadata


class TestEditMetadataIntegration:
    """Integration tests with other checkpoint functions."""

    def test_replace_metadata_integration(self, sample_checkpoint):
        """Test that replace_metadata still works after optimization."""
        new_metadata = {"version": "2.0", "new_field": "new_value", "model_info": {"layers": 20, "parameters": 2000000}}

        replace_metadata(sample_checkpoint, new_metadata, name="metadata.json")

        loaded_metadata = load_metadata(sample_checkpoint, name="metadata.json")
        assert loaded_metadata == new_metadata

    def test_remove_metadata_integration(self, sample_checkpoint):
        """Test that remove_metadata still works after optimization."""
        assert has_metadata(sample_checkpoint, name="metadata.json")

        remove_metadata(sample_checkpoint, name="metadata.json")

        assert not has_metadata(sample_checkpoint, name="metadata.json")

    def test_metadata_with_arrays_roundtrip(self, sample_checkpoint):
        """Test complete roundtrip with supporting arrays."""
        # First remove existing metadata
        remove_metadata(sample_checkpoint, name="metadata.json")

        # Add metadata with arrays
        metadata = {"version": "1.0", "test": True}
        arrays = {"test_array": np.array([1, 2, 3, 4, 5])}

        save_metadata(sample_checkpoint, metadata, supporting_arrays=arrays, name="metadata.json")

        # Load and verify
        loaded_metadata, loaded_arrays = load_metadata(sample_checkpoint, supporting_arrays=True, name="metadata.json")
        assert loaded_metadata["test"] is True
        np.testing.assert_array_equal(loaded_arrays["test_array"], arrays["test_array"])

        # Edit with _edit_metadata
        def update_callback(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
            data["edited"] = True
            with open(file_path, "w") as f:
                json.dump(data, f)

        _edit_metadata(sample_checkpoint, "metadata.json", update_callback)

        # Verify edit preserved arrays
        final_metadata, final_arrays = load_metadata(sample_checkpoint, supporting_arrays=True, name="metadata.json")
        assert final_metadata["edited"] is True
        assert final_metadata["test"] is True
        np.testing.assert_array_equal(final_arrays["test_array"], arrays["test_array"])
