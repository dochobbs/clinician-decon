import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
  private let serverURL = URL(string: "http://127.0.0.1:8769/")!
  private let statusURL = URL(string: "http://127.0.0.1:8769/api/setup/status")!

  private var window: NSWindow!
  private var webView: WKWebView!
  private var statusLabel: NSTextField!
  private var detailLabel: NSTextField!
  private var launcherProcess: Process?
  private var pollTimer: Timer?
  private var serverMonitorTimer: Timer?
  private var didLoadApp = false
  private var serverMissCount = 0
  private lazy var nativeLogURL: URL = {
    let logsDir = FileManager.default.homeDirectoryForCurrentUser
      .appendingPathComponent("Library/Application Support/Clinician Decon/logs", isDirectory: true)
    try? FileManager.default.createDirectory(at: logsDir, withIntermediateDirectories: true)
    return logsDir.appendingPathComponent("native.log")
  }()

  func applicationDidFinishLaunching(_ notification: Notification) {
    logNative("applicationDidFinishLaunching")
    NSApp.setActivationPolicy(.regular)
    buildMenu()
    buildWindow()
    startLauncher()
    startPolling()
  }

  func applicationWillTerminate(_ notification: Notification) {
    logNative("applicationWillTerminate")
    stopLocalServer()
  }

  func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
    true
  }

  private func buildMenu() {
    let mainMenu = NSMenu()
    let appMenuItem = NSMenuItem()
    mainMenu.addItem(appMenuItem)

    let appMenu = NSMenu()
    appMenu.addItem(NSMenuItem(
      title: "Open in Browser",
      action: #selector(openInBrowser(_:)),
      keyEquivalent: "b"
    ))
    appMenu.addItem(.separator())
    appMenu.addItem(NSMenuItem(
      title: "Quit Clinician Decon",
      action: #selector(NSApplication.terminate(_:)),
      keyEquivalent: "q"
    ))
    appMenuItem.submenu = appMenu
    NSApp.mainMenu = mainMenu
  }

  private func buildWindow() {
    let configuration = WKWebViewConfiguration()
    configuration.websiteDataStore = .default()
    configuration.userContentController.add(self, name: "deconNative")

    webView = WKWebView(frame: .zero, configuration: configuration)
    webView.navigationDelegate = self
    webView.uiDelegate = self
    webView.translatesAutoresizingMaskIntoConstraints = false
    webView.isHidden = true

    statusLabel = NSTextField(labelWithString: "Starting Clinician Decon")
    statusLabel.font = NSFont.systemFont(ofSize: 22, weight: .semibold)
    statusLabel.alignment = .center

    detailLabel = NSTextField(labelWithString: "Loading the local privacy engine on this Mac.")
    detailLabel.font = NSFont.systemFont(ofSize: 14)
    detailLabel.textColor = .secondaryLabelColor
    detailLabel.alignment = .center

    let statusStack = NSStackView(views: [statusLabel, detailLabel])
    statusStack.orientation = .vertical
    statusStack.alignment = .centerX
    statusStack.spacing = 10
    statusStack.translatesAutoresizingMaskIntoConstraints = false

    let contentView = NSView()
    contentView.wantsLayer = true
    contentView.layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
    contentView.addSubview(webView)
    contentView.addSubview(statusStack)

    NSLayoutConstraint.activate([
      webView.leadingAnchor.constraint(equalTo: contentView.leadingAnchor),
      webView.trailingAnchor.constraint(equalTo: contentView.trailingAnchor),
      webView.topAnchor.constraint(equalTo: contentView.topAnchor),
      webView.bottomAnchor.constraint(equalTo: contentView.bottomAnchor),

      statusStack.centerXAnchor.constraint(equalTo: contentView.centerXAnchor),
      statusStack.centerYAnchor.constraint(equalTo: contentView.centerYAnchor),
      statusStack.leadingAnchor.constraint(greaterThanOrEqualTo: contentView.leadingAnchor, constant: 32),
      statusStack.trailingAnchor.constraint(lessThanOrEqualTo: contentView.trailingAnchor, constant: -32),
    ])

    window = NSWindow(
      contentRect: NSRect(x: 0, y: 0, width: 1280, height: 860),
      styleMask: [.titled, .closable, .miniaturizable, .resizable],
      backing: .buffered,
      defer: false
    )
    window.title = "Clinician Decon"
    window.minSize = NSSize(width: 980, height: 680)
    window.contentView = contentView
    window.center()
    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
  }

  private func startLauncher() {
    guard let executableDir = Bundle.main.executableURL?.deletingLastPathComponent() else {
      showLaunchFailure("The app bundle is missing its executable directory.")
      return
    }

    let launcherURL = executableDir.appendingPathComponent("clinician-decon-launcher")
    logNative("resolved launcher: \(launcherURL.path)")
    guard FileManager.default.isExecutableFile(atPath: launcherURL.path) else {
      showLaunchFailure("The app bundle is missing its local server launcher.")
      return
    }

    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/bin/zsh")
    process.arguments = [launcherURL.path]
    var environment = ProcessInfo.processInfo.environment
    environment["DECON_NO_BROWSER"] = "1"
    process.environment = environment
    process.terminationHandler = { [weak self] _ in
      DispatchQueue.main.async {
        guard let self else { return }
        if !self.didLoadApp {
          self.logNative("launcher terminated before app loaded")
          self.showLaunchFailure("The local privacy engine stopped before the app was ready.")
        }
      }
    }

    do {
      try process.run()
      logNative("launcher started pid \(process.processIdentifier)")
      launcherProcess = process
    } catch {
      logNative("launcher failed: \(error.localizedDescription)")
      showLaunchFailure("The local privacy engine could not start: \(error.localizedDescription)")
    }
  }

  private func startPolling() {
    pollTimer?.invalidate()
    pollTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
      self?.checkServer()
    }
    checkServer()
  }

  private func checkServer() {
    var request = URLRequest(url: statusURL)
    request.cachePolicy = .reloadIgnoringLocalCacheData
    request.timeoutInterval = 1.5

    URLSession.shared.dataTask(with: request) { [weak self] _, response, _ in
      guard let self else { return }
      guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
        return
      }
      DispatchQueue.main.async {
        self.logNative("setup status ready")
        self.loadLocalApp()
      }
    }.resume()
  }

  private func loadLocalApp() {
    guard !didLoadApp else { return }
    logNative("loading local app")
    didLoadApp = true
    pollTimer?.invalidate()
    pollTimer = nil
    startServerMonitor()
    webView.isHidden = false
    statusLabel.isHidden = true
    detailLabel.isHidden = true

    var request = URLRequest(url: serverURL)
    request.cachePolicy = .reloadIgnoringLocalCacheData
    webView.load(request)
  }

  private func showLaunchFailure(_ message: String) {
    logNative("launch failure: \(message)")
    pollTimer?.invalidate()
    pollTimer = nil
    serverMonitorTimer?.invalidate()
    serverMonitorTimer = nil
    webView.isHidden = true
    statusLabel.stringValue = "Clinician Decon did not start"
    detailLabel.stringValue = message
    detailLabel.textColor = .systemRed
  }

  private func stopLocalServer() {
    logNative("stopping local server")
    pollTimer?.invalidate()
    pollTimer = nil
    serverMonitorTimer?.invalidate()
    serverMonitorTimer = nil

    var request = URLRequest(url: URL(string: "http://127.0.0.1:8769/api/shutdown")!)
    request.httpMethod = "POST"
    request.timeoutInterval = 1.0
    let semaphore = DispatchSemaphore(value: 0)
    URLSession.shared.dataTask(with: request) { _, _, _ in
      semaphore.signal()
    }.resume()
    _ = semaphore.wait(timeout: .now() + 1.5)

    if let process = launcherProcess, process.isRunning {
      logNative("terminating launcher pid \(process.processIdentifier)")
      process.terminate()
    }
  }

  private func startServerMonitor() {
    serverMissCount = 0
    serverMonitorTimer?.invalidate()
    serverMonitorTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
      self?.checkServerStillRunning()
    }
  }

  private func checkServerStillRunning() {
    var request = URLRequest(url: statusURL)
    request.cachePolicy = .reloadIgnoringLocalCacheData
    request.timeoutInterval = 1.0

    URLSession.shared.dataTask(with: request) { [weak self] _, response, _ in
      guard let self else { return }
      let isRunning = (response as? HTTPURLResponse)?.statusCode == 200
      DispatchQueue.main.async {
        if isRunning {
          self.serverMissCount = 0
          return
        }
        self.serverMissCount += 1
        if self.serverMissCount >= 2 {
          self.logNative("local server stopped; terminating native app")
          NSApp.terminate(nil)
        }
      }
    }.resume()
  }

  @objc private func openInBrowser(_ sender: Any?) {
    logNative("opening local app in browser")
    NSWorkspace.shared.open(serverURL)
  }

  private func logNative(_ message: String) {
    let line = "\(ISO8601DateFormatter().string(from: Date())) \(message)\n"
    guard let data = line.data(using: .utf8) else { return }
    if FileManager.default.fileExists(atPath: nativeLogURL.path),
       let handle = try? FileHandle(forWritingTo: nativeLogURL) {
      defer { try? handle.close() }
      _ = try? handle.seekToEnd()
      try? handle.write(contentsOf: data)
    } else {
      try? data.write(to: nativeLogURL, options: .atomic)
    }
  }

  func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
    guard message.name == "deconNative" else { return }
    if let body = message.body as? [String: Any],
       let action = body["action"] as? String {
      switch action {
      case "quit":
        logNative("received web quit message")
        NSApp.terminate(nil)
      case "openBrowser":
        openInBrowser(nil)
      default:
        logNative("ignored web message action: \(action)")
      }
    }
  }

  func webView(
    _ webView: WKWebView,
    decidePolicyFor navigationAction: WKNavigationAction,
    decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
  ) {
    if let url = navigationAction.request.url,
       let host = url.host,
       host != "127.0.0.1",
       host != "localhost" {
      NSWorkspace.shared.open(url)
      decisionHandler(.cancel)
      return
    }
    decisionHandler(.allow)
  }

  func webView(
    _ webView: WKWebView,
    createWebViewWith configuration: WKWebViewConfiguration,
    for navigationAction: WKNavigationAction,
    windowFeatures: WKWindowFeatures
  ) -> WKWebView? {
    if let url = navigationAction.request.url {
      NSWorkspace.shared.open(url)
    }
    return nil
  }
}

@main
struct ClinicianDeconMain {
  private static var retainedDelegate: AppDelegate?

  static func main() {
    let app = NSApplication.shared
    let delegate = AppDelegate()
    retainedDelegate = delegate
    app.delegate = delegate
    app.setActivationPolicy(.regular)
    app.run()
  }
}
