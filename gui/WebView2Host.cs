using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length < 1) return;
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm(args[0], args.Length > 1 ? args[1] : null));
    }
}

internal sealed class MainForm : Form
{
    private readonly WebView2 view = new WebView2();
    private readonly string url;
    private readonly string profile;

    internal MainForm(string url, string profile)
    {
        this.url = url;
        this.profile = profile;
        Text = "Link Distill";
        MinimumSize = new Size(780, 600);
        Size = new Size(1180, 780);
        StartPosition = FormStartPosition.CenterScreen;
        view.Dock = DockStyle.Fill;
        Controls.Add(view);
        Shown += Initialize;
    }

    private async void Initialize(object sender, EventArgs e)
    {
        try
        {
            var environment = await CoreWebView2Environment.CreateAsync(null, profile);
            await view.EnsureCoreWebView2Async(environment);
            view.CoreWebView2.Navigate(url);
        }
        catch (Exception)
        {
            MessageBox.Show(
                "无法启动 WebView2。请安装 Microsoft Edge WebView2 Runtime 后重试。",
                "Link Distill", MessageBoxButtons.OK, MessageBoxIcon.Error);
            Close();
        }
    }
}
