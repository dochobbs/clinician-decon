from pathlib import Path
import json
import plistlib


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mac_installer_assets_define_local_openmed_setup_path():
  builder = REPO_ROOT / "installer" / "mac" / "build_dmg.sh"
  self_contained_builder = REPO_ROOT / "installer" / "mac" / "build_self_contained_dmg.sh"
  native_builder = REPO_ROOT / "installer" / "mac" / "build_native_wrapper.sh"
  launcher = REPO_ROOT / "installer" / "mac" / "app" / "clinician-decon-launcher"
  plist_path = REPO_ROOT / "installer" / "mac" / "app" / "Info.native.plist"
  native_source = REPO_ROOT / "installer" / "mac" / "native" / "ClinicianDeconApp.swift"
  icon_generator = REPO_ROOT / "installer" / "mac" / "create_icon_assets.py"
  source_icon = REPO_ROOT / "decon-mark.svg"
  asset_svg = REPO_ROOT / "installer" / "mac" / "assets" / "decon-mark.svg"
  app_icon = REPO_ROOT / "installer" / "mac" / "assets" / "ClinicianDecon.icns"
  install_doc = REPO_ROOT / "docs" / "install" / "mac-clean-install.md"
  demo_readme = REPO_ROOT / "docs" / "install" / "mac-demo-readme.md"
  qa_doc = REPO_ROOT / "docs" / "qa" / "mac-installer-qa.md"
  web_manifest = REPO_ROOT / "package" / "web" / "manifest.json"
  web_index = REPO_ROOT / "package" / "web" / "index.html"
  web_app = REPO_ROOT / "package" / "web" / "app.js"
  web_styles = REPO_ROOT / "package" / "web" / "styles.css"
  web_worker = REPO_ROOT / "package" / "web" / "sw.js"
  web_favicon = REPO_ROOT / "package" / "web" / "favicon.ico"
  web_icon_svg = REPO_ROOT / "package" / "web" / "icons" / "decon-mark.svg"
  web_icon_192 = REPO_ROOT / "package" / "web" / "icons" / "icon-192.png"
  web_icon_512 = REPO_ROOT / "package" / "web" / "icons" / "icon-512.png"

  for path in (
    builder,
    self_contained_builder,
    native_builder,
    launcher,
    plist_path,
    native_source,
    icon_generator,
    source_icon,
    asset_svg,
    app_icon,
    install_doc,
    demo_readme,
    qa_doc,
    web_manifest,
    web_index,
    web_app,
    web_styles,
    web_worker,
    web_favicon,
    web_icon_svg,
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
  assert "DECON_NO_BROWSER" in launcher_text
  assert "open_local_ui" in launcher_text

  builder_text = builder.read_text(encoding="utf-8")
  assert "package/local-models" in builder_text
  assert "hdiutil create" in builder_text
  assert "Clinician Decon.app" in builder_text
  assert "ClinicianDecon.icns" in builder_text
  assert "mac-demo-readme.md" in builder_text
  assert "Info.native.plist" in builder_text
  assert "build_native_wrapper.sh" in builder_text

  self_contained_text = self_contained_builder.read_text(encoding="utf-8")
  assert "uv python install" in self_contained_text
  assert "--target" in self_contained_text
  assert "python-packages" in self_contained_text
  assert "local-models" in self_contained_text
  assert "DECON_MODEL_DIR" in self_contained_text
  assert "self-contained" in self_contained_text
  assert "ClinicianDecon.icns" in self_contained_text
  assert "mac-demo-readme.md" in self_contained_text
  assert "Info.native.plist" in self_contained_text
  assert "build_native_wrapper.sh" in self_contained_text

  native_builder_text = native_builder.read_text(encoding="utf-8")
  assert "swiftc" in native_builder_text
  assert "-framework WebKit" in native_builder_text
  assert "ClinicianDeconApp.swift" in native_builder_text

  icon_generator_text = icon_generator.read_text(encoding="utf-8")
  assert "SOURCE_SVG_PATH" in icon_generator_text
  assert "decon-mark.svg" in icon_generator_text
  assert "iconutil" not in icon_generator_text
  assert "_write_icns" in icon_generator_text

  source_icon_text = source_icon.read_text(encoding="utf-8")
  assert 'fill="#1c6b58"' in source_icon_text
  assert 'x1="50"' in source_icon_text
  assert 'cx="30"' in source_icon_text
  assert web_icon_svg.read_text(encoding="utf-8") == source_icon_text
  assert asset_svg.read_text(encoding="utf-8") == source_icon_text

  native_source_text = native_source.read_text(encoding="utf-8")
  assert "WKWebView" in native_source_text
  assert "WKScriptMessageHandler" in native_source_text
  assert 'configuration.userContentController.add(self, name: "deconNative")' in native_source_text
  assert 'action == "quit"' in native_source_text
  assert "NSApp.terminate(nil)" in native_source_text
  assert "serverMonitorTimer" in native_source_text
  assert "checkServerStillRunning" in native_source_text
  assert "local server stopped; terminating native app" in native_source_text
  assert "DECON_NO_BROWSER" in native_source_text
  assert "clinician-decon-launcher" in native_source_text
  assert "http://127.0.0.1:8769/" in native_source_text

  plist = plistlib.loads(plist_path.read_bytes())
  assert plist["CFBundleName"] == "Clinician Decon"
  assert plist["CFBundleExecutable"] == "ClinicianDeconNative"
  assert plist["CFBundleIconFile"] == "ClinicianDecon"
  assert "LSUIElement" not in plist
  assert plist["NSAppTransportSecurity"]["NSAllowsLocalNetworking"] is True

  install_text = install_doc.read_text(encoding="utf-8")
  assert "self-contained DMG" in install_text
  assert "OpenMed model files are bundled" in install_text
  assert "raw pasted text stays on 127.0.0.1" in install_text
  assert "~/Library/Application Support/Clinician Decon" in install_text

  demo_text = demo_readme.read_text(encoding="utf-8")
  assert "Drag `Clinician Decon.app` to `Applications`" in demo_text
  assert "Right-click `Clinician Decon.app`, choose `Open`" in demo_text
  assert "`Clinician Decon` app window should open automatically" in demo_text
  assert "Choose `For use in`" in demo_text
  assert "native window around the local web UI" in demo_text
  assert "click `Quit` in" in demo_text
  assert "build_self_contained_dmg.sh" not in demo_text

  qa_text = qa_doc.read_text(encoding="utf-8")
  assert "No raw PHI appears in logs" in qa_text
  assert "No prompt text appears in third-party URLs" in qa_text
  assert "Confirm port `8769` is no longer listening" in qa_text

  manifest = json.loads(web_manifest.read_text(encoding="utf-8"))
  assert {"src": "/icons/decon-mark.svg", "sizes": "any", "type": "image/svg+xml"} in manifest["icons"]
  assert {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"} in manifest["icons"]
  assert {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"} in manifest["icons"]

  web_index_text = web_index.read_text(encoding="utf-8")
  assert "Strip identifiers" in web_index_text
  assert "before" in web_index_text
  assert "The original text stays on this Mac." in web_index_text
  assert "/icons/decon-mark.svg" in web_index_text
  assert "Scrubbed draft" in web_index_text
  assert "your review before it leaves" in web_index_text
  assert "app-controls" in web_index_text
  assert 'id="shutdownButton"' in web_index_text
  assert ">Quit</button>" in web_index_text
  assert "Running on this Mac" in web_index_text
  assert "For use in" in web_index_text
  assert "Copy across" in web_index_text
  assert "What was pulled" in web_index_text
  assert "What to double-check" in web_index_text
  assert "on this mac" in web_index_text
  assert "sampleSelect" in web_index_text
  assert "ADHD med follow-up" in web_index_text
  assert "Gilbert/Tylenol" not in web_index_text
  assert ">Load</button>" in web_index_text
  assert "Load Example" not in web_index_text
  assert "Quit Local App" not in web_index_text
  assert "Not</strong> a full chart de-identification export" in web_index_text

  web_app_text = web_app.read_text(encoding="utf-8")
  assert "Reading on this Mac" in web_app_text
  assert "Still reading on this Mac" in web_app_text
  assert "Decon did not run." in web_app_text
  assert "AbortController" in web_app_text
  assert "const samples" in web_app_text
  assert "removed_spans" in web_app_text
  assert "requestNativeQuit" in web_app_text
  assert "window.webkit?.messageHandlers?.deconNative" in web_app_text
  assert 'nativeHandler.postMessage({ action: "quit" })' in web_app_text
  assert "Closing app window." in web_app_text
  assert "Initials, nicknames, and single first names" in web_app_text
  assert "A relationship can identify a patient" in web_app_text
  assert "flyCourier" in web_app_text
  assert "guanfacine" in web_app_text
  assert "PFAPA" in web_app_text
  assert "Sarah O" not in web_app_text
  assert 'shutdownButton.textContent = "Quit"' in web_app_text
  assert "/api/shutdown" in web_app_text
  assert "Stopped. Close this window." in web_app_text

  web_styles_text = web_styles.read_text(encoding="utf-8")
  assert "--ground-in: #fbfaf6" in web_styles_text
  assert "--ground-out: #eef2f2" in web_styles_text
  assert "var(--ground-in) 50%" in web_styles_text
  assert "var(--ground-out) 50%" in web_styles_text
  assert ".seam-tag" in web_styles_text
  assert ".courier.fly" in web_styles_text
  assert "container-type: inline-size" in web_styles_text
  assert "@container (max-width: 500px)" in web_styles_text
  assert "@media (max-width: 840px)" in web_styles_text
  assert "prefers-reduced-motion" in web_styles_text
  assert "flex-wrap: wrap" in web_styles_text

  worker_text = web_worker.read_text(encoding="utf-8")
  assert "decon-static-v9" in worker_text
  assert "/icons/decon-mark.svg" in worker_text
  assert "decon-static-v8" in worker_text
  assert "decon-static-v7" in worker_text
  assert "decon-static-v6" in worker_text
  assert "decon-static-v5" in worker_text
  assert "decon-static-v4" in worker_text
  assert "decon-static-v3" in worker_text
  assert "decon-static-v2" in worker_text
  assert "decon-static-v1" in worker_text
  assert "self.skipWaiting" in worker_text
  assert "clients.claim" in worker_text
  assert "fetch(event.request)" in worker_text
