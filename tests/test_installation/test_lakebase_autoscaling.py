from types import SimpleNamespace

from databricks.sdk.errors import NotFound

from lakebase_autoscaling import (
    ensure_autoscaling_project,
    normalize_project_id,
    project_resource_names,
)


class Operation:
    def __init__(self, value):
        self.value = value

    def wait(self):
        return self.value


def endpoint(name):
    return SimpleNamespace(
        name=name,
        status=SimpleNamespace(
            hosts=SimpleNamespace(host="primary.example"),
            current_state="ACTIVE",
        ),
    )


def test_direct_project_creation_configures_autoscaling_and_scale_to_zero():
    project_name, branch_name, endpoint_name = project_resource_names(
        "Customer Meter"
    )
    captured = {}

    class Postgres:
        def get_project(self, name):
            assert name == project_name
            raise NotFound("missing")

        def create_project(self, **kwargs):
            captured.update(kwargs)
            return Operation(SimpleNamespace(name=project_name, uid="uid-1"))

        def get_endpoint(self, name):
            assert name == endpoint_name
            return endpoint(name)

    resources, created = ensure_autoscaling_project(
        SimpleNamespace(postgres=Postgres()),
        "Customer Meter",
        suspend_after_seconds=600,
    )

    spec = captured["project"].spec
    assert captured["project_id"] == "customer-meter"
    assert spec.pg_version == 17
    assert spec.enable_pg_native_login is True
    assert spec.default_endpoint_settings.autoscaling_limit_min_cu == 1.0
    assert spec.default_endpoint_settings.autoscaling_limit_max_cu == 16.0
    assert spec.default_endpoint_settings.no_suspension is None
    assert spec.default_endpoint_settings.suspend_timeout_duration.seconds == 600
    assert resources.branch_name == branch_name
    assert resources.endpoint_name == endpoint_name
    assert resources.host == "primary.example"
    assert created


def test_existing_direct_project_is_reused():
    project_name, _, endpoint_name = project_resource_names("lakemeter")

    class Postgres:
        def get_project(self, name):
            assert name == project_name
            return SimpleNamespace(name=name, uid="existing")

        def create_project(self, **_kwargs):
            raise AssertionError("existing project must not be recreated")

        def get_endpoint(self, name):
            return endpoint(name)

    resources, created = ensure_autoscaling_project(
        SimpleNamespace(postgres=Postgres()),
        "lakemeter",
    )

    assert resources.project_uid == "existing"
    assert resources.endpoint_name == endpoint_name
    assert not created


def test_project_ids_are_normalized_for_resource_paths():
    assert normalize_project_id("  My_Customer.Project  ") == "my-customer-project"

