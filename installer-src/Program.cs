using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography.X509Certificates;
using Microsoft.Win32;
using System.Windows.Forms;

internal static class Program
{
    private const string AppName = "DeTrace";
    private const string Publisher = "Roberto Raimondo";
    private const string Version = "1.0.0";

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string installDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                "DeTrace");
            string exePath = Path.Combine(installDir, "DeTrace.exe");

            StopRunningApp();
            StopRunningPythonApp();
            Directory.CreateDirectory(installDir);
            Directory.CreateDirectory(Path.Combine(installDir, ".detrace-pyi"));
            OfferCertificateTrust(installDir);
            ExtractApp(exePath);
            CreateShortcuts(exePath, installDir);
            CreateUninstaller(installDir);
            RegisterInstalledApp(exePath, installDir);
            ProcessStartInfo launchInfo = new ProcessStartInfo
            {
                FileName = exePath,
                WorkingDirectory = installDir,
                UseShellExecute = false,
                WindowStyle = ProcessWindowStyle.Maximized
            };
            if (args.Any(arg => string.Equals(arg, "--repair", StringComparison.OrdinalIgnoreCase)))
            {
                launchInfo.Environment["DETRACE_FORCE_REPAIR_SETUP"] = "1";
            }
            Process.Start(launchInfo);
            return 0;
        }
        catch (Exception ex)
        {
            ShowMessage("DeTrace setup failed", ex.Message);
            return 1;
        }
    }

    private static void StopRunningApp()
    {
        foreach (Process process in Process.GetProcessesByName("DeTrace"))
        {
            try
            {
                process.Kill(true);
                process.WaitForExit(10000);
            }
            catch
            {
                // Continue setup even if an old process already exited or cannot be queried.
            }
            finally
            {
                process.Dispose();
            }
        }
    }

    private static void StopRunningPythonApp()
    {
        string dataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "DeTrace");
        string command = "$data = '" + EscapeForPowerShell(dataDir) + "'; " +
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and " +
            "($_.CommandLine -like ('*' + $data + '*') -and " +
            "($_.CommandLine -like '*desktop_window.py*' -or $_.CommandLine -like '*server.py*')) } | " +
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }";
        using Process process = Process.Start(new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoProfile -ExecutionPolicy Bypass -Command \"" + command + "\"",
            UseShellExecute = false,
            CreateNoWindow = true
        })!;
        process.WaitForExit(10000);
    }

    private static void ExtractApp(string exePath)
    {
        using Stream? payload = Assembly.GetExecutingAssembly().GetManifestResourceStream("DeTrace.exe");
        if (payload is null)
        {
            throw new InvalidOperationException("The installer payload is missing.");
        }

        string tempPath = exePath + ".new";
        using (FileStream output = File.Create(tempPath))
        {
            payload.CopyTo(output);
        }

        if (File.Exists(exePath))
        {
            File.Replace(tempPath, exePath, null);
        }
        else
        {
            File.Move(tempPath, exePath);
        }
    }

    private static void CreateShortcuts(string exePath, string installDir)
    {
        string startMenuDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            "DeTrace");
        Directory.CreateDirectory(startMenuDir);

        CreateShortcut(Path.Combine(startMenuDir, "DeTrace.lnk"), exePath, installDir, "Launch DeTrace");
        CreateShortcut(
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "DeTrace.lnk"),
            exePath,
            installDir,
            "Launch DeTrace");
    }

    private static void CreateShortcut(string shortcutPath, string targetPath, string workingDirectory, string description)
    {
        Type? shellType = Type.GetTypeFromProgID("WScript.Shell");
        if (shellType is null)
        {
            return;
        }

        object? shell = Activator.CreateInstance(shellType);
        if (shell is null)
        {
            return;
        }

        object? shortcut = shellType.InvokeMember(
            "CreateShortcut",
            BindingFlags.InvokeMethod,
            null,
            shell,
            new object[] { shortcutPath });
        if (shortcut is null)
        {
            return;
        }

        Type shortcutType = shortcut.GetType();
        shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath });
        shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut, new object[] { workingDirectory });
        shortcutType.InvokeMember("Description", BindingFlags.SetProperty, null, shortcut, new object[] { description });
        shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, Array.Empty<object>());

        Marshal.FinalReleaseComObject(shortcut);
        Marshal.FinalReleaseComObject(shell);
    }

    private static void CreateUninstaller(string installDir)
    {
        string scriptPath = Path.Combine(installDir, "Uninstall-DeTrace.ps1");
        string dataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "DeTrace");
        string startMenuDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            "DeTrace");
        string desktopShortcut = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "DeTrace.lnk");
        string uninstallKey = @"HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DeTrace";

        string script = "$ErrorActionPreference = 'SilentlyContinue'\r\n" +
            "Get-Process DeTrace -ErrorAction SilentlyContinue | Stop-Process -Force\r\n" +
            "Remove-Item -LiteralPath '" + EscapeForPowerShell(desktopShortcut) + "' -Force\r\n" +
            "Remove-Item -LiteralPath '" + EscapeForPowerShell(startMenuDir) + "' -Recurse -Force\r\n" +
            "Remove-Item -LiteralPath '" + uninstallKey + "' -Recurse -Force\r\n" +
            "Remove-Item -LiteralPath '" + EscapeForPowerShell(dataDir) + "' -Recurse -Force\r\n" +
            "$target = '" + EscapeForPowerShell(installDir) + "'\r\n" +
            "Start-Process -FilePath cmd.exe -WindowStyle Hidden -ArgumentList '/c timeout /t 2 /nobreak >nul & rmdir /s /q \"' + $target + '\"'\r\n";
        File.WriteAllText(scriptPath, script);
    }

    private static void RegisterInstalledApp(string exePath, string installDir)
    {
        string uninstallScript = Path.Combine(installDir, "Uninstall-DeTrace.ps1");
        string uninstallCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"" + uninstallScript + "\"";
        using RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\DeTrace");
        key.SetValue("DisplayName", AppName, RegistryValueKind.String);
        key.SetValue("DisplayVersion", Version, RegistryValueKind.String);
        key.SetValue("Publisher", Publisher, RegistryValueKind.String);
        key.SetValue("InstallLocation", installDir, RegistryValueKind.String);
        key.SetValue("DisplayIcon", exePath, RegistryValueKind.String);
        key.SetValue("UninstallString", uninstallCommand, RegistryValueKind.String);
        key.SetValue("QuietUninstallString", uninstallCommand, RegistryValueKind.String);
        key.SetValue("NoModify", 1, RegistryValueKind.DWord);
        key.SetValue("NoRepair", 1, RegistryValueKind.DWord);

        long sizeBytes = Directory.Exists(installDir)
            ? Directory.EnumerateFiles(installDir, "*", SearchOption.AllDirectories).Sum(path => new FileInfo(path).Length)
            : 0;
        key.SetValue("EstimatedSize", Math.Max(1, sizeBytes / 1024), RegistryValueKind.DWord);
    }

    private static void OfferCertificateTrust(string installDir)
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        DialogResult result = MessageBox.Show(
            "DeTrace can export the public signing certificate from this setup file and trust it for the current Windows user.\r\n\r\n" +
            "This helps Windows recognize DeTrace files signed by the same build certificate. The private signing key is not included or installed.\r\n\r\n" +
            "Install the DeTrace publisher certificate for this user?",
            "Trust DeTrace publisher certificate",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question,
            MessageBoxDefaultButton.Button2);

        if (result != DialogResult.Yes)
        {
            return;
        }

        try
        {
            string setupPath = Environment.ProcessPath ?? Assembly.GetExecutingAssembly().Location;
            X509Certificate2 certificate = new X509Certificate2(X509Certificate.CreateFromSignedFile(setupPath));
            string certificatePath = Path.Combine(installDir, "DeTrace-CodeSigning.cer");
            File.WriteAllBytes(certificatePath, certificate.Export(X509ContentType.Cert));

            TrustCertificateForCurrentUser(certificate, StoreName.Root);
            TrustCertificateForCurrentUser(certificate, StoreName.TrustedPublisher);

            MessageBox.Show(
                "The DeTrace public signing certificate was saved and trusted for the current user:\r\n\r\n" + certificatePath,
                "DeTrace certificate installed",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "DeTrace setup will continue, but the publisher certificate could not be installed.\r\n\r\n" + ex.Message,
                "Certificate install skipped",
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning);
        }
    }

    private static void TrustCertificateForCurrentUser(X509Certificate2 certificate, StoreName storeName)
    {
        using X509Store store = new X509Store(storeName, StoreLocation.CurrentUser);
        store.Open(OpenFlags.ReadWrite);
        X509Certificate2Collection existing = store.Certificates.Find(
            X509FindType.FindByThumbprint,
            certificate.Thumbprint,
            validOnly: false);
        if (existing.Count == 0)
        {
            store.Add(certificate);
        }
    }

    private static void ShowMessage(string title, string message)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoProfile -Command \"Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('" +
                EscapeForPowerShell(message) + "', '" + EscapeForPowerShell(title) + "')\"",
            UseShellExecute = false,
            CreateNoWindow = true
        })?.WaitForExit();
    }

    private static string EscapeForPowerShell(string value)
    {
        return value.Replace("'", "''");
    }
}
