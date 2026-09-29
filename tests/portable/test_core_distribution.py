"""Exercise actual core archives, provenance, and SDK import compatibility."""

import base64
import csv
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import textwrap
import zipfile
from email.parser import BytesParser
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def run_python(code, *args, cwd, no_site=True):
    flags = ["-E", "-B", "-I"] + (["-S"] if no_site else [])
    result = subprocess.run(
        [sys.executable, *flags, "-c", textwrap.dedent(code), *map(str, args)],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture(scope="module")
def archives(tmp_path_factory):
    temporary = tmp_path_factory.mktemp("core-distribution")
    tracked = subprocess.check_output(
        ["git", "ls-files", "*egg-info*"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    before = {name: (ROOT / name).read_bytes() for name in tracked}
    result = subprocess.run(
        [
            sys.executable,
            "-E",
            "-B",
            str(ROOT / "scripts/build_core_distribution.py"),
            "--out-dir",
            str(temporary / "artifacts"),
        ],
        cwd=temporary,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert before == {name: (ROOT / name).read_bytes() for name in tracked}
    assert not list((ROOT / "packages/usmsb-core").rglob("*.egg-info"))
    assert not (ROOT / "packages/usmsb-core/src").exists()
    wheels = list((temporary / "artifacts").glob("*.whl"))
    sdists = list((temporary / "artifacts").glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    return wheels[0], sdists[0]


def test_wheel_metadata_declares_only_opt_in_learning(archives):
    with zipfile.ZipFile(archives[0]) as wheel:
        metadata = BytesParser().parsebytes(
            wheel.read(
                next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
            )
        )
        assert metadata["Name"] == "usmsb-core"
        assert Version(metadata["Version"]).is_prerelease
        python = SpecifierSet(metadata["Requires-Python"])
        assert "3.14.0" in python and "3.14.7" in python
        assert "3.13.9" not in python and "3.15.0" not in python
        assert metadata["License-Expression"] == "MIT"
        assert metadata.get_all("License-File") == ["LICENSE"]
        assert metadata.get_all("Provides-Extra") == ["learning"]
        requirements = [Requirement(item) for item in metadata.get_all("Requires-Dist", [])]
        assert len(requirements) == 1
        requirement = requirements[0]
        assert requirement.name.lower() == "pydantic"
        assert requirement.marker is not None
        assert not requirement.marker.evaluate({"extra": ""})
        assert requirement.marker.evaluate({"extra": "learning"})
        assert "2.0" in requirement.specifier and "2.99" in requirement.specifier
        assert "1.10" not in requirement.specifier and "3.0" not in requirement.specifier


def test_wheel_provenance_matches_canonical_sources_and_license(archives):
    with zipfile.ZipFile(archives[0]) as wheel:
        names = wheel.namelist()
        assert all(name.startswith(("usmsb_core/", "usmsb_core-")) for name in names)
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
        manifest = json.loads(wheel.read("usmsb_core/MANIFEST.json"))
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
        assert manifest["revision"] == revision
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--", *manifest["source_paths"].values()],
            cwd=ROOT,
            text=True,
        ).splitlines()
        assert manifest["source_status"] == status
        assert manifest["revision_kind"] == (
            "base_commit_with_worktree_changes" if status else "commit"
        )
        package_files = {
            name.removeprefix("usmsb_core/") for name in names if name.startswith("usmsb_core/")
        }
        assert package_files == set(manifest["sha256"]) | {"MANIFEST.json"}
        assert {"autonomy/journal.py", "autonomy/profiles.py", "LICENSE"} <= package_files
        for name, expected in manifest["sha256"].items():
            content = wheel.read(f"usmsb_core/{name}")
            assert hashlib.sha256(content).hexdigest() == expected, name
        for name, source in manifest["source_paths"].items():
            canonical = (ROOT / source).read_bytes().replace(b"\r\n", b"\n")
            assert wheel.read(f"usmsb_core/{name}") == canonical, source
        assert (
            manifest["content_digest"]
            == hashlib.sha256(json.dumps(manifest["sha256"], sort_keys=True).encode()).hexdigest()
        )
        license_name = next(name for name in names if name.endswith(".dist-info/licenses/LICENSE"))
        assert wheel.read(license_name) == wheel.read("usmsb_core/LICENSE")
        assert b"MIT License" in wheel.read(license_name)


def test_wheel_record_covers_manifest_and_every_packaged_byte(archives):
    with zipfile.ZipFile(archives[0]) as wheel:
        record_name = next(name for name in wheel.namelist() if name.endswith(".dist-info/RECORD"))
        rows = list(csv.reader(io.StringIO(wheel.read(record_name).decode())))
        assert {row[0] for row in rows} == set(wheel.namelist())
        for name, digest, size in rows:
            if name == record_name:
                assert digest == size == ""
                continue
            content = wheel.read(name)
            expected = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
            assert digest == "sha256=" + expected.decode(), name
            assert int(size) == len(content), name


def test_sdist_retains_wheel_sources_manifest_license_and_metadata(archives):
    with zipfile.ZipFile(archives[0]) as wheel, tarfile.open(archives[1]) as sdist:
        members = sdist.getnames()
        prefix = members[0].split("/")[0]
        for name in wheel.namelist():
            if name.startswith("usmsb_core/"):
                assert sdist.extractfile(f"{prefix}/src/{name}").read() == wheel.read(name)
        assert sdist.extractfile(f"{prefix}/LICENSE").read() == wheel.read("usmsb_core/LICENSE")
        for name in ("pyproject.toml", "README.md"):
            assert (
                sdist.extractfile(f"{prefix}/{name}").read()
                == (ROOT / "packages/usmsb-core" / name).read_bytes()
            )


@pytest.mark.parametrize("unpack", [False, True], ids=["wheel-zip", "unpacked-wheel"])
def test_core_wheel_runs_without_site_packages_or_sdk(archives, tmp_path, unpack):
    path = archives[0]
    if unpack:
        path = tmp_path / "installed"
        with zipfile.ZipFile(archives[0]) as wheel:
            wheel.extractall(path)
    run_python(
        """
        import importlib
        from importlib import metadata, resources, util
        import json
        import sys

        assert sys.flags.isolated and sys.flags.no_site
        assert not any("site-packages" in part for part in sys.path)
        assert util.find_spec("usmsb_sdk") is None
        assert util.find_spec("pydantic") is None
        sys.path.insert(0, sys.argv[1])
        import usmsb_core.autonomy as autonomy
        from usmsb_core.core.elements import Goal

        manifest = json.loads(resources.files("usmsb_core").joinpath("MANIFEST.json").read_text())
        optional = {"autonomy/learning.py", "growth_economic_harness/models.py",
                    "growth_economic_harness/experience_loop.py"}
        for filename in manifest["sha256"]:
            if not filename.endswith(".py") or filename in optional:
                continue
            module = filename.removesuffix(".py").replace("/", ".")
            module = module.removesuffix(".__init__")
            if module == "__init__":
                module = ""
            importlib.import_module("usmsb_core" + ("." + module if module else ""))
        goal = autonomy.goal_element({"id": "g1", "title": "Verify portable wheel",
            "description": "No third party dependencies", "owner_id": "a", "status": "active"})
        assert isinstance(goal, Goal) and goal.associated_agent_id == "a"
        status = autonomy.remote_status({"state": "accepted", "run_ref": "local:1"})
        assert status["state"] == "accepted"
        assert autonomy.CollaborationJournal.__module__ == "usmsb_core.autonomy.journal"
        principals = {"a": {"controller": "owner-a", "operations": ["goal.create"]}}
        journal = autonomy.CollaborationJournal(
            "journal.sqlite", host_id="local-test", principals=principals)
        command = {"id": "g1", "intent": {"title": "Verify wheel", "description": "Read archive",
                   "domain": "research", "success_criteria": "A durable receipt"}}
        receipt = journal.apply("a", "command-1", "goal.create", command)
        reopened = autonomy.CollaborationJournal(
            "journal.sqlite", host_id="local-test", principals=principals)
        assert reopened.apply("a", "command-1", "goal.create", command) == receipt
        assert reopened.get("goal", "g1")["owner_id"] == "a"
        assert len(reopened.events()) == 1
        assert "usmsb_core.autonomy.learning" not in sys.modules
        assert "pydantic" not in sys.modules
        assert not any(name == "usmsb_sdk" or name.startswith("usmsb_sdk.") for name in sys.modules)
        assert metadata.version("usmsb-core").startswith("0.9.0a")
        license_text = resources.files("usmsb_core").joinpath("LICENSE").read_text()
        assert license_text.startswith("MIT License")
        try:
            importlib.import_module("usmsb_core.autonomy.learning")
        except ModuleNotFoundError as error:
            assert error.name == "pydantic"
        else:
            raise AssertionError("Learning must be optional and require Pydantic")
        """,
        path,
        cwd=tmp_path,
    )


def test_learning_extra_imports_with_pydantic(archives, tmp_path):
    run_python(
        """
        import sys
        sys.path.insert(0, sys.argv[1])
        from usmsb_core.autonomy.learning import ExperienceJournal, PromotionEvidence
        from usmsb_core.growth_economic_harness.models import ExperienceDraft
        import pydantic
        assert pydantic.__version__.split(".")[0] == "2"
        assert ExperienceJournal.__module__ == "usmsb_core.autonomy.learning"
        assert issubclass(ExperienceDraft, pydantic.BaseModel)
        assert PromotionEvidence.__module__ == "usmsb_core.growth_economic_harness.experience_loop"
        assert not any(name == "usmsb_sdk" or name.startswith("usmsb_sdk.") for name in sys.modules)
        """,
        archives[0],
        cwd=tmp_path,
        no_site=False,
    )


@pytest.mark.parametrize("first_import", ["import usmsb_sdk", "import usmsb_sdk.core"])
def test_sdk_elements_and_contracts_import_without_dependencies(tmp_path, first_import):
    run_python(
        """
        import sys
        sys.path.insert(0, sys.argv[1])
        exec(sys.argv[2])
        import usmsb_sdk
        assert "usmsb_sdk.agent_sdk" not in sys.modules
        assert "usmsb_sdk.core.elements" not in sys.modules
        from usmsb_sdk import Goal
        from usmsb_sdk.core import Goal as CoreGoal
        from usmsb_sdk.core.elements import Goal as OriginalGoal
        from usmsb_sdk.autonomy import goal_element
        assert Goal is CoreGoal is OriginalGoal
        assert isinstance(goal_element({"id": "g", "title": "Test", "description": "Read",
                                       "owner_id": "a", "status": "active"}), Goal)
        assert usmsb_sdk.Goal is Goal and usmsb_sdk.__dict__["Goal"] is Goal
        assert "usmsb_sdk.core.config" not in sys.modules
        assert "usmsb_sdk.core.universal_actions" not in sys.modules
        assert "usmsb_sdk.core.logic" not in sys.modules
        assert "usmsb_sdk.agent_sdk" not in sys.modules
        assert "usmsb_sdk.api" not in sys.modules
        for name in ("pydantic", "fastapi", "web3", "openai", "httpx", "sqlalchemy"):
            assert name not in sys.modules
        assert sys.flags.no_site
        """,
        ROOT / "src",
        first_import,
        cwd=tmp_path,
    )


def test_sdk_core_preserves_aliases_interfaces_action_result_and_star_import(tmp_path):
    run_python(
        """
        import sys
        sys.path.insert(0, sys.argv[1])
        import usmsb_sdk.core as core
        from usmsb_sdk.core import CoreAgentConfig, ActionResult
        from usmsb_sdk.core.config import AgentConfig
        from usmsb_sdk.core.logic.goal_action_outcome import ActionResult as LoopResult
        from usmsb_sdk.core import interfaces, universal_actions
        assert CoreAgentConfig is AgentConfig
        assert ActionResult is LoopResult
        assert ActionResult is not universal_actions.ActionResult
        for role in ("Decision", "Evaluation", "Execution", "Feedback", "Interaction",
                     "Learning", "Perception", "RiskManagement", "Transformation"):
            name = f"I{role}Service"
            assert getattr(core, name) is getattr(universal_actions, name)
            assert getattr(core, name) is not getattr(interfaces, name)
        namespace = {}
        exec("from usmsb_sdk.core import *", namespace)
        assert set(namespace) - {"__builtins__"} == set(core.__all__)
        original_exports = set('''
            CoreAgentConfig AuthConfig DatabaseConfig LoggingConfig NetworkConfig PlatformConfig
            load_config load_config_from_env Agent AgentType Environment EnvironmentType Goal
            GoalStatus Information InformationType Object Resource ResourceType Risk RiskType
            Rule RuleType Value ValueType IDecisionService IEvaluationService IExecutionService
            IFeedbackService IInteractionService ILearningService IPerceptionService
            IRiskManagementService ITransformationService LLMPerceptionService LLMDecisionService
            LLMExecutionService LLMInteractionService LLMTransformationService LLMEvaluationService
            LLMFeedbackService LLMLearningService LLMRiskManagementService
            UniversalActionServiceFactory ActionResult ActionResultStatus GoalActionOutcomeLoop
            GoalManager LoopStatus LoopIteration LogicEngineRegistry
            ResourceTransformationValueEngine
            InformationDecisionControlEngine SystemEnvironmentEngine EmergenceSelfOrganizationEngine
            AdaptationEvolutionEngine AdaptationRecord EvolutionMetric
        '''.split())
        assert original_exports <= namespace.keys()
        assert set(core.__all__) <= set(dir(core))
        assert namespace["CoreAgentConfig"] is AgentConfig
        assert namespace["ActionResult"] is LoopResult
        """,
        ROOT / "src",
        cwd=tmp_path,
    )


def test_sdk_optional_exports_load_original_modules_only_on_access(tmp_path):
    run_python(
        """
        import sys
        import types
        sys.path.insert(0, sys.argv[1])
        import usmsb_sdk as sdk
        assert "usmsb_sdk.agent_sdk" not in sys.modules
        assert "usmsb_sdk.api" not in sys.modules

        # Stand-ins for expensive modules verify routing without installing or
        # executing any provider. Real core exports are tested separately.
        modules = {
            "usmsb_sdk.agent_sdk": ["BaseAgent", "AgentConfig", "AgentCapability",
                "CapabilityDefinition", "SkillDefinition", "ProtocolConfig", "ProtocolType",
                "RegistrationManager", "CommunicationManager", "DiscoveryManager", "create_agent"],
            "usmsb_sdk.api.python.agent_builder": ["AgentBuilder"],
            "usmsb_sdk.api.python.environment_builder": ["EnvironmentBuilder"],
            "usmsb_sdk.api.python.usmsb_manager": ["USMSBManager"],
        }
        for module_name, names in modules.items():
            module = types.ModuleType(module_name)
            for name in names:
                assert name not in sdk.__dict__
                setattr(module, name, object())
            sys.modules[module_name] = module
            for name in names:
                assert getattr(sdk, name) is getattr(module, name)
                assert sdk.__dict__[name] is getattr(module, name)
        namespace = {}
        exec("from usmsb_sdk import *", namespace)
        elements = {"Agent", "Object", "Goal", "Resource", "Rule", "Information",
                    "Value", "Risk", "Environment"}
        expected = elements | {name for names in modules.values() for name in names}
        assert set(namespace) - {"__builtins__"} == expected == set(sdk.__all__)
        assert expected <= set(dir(sdk))
        """,
        ROOT / "src",
        cwd=tmp_path,
    )


def test_lazy_import_errors_are_not_hidden_and_unknown_attributes_remain_absent(tmp_path):
    run_python(
        """
        import importlib.abc
        import sys
        sys.path.insert(0, sys.argv[1])
        import usmsb_sdk
        import usmsb_sdk.core
        for module in (usmsb_sdk, usmsb_sdk.core):
            assert not hasattr(module, "not_a_public_export")
            try:
                getattr(module, "not_a_public_export")
            except AttributeError as error:
                assert module.__name__ in str(error)
            else:
                raise AssertionError("Unknown exports must raise AttributeError")
        class MissingProvider(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "usmsb_sdk.agent_sdk":
                    raise ModuleNotFoundError("sentinel missing provider", name="sentinel_provider")
        sys.meta_path.insert(0, MissingProvider())
        try:
            usmsb_sdk.BaseAgent
        except ModuleNotFoundError as error:
            assert error.name == "sentinel_provider"
        else:
            raise AssertionError("Dependency errors must propagate")
        assert "BaseAgent" not in usmsb_sdk.__dict__
        """,
        ROOT / "src",
        cwd=tmp_path,
    )
