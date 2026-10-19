using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

// Community portable launcher. No registry writes and no global environment changes.
internal static class CaprinePortable
{
    private static string Quote(string arg)
    {
        if (arg.Length > 0 && arg.IndexOfAny(new char[] { ' ', '\t', '\n', '"' }) < 0)
            return arg;
        var output = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in arg)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"')
            {
                output.Append('\\', slashes * 2 + 1);
                output.Append('"');
                slashes = 0;
                continue;
            }
            output.Append('\\', slashes);
            slashes = 0;
            output.Append(c);
        }
        output.Append('\\', slashes * 2);
        output.Append('"');
        return output.ToString();
    }

    [STAThread]
    private static int Main(string[] args)
    {
        string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        string exe = Path.Combine(root, @"App\Caprine\Caprine.exe");
        string data = Path.Combine(root, @"Data\Caprine");
        string temp = Path.Combine(root, @"Data\Temp");
        try
        {
            if (!File.Exists(exe))
            {
                MessageBox.Show("Missing App\\Caprine\\Caprine.exe. Extract the entire portable ZIP.", "Caprine Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }
            Directory.CreateDirectory(data);
            Directory.CreateDirectory(temp);
            var info = new ProcessStartInfo(exe);
            info.UseShellExecute = false;
            info.WorkingDirectory = Path.GetDirectoryName(exe);
            info.EnvironmentVariables["CAPRINE_PORTABLE_DATA_DIR"] = data;
            info.EnvironmentVariables["TEMP"] = temp;
            info.EnvironmentVariables["TMP"] = temp;
            var command = new StringBuilder();
            foreach (var arg in args)
            {
                if (command.Length > 0) command.Append(' ');
                command.Append(Quote(arg));
            }
            info.Arguments = command.ToString();
            using (var child = Process.Start(info))
            {
                if (child == null) return 3;
                child.WaitForExit();
                return child.ExitCode;
            }
        }
        catch (Exception e)
        {
            MessageBox.Show(e.Message, "Caprine Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
