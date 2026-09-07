"""Grounding tests for docs/ANALYSIS.md (research deliverable).

These tests validate that the deliverable (1) exists and is a complete, usable
document answering every part of the goal, and (2) every material factual claim
about the analysed code is actually true of the code in `civil42pwa-public/`.

The project is research/analysis: we do NOT run the app; we only compare the
written claims against the source files on disk.
"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "docs" / "ANALYSIS.md"
PWA = ROOT / "civil42pwa-public"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestDeliverableStructure(unittest.TestCase):
    """The deliverable must be a complete, self-contained document."""

    def test_file_exists_and_is_substantial(self):
        self.assertTrue(ANALYSIS.exists(), "docs/ANALYSIS.md is missing")
        text = ANALYSIS.read_text(encoding="utf-8")
        self.assertGreater(len(text), 6000, "ANALYSIS.md looks like a stub/placeholder")

    def test_all_nine_sections_present(self):
        text = ANALYSIS.read_text(encoding="utf-8")
        for i in range(1, 10):
            self.assertIn(f"## {i}.", text, f"missing section header '## {i}.'")

    def test_answers_every_part_of_the_goal(self):
        text = ANALYSIS.read_text(encoding="utf-8")
        for needle in ["Co robi repozytorium", "Porównanie z pomysłem", "PoC", "MVP",
                       "gotowy produkt w wersji beta", "Źródła", "Otwarte pytania"]:
            self.assertIn(needle, text, f"missing required content: {needle!r}")


class TestCloneState(unittest.TestCase):
    """The clone must match the doc's claim: commit 429f9bc, correct origin, clean tree."""

    def test_head_commit_matches_doc(self):
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PWA, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(out, "429f9bc", f"doc claims commit 429f9bc but HEAD is {out!r}")

    def test_origin_url_matches_doc(self):
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=PWA, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(out, "https://github.com/rzymek/civil42pwa-public.git")

    def test_working_tree_clean(self):
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PWA, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(out, "", "clone has uncommitted local changes (analysed repo must stay clean)")

    def test_target_repo_has_no_readme(self):
        self.assertFalse((PWA / "README.md").exists(), "doc claims target repo has no README")


class TestPersistTripleBug(unittest.TestCase):
    """F2 / section 4.2 / section 1.3: the persist() write path is broken three ways."""

    @classmethod
    def setUpClass(cls):
        cls.persist = read("civil42pwa-public/functions/src/persist.ts")

    def test_ddl_comment_has_no_geo_desc(self):
        ddl = self.persist.split("DDL for Snowflake setup:")[1].split("*/")[0]
        self.assertNotIn("geo_desc", ddl, "DDL comment actually contains geo_desc")
        self.assertIn("audio_path", ddl)
        self.assertIn("image_path", ddl)

    def test_insert_has_five_placeholders_and_geo_desc(self):
        insert = self.persist.split("INSERT INTO reports")[1].split("`;")[0]
        self.assertIn("geo_desc", insert)
        self.assertEqual(insert.count("?"), 5, "INSERT must have 5 placeholders")

    def test_binds_have_only_four_values(self):
        binds = self.persist.split("await executeQuery(insertSql, [")[1].split("])")[0]
        # 4 items => 3 top-level commas; the bound strings contain no commas
        self.assertEqual(binds.count(","), 3, f"expected 4 binds, found {binds.count(',') + 1}")
        self.assertNotIn("desc", binds, "loc.desc is never bound to the query")

    def test_desc_param_is_declared_but_unused(self):
        self.assertIn("desc: string", self.persist, "persist() signature should declare desc")
        body = self.persist.split("desc: string", 1)[1]
        self.assertNotIn("loc.desc", body, "loc.desc is not used anywhere in the body")


class TestReportEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read("civil42pwa-public/functions/src/report.ts")

    def test_parses_with_busboy_and_answers_english(self):
        self.assertIn("busboy", self.report)
        self.assertIn("Report received successfully", self.report)

    def test_geocodes_before_persist_and_passes_desc(self):
        self.assertIn("await whatIsAtLocation({lat,lon})", self.report)
        self.assertIn("{lat, lon, desc: geoDesc}", self.report)

    def test_no_validation_of_voice_and_image(self):
        # buffers are dereferenced directly without presence checks (F3)
        self.assertIn("voice.buffer.length", self.report)
        self.assertIn("image.buffer.length", self.report)
        self.assertNotIn("if (!voice)", self.report)
        self.assertNotIn("if (!image)", self.report)

    def test_stale_todo_comment_present(self):
        self.assertIn("TODO: Implement storage/database logic", self.report)


class TestBackendHelpers(unittest.TestCase):
    def test_snowflake_placeholder_credentials(self):
        snow = read("civil42pwa-public/functions/src/snowflake.ts")
        for literal in ("'[SNOWFLAKE-ACCOUNT]'", "'[SNOWFLAKE-USERNAME]'", "'[SNOWFLAKE-TOKEN]'"):
            self.assertIn(literal, snow)
        for value in ("CIVIL42", "public", "civil42wh"):
            self.assertIn(value, snow)

    def test_query_snowflake_declares_no_secrets(self):
        idx = read("civil42pwa-public/functions/src/index.ts")
        self.assertIn("secrets: []", idx)
        self.assertIn("SELECT CURRENT_VERSION()", idx)

    def test_reverse_geocoding_uses_nominatim(self):
        w = read("civil42pwa-public/functions/src/whatIsAtLocation.ts")
        self.assertIn("nominatim.openstreetmap.org/reverse", w)
        self.assertIn("Civil42PWA/1.0", w)
        self.assertIn("display_name", w)


class TestFrontendClaims(unittest.TestCase):
    def test_app_typo_and_continuous_recording(self):
        app = read("civil42pwa-public/src/app.tsx")
        self.assertIn("Nacinij", app)
        self.assertIn("audio.start()", app)
        self.assertIn("useGeoLocation", app)

    def test_gps_used_without_ready_guard(self):
        app = read("civil42pwa-public/src/app.tsx")
        self.assertIn("lat: gps.latitude", app)
        self.assertIn("lon: gps.longitude", app)

    def test_microphone_errors_silently(self):
        u = read("civil42pwa-public/src/useRecordAudio.tsx")
        self.assertIn("console.error", u)
        self.assertIn("getUserMedia({audio: true})", u)

    def test_send_multipart_to_relative_report(self):
        s = read("civil42pwa-public/src/send.tsx")
        self.assertIn('fetch("/report"', s)
        self.assertIn('"voice.webm"', s)
        self.assertIn('"image.png"', s)
        self.assertIn('formData.append("lat"', s)
        self.assertIn('formData.append("lon"', s)

    def test_camera_uses_environment_facing(self):
        c = read("civil42pwa-public/src/Camera.tsx")
        self.assertIn('facingMode: "environment"', c)

    def test_state_module_is_empty_dead_code(self):
        st = read("civil42pwa-public/src/state/state.tsx")
        i = st.index("const initialState = {")
        j = st.index("}", i)
        self.assertEqual(st[i + len("const initialState = {"):j].strip(), "",
                         "initialState must be empty per the doc")
        self.assertIn("resetState", st)

    def test_app_spec_is_vacuous(self):
        spec = read("civil42pwa-public/src/app.spec.tsx")
        self.assertIn("expect(true).toBe(true)", spec)


class TestConfigClaims(unittest.TestCase):
    def test_deploy_script_uses_surge(self):
        pkg = read("civil42pwa-public/package.json")
        self.assertIn('"deploy": "surge dist/ Civil42.surge.sh"', pkg)
        self.assertIn("vitest", pkg)
        self.assertIn("vite-plugin-pwa", pkg)
        self.assertIn("pwa-assets-generator", pkg)

    def test_public_icon_exists(self):
        self.assertTrue((PWA / "public" / "icon.png").exists())

    def test_firebase_rewrites(self):
        fb = read("civil42pwa-public/firebase.json")
        self.assertIn('"source": "/report"', fb)
        self.assertIn('"source": "/snow"', fb)
        self.assertIn('"functionId": "report"', fb)
        self.assertIn('"functionId": "querySnowflake"', fb)

    def test_firebase_project_id(self):
        self.assertIn("civil42poc", read("civil42pwa-public/.firebaserc"))

    def test_node_version_mismatch(self):
        self.assertEqual(read("civil42pwa-public/.nvmrc").strip(), "v24")
        self.assertIn('"node": "22"', read("civil42pwa-public/functions/package.json"))

    def test_surge_ci_workflow(self):
        d = read("civil42pwa-public/.github/workflows/deploy.yml")
        self.assertIn("SURGE_LOGIN", d)
        self.assertIn("SURGE_TOKEN", d)

    def test_firebase_pr_preview_workflow(self):
        fpr = read("civil42pwa-public/.github/workflows/firebase-hosting-pull-request.yml")
        self.assertIn("civil42poc", fpr)
        self.assertIn("FirebaseExtended/action-hosting-deploy", fpr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
