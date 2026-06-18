from pathlib import Path
import json
import plistlib


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mac_installer_assets_define_local_openmed_setup_path():
  builder = REPO_ROOT / "installer" / "mac" / "build_dmg.sh"
  self_contained_builder = REPO_ROOT / "installer" / "mac" / "build_self_contained_dmg.sh"
  launcher = REPO_ROOT / "installer" / "mac" / "app" / "clinician-decon-launcher"
  plist_path = REPO_ROOT / "installer" / "mac" / "app" / "Info.plist"
  icon_generator = REPO_ROOT / "installer" / "mac" / "create_icon_assets.py"
  app_icon = REPO_ROOT / "installer" / "mac" / "assets" / "ClinicianDecon.icns"
  install_doc = REPO_ROOT / "docs" / "install" / "mac-clean-install.md"
  demo_readme = REPO_ROOT / "docs" / "install" / "mac-demo-readme.md"
  qa_doc = REPO_ROOT / "docs" / "qa" / "mac-installer-qa.md"
  web_manifest = REPO_ROOT / "package" / "web" / "manifest.json"
  web_index = REPO_ROOT / "package" / "web" / "index.html"
  web_app = REPO_ROOT / "package" / "web" / "app.js"
  web_worker = REPO_ROOT / "package" / "web" / "sw.js"
  web_favicon = REPO_ROOT / "package" / "web" / "favicon.ico"
  web_icon_192 = REPO_ROOT / "package" / "web" / "icons" / "icon-192.png"
  web_icon_512 = REPO_ROOT / "package" / "web" / "icons" / "icon-512.png"

  for path in (
    builder,
    self_contained_builder,
    launcher,
    plist_path,
    icon_generator,
    app_icon,
    install_doc,
    demo_readme,
    qa_doc,
    web_manifest,
    web_index,
    web_app,
    web_worker,
    web_favicon,
    web_icon_192,
    web_icon_512,
  ):
    assert path.is_file(), f"missing Mac installer asset: {path.relative_to(REPO_ROOT)}"

  launcher_text = launcher.read_text(encoding="utf-8")
  assert "127.0.0.1" in launcher_text
  assert "server.pid" in launcher_text
  assert "Starting the local privacy engine" in launcher_text
  assert 'wait "$SERVER_PID"' in launcher_text
  assert "trap cleanup EXIT INT TERM" in launcher_text
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
  assert "ClinicianDecon.icns" in builder_text
  assert "mac-demo-readme.md" in builder_text

  self_contained_text = self_contained_builder.read_text(encoding="utf-8")
  assert "uv python install" in self_contained_text
  assert "--target" in self_contained_text
  assert "python-packages" in self_contained_text
  assert "local-models" in self_contained_text
  assert "DECON_MODEL_DIR" in self_contained_text
  assert "self-contained" in self_contained_text
  assert "ClinicianDecon.icns" in self_contained_text
  assert "mac-demo-readme.md" in self_contained_text

  plist = plistlib.loads(plist_path.read_bytes())
  assert plist["CFBundleName"] == "Clinician Decon"
  assert plist["CFBundleExecutable"] == "clinician-decon-launcher"
  assert plist["CFBundleIconFile"] == "ClinicianDecon"
  assert plist["LSUIElement"] is True

  install_text = install_doc.read_text(encoding="utf-8")
  assert "self-contained DMG" in install_text
  assert "OpenMed model files are bundled" in install_text
  assert "raw pasted text stays on 127.0.0.1" in install_text
  assert "~/Library/Application Support/Clinician Decon" in install_text

  demo_text = demo_readme.read_text(encoding="utf-8")
  assert "Drag `Clinician Decon.app` to `Applications`" in demo_text
  assert "Right-click `Clinician Decon.app`, choose `Open`" in demo_text
  assert "http://127.0.0.1:8769/" in demo_text
  assert "Choose `For use in`" in demo_text
  assert "The browser tab is the app window" in demo_text
  assert "click `Quit` in" in demo_text
  assert "build_self_contained_dmg.sh" not in demo_text

  qa_text = qa_doc.read_text(encoding="utf-8")
  assert "No raw PHI appears in logs" in qa_text
  assert "No prompt text appears in third-party URLs" in qa_text
  assert "Confirm port `8769` is no longer listening" in qa_text

  manifest = json.loads(web_manifest.read_text(encoding="utf-8"))
  assert {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"} in manifest["icons"]
  assert {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"} in manifest["icons"]

  web_index_text = web_index.read_text(encoding="utf-8")
  assert "How to use it" in web_index_text
  assert "app-controls" in web_index_text
  assert 'id="shutdownButton"' in web_index_text
  assert ">Quit</button>" in web_index_text
  assert "Paste PHI text" in web_index_text
  assert "Pick destination" in web_index_text
  assert "Review locally" in web_index_text
  assert "Copy manually" in web_index_text
  assert "For use in" in web_index_text
  assert "sampleSelect" in web_index_text
  assert "ADHD med follow-up" in web_index_text
  assert "Gilbert/Tylenol" not in web_index_text
  assert "Quit Local App" not in web_index_text
  assert "Intended use" in web_index_text

  web_app_text = web_app.read_text(encoding="utf-8")
  assert "Running local decon" in web_app_text
  assert "Still running" in web_app_text
  assert "Decon did not run." in web_app_text
  assert "AbortController" in web_app_text
  assert "const samples" in web_app_text
  assert "guanfacine" in web_app_text
  assert "PFAPA" in web_app_text
  assert "Sarah O" not in web_app_text
  assert 'shutdownButton.textContent = "Quit"' in web_app_text
  assert "/api/shutdown" in web_app_text
  assert "Stopped. Close this tab." in web_app_text

  worker_text = web_worker.read_text(encoding="utf-8")
  assert "decon-static-v5" in worker_text
  assert "decon-static-v4" in worker_text
  assert "decon-static-v3" in worker_text
  assert "decon-static-v2" in worker_text
  assert "decon-static-v1" in worker_text
  assert "self.skipWaiting" in worker_text
  assert "clients.claim" in worker_text
  assert "fetch(event.request)" in worker_text
