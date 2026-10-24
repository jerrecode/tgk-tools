"""Installation entrypoint: safe flags, durable default and shell syntax."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
INSTALLER=ROOT/"install.sh"


class InstallerTests(unittest.TestCase):
    def test_shell_syntax(self):
        result=subprocess.run(["sh","-n",str(INSTALLER)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_help_before_environment_or_installation(self):
        result=subprocess.run(["sh",str(INSTALLER),"--help"],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("--copy",result.stdout)
        self.assertIn("--editable",result.stdout)
        self.assertIn("default",result.stdout)

    def test_unrecognized_option_refuses_work(self):
        result=subprocess.run(["sh",str(INSTALLER),"--unknown"],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn("Unknown installation option",result.stderr)

    def test_durable_copy_is_default_and_editable_requires_opt_in(self):
        source=INSTALLER.read_text(encoding="utf-8")
        self.assertIn("INSTALL_MODE=copy",source)
        self.assertIn('if [ "$INSTALL_MODE" = copy ]; then',source)
        self.assertIn("--no-deps --force-reinstall .",source)
        self.assertIn("--no-deps --editable .",source)
        self.assertIn('"$PYTHON" -m tgk.config init',source)
        self.assertIn('"$PYTHON" -m tgk.config validate',source)
        self.assertIn('"$PYTHON" -m tgk.config audit',source)
        self.assertIn('"$PYTHON" -m tgk.install_assets',source)
        self.assertLess(source.index('"$PYTHON" -m tgk.config init'),
                        source.index('"$PYTHON" -m tgk.install_assets'))
        self.assertIn("(0, 6, 11)",source)


if __name__=="__main__":
    unittest.main()
