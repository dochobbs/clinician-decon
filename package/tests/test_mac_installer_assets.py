from pathlib import Path
import plistlib


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mac_installer_assets_define_local_openmed_setup_path():
  builder = REPO_ROOT / "installer" / "mac" / "build_dmg.sh"
  self_contained_builder = REPO_ROOT / "installer" / "mac" / "build_self_contained_dmg.sh"
  launcher = REPO_ROOT / "installer" / "mac" / "app" / "clinician-decon-launcher"
  plist_path = REPO_ROOT / "installer" / "mac" / "app" / "Info.plist"
  install_doc = REPO_ROOT / "docs" / "install" / "mac-clean-install.md"
  qa_doc = REPO_ROOT / "docs" / "qa" / "mac-installer-qa.md"

  for path in (builder, self_contained_builder, launcher, plist_path, install_doc, qa_doc):
    assert path.is_file(), f"missing Mac installer asset: {path.relative_to(REPO_ROOT)}"

  launcher_text = launcher.read_text(encoding="utf-8")
  assert "127.0.0.1" in launcher_text
  assert "DECON_HOME" in launcher_text
  assert "BUNDLED_PYTHON" in launcher_text
  assert "BUNDLED_SITE_PACKAGES" in launcher_text
  assert "DECON_MODEL_DIR" in launcher_text
  assert "PYTHONPATH" in launcher_text
  assert "decon-setup-openmed" in launcher_text
  assert "OpenMed setup did not complete" in launcher_text

  builder_text = builder.read_text(encoding="utf-8")
  assert "package/local-models" in builder_text
  assert "hdiutil create" in builder_text
  assert "Clinician Decon.app" in builder_text

  self_contained_text = self_contained_builder.read_text(encoding="utf-8")
  assert "uv python install" in self_contained_text
  assert "--target" in self_contained_text
  assert "python-packages" in self_contained_text
  assert "local-models" in self_contained_text
  assert "DECON_MODEL_DIR" in self_contained_text
  assert "self-contained" in self_contained_text

  plist = plistlib.loads(plist_path.read_bytes())
  assert plist["CFBundleName"] == "Clinician Decon"
  assert plist["CFBundleExecutable"] == "clinician-decon-launcher"

  install_text = install_doc.read_text(encoding="utf-8")
  assert "self-contained DMG" in install_text
  assert "OpenMed model files are bundled" in install_text
  assert "raw pasted text stays on 127.0.0.1" in install_text
  assert "~/Library/Application Support/Clinician Decon" in install_text

  qa_text = qa_doc.read_text(encoding="utf-8")
  assert "No raw PHI appears in logs" in qa_text
  assert "No prompt text appears in third-party URLs" in qa_text
