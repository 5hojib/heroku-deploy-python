import argparse
import os
import subprocess
import sys
# import dotenv


def run_command(command, cwd=None, check=True):
    """Run a command with real-time output."""
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
    )

    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip())

    stderr = process.stderr.read()
    if stderr:
        print(stderr, file=sys.stderr)

    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)


def create_netrc_file(email, api_key):
    """Create .netrc file for Heroku authentication."""
    netrc_content = f"""machine api.heroku.com
    login {email}
    password {api_key}
machine git.heroku.com
    login {email}
    password {api_key}
"""
    netrc_path = os.path.expanduser("~/.netrc")
    with open(netrc_path, "w") as f:
        f.write(netrc_content)
    os.chmod(netrc_path, 0o600)
    print("Created and wrote to ~/.netrc")


def add_remote(args):
    """Add Heroku git remote or create Heroku app if not exists."""
    try:
        subprocess.run(["heroku", "git:remote", "--app", args.app_name], check=True)
        print("Added git remote heroku")
    except subprocess.CalledProcessError:
        if args.dontautocreate:
            raise

        create_command = ["heroku", "create", args.app_name]
        if args.buildpack:
            create_command.extend(["--buildpack", args.buildpack])
        if args.region:
            create_command.extend(["--region", args.region])
        if args.stack:
            create_command.extend(["--stack", args.stack])
        if args.team:
            create_command.extend(["--team", args.team])

        subprocess.run(create_command, check=True)


def add_config(args):
    """Add configuration variables to Heroku app."""
    config_vars = []

    # Add config vars from environment variables starting with HD_
    for key, value in os.environ.items():
        if key.startswith("HD_"):
            config_vars.append(f"{key[3:]}='{value}'")

    # Add config vars from env_file if provided
    # if args.env_file:
    #     env_path = os.path.join(args.appdir or "", args.env_file)
    #     env_config = dotenv.dotenv_values(env_path)
    #     config_vars.extend([f"{k}={v}" for k, v in env_config.items()])

    if config_vars:
        subprocess.run(
            ["heroku", "config:set", f"--app={args.app_name}"] + config_vars,
            check=True,
        )


def create_procfile(args):
    """Create Procfile if specified."""
    if args.procfile:
        procfile_path = os.path.join(args.appdir or "", "Procfile")
        with open(procfile_path, "w") as f:
            f.write(args.procfile)

        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-m", "Added Procfile"], check=True)
        print("Written Procfile with custom configuration")


def deploy(args):
    """Deploy application to Heroku."""
    force = "--force"

    if args.usedocker:
        run_command(f"heroku stack:set container --app {args.app_name}")
        run_command(
            f"heroku container:push {args.docker_process_type} --app {args.app_name} {args.docker_build_args or ''}",
            cwd=args.appdir,
        )
        run_command(
            f"heroku container:release {args.docker_process_type} --app {args.app_name}",
            cwd=args.appdir,
        )
    else:
        remote_branch = subprocess.check_output(
            "git remote show heroku | grep 'HEAD' | cut -d':' -f2 | sed -e 's/^ *//g' -e 's/ *$//g'",
            shell=True,
        ).decode().strip()

        if remote_branch == "master":
            run_command("heroku plugins:install heroku-repo")
            run_command(f"heroku repo:reset -a {args.app_name}")

        run_command(f"git push heroku {args.branch}:{remote_branch} {force}")


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", type=str, required=True, help="Heroku account email")
    parser.add_argument("--api_key", type=str, required=True, help="Heroku API key")
    parser.add_argument("--app_name", type=str, required=True, help="Heroku app name")
    parser.add_argument("--branch", type=str, default="main", help="Git branch to deploy")
    # parser.add_argument("--dontuseforce", action="store_true", help="Avoid using force push")
    parser.add_argument("--usedocker", type=str2bool, required=False, help="Deploy using Docker")
    parser.add_argument("--docker_process_type", type=str, default=None, help="Docker process type")
    parser.add_argument("--docker_build_args", type=str, default=None, help="Docker build arguments")
    # parser.add_argument("--env_file", type=str, default=None, help="Environment file path")
    parser.add_argument("--appdir", type=str, default=None, help="Application directory")
    parser.add_argument("--dontautocreate", action="store_true", help="Avoid auto-creating the app")
    parser.add_argument("--buildpack", type=str, default=None, help="Heroku buildpack")
    parser.add_argument("--region", type=str, default=None, help="Heroku app region")
    parser.add_argument("--team", type=str, default=None, help="Heroku team")
    parser.add_argument("--stack", type=str, default=None, help="Heroku stack")
    parser.add_argument("--procfile", type=str, default=None, help="Procfile content")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_netrc_file(args.email, args.api_key)
    add_remote(args)
    add_config(args)
    create_procfile(args)
    deploy(args)