import os
import sys
import time
import requests
import subprocess
import dotenv

def create_netrc_file(email, api_key):
    """Create .netrc file for Heroku authentication."""
    netrc_content = f"""machine api.heroku.com
    login {email}
    password {api_key}
machine git.heroku.co
    login {email}
    password {api_key}
"""
    netrc_path = os.path.expanduser('~/.netrc')
    with open(netrc_path, 'w') as f:
        f.write(netrc_content)
    os.chmod(netrc_path, 0o600)
    print("Created and wrote to ~/.netrc")

def add_remote(app_name, dontautocreate=False, buildpack=None, region=None, team=None, stack=None):
    """Add Heroku git remote or create Heroku app if not exists."""
    try:
        subprocess.run(['heroku', 'git:remote', '--app', app_name], check=True)
        print("Added git remote heroku")
    except subprocess.CalledProcessError:
        if dontautocreate:
            raise

        create_command = ['heroku', 'create', app_name]
        if buildpack:
            create_command.extend(['--buildpack', buildpack])
        if region:
            create_command.extend(['--region', region])
        if stack:
            create_command.extend(['--stack', stack])
        if team:
            create_command.extend(['--team', team])

        subprocess.run(create_command, check=True)

def add_config(app_name, env_file=None, appdir=None):
    """Add configuration variables to Heroku app."""
    config_vars = []

    # Add config vars from environment variables starting with HD_
    for key, value in os.environ.items():
        if key.startswith('HD_'):
            config_vars.append(f"{key[3:]}='{value}'")

    # Add config vars from env_file if provided
    if env_file:
        env_path = os.path.join(appdir or '', env_file)
        env_config = dotenv.dotenv_values(env_path)
        config_vars.extend([f"{k}={v}" for k, v in env_config.items()])

    if config_vars:
        subprocess.run(['heroku', 'config:set', f'--app={app_name}'] + config_vars, check=True)

def create_procfile(procfile, appdir=None):
    """Create Procfile if specified."""
    if procfile:
        procfile_path = os.path.join(appdir or '', 'Procfile')
        with open(procfile_path, 'w') as f:
            f.write(procfile)
        
        subprocess.run(['git', 'add', '-A'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Added Procfile'], check=True)
        print("Written Procfile with custom configuration")

def run_command(command, cwd=None, check=True):
    """Run a command with real-time output."""
    process = subprocess.Popen(
        command, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        cwd=cwd
    )

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())

    stderr = process.stderr.read()
    if stderr:
        print(stderr, file=sys.stderr)

    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)

def deploy(
    app_name, 
    branch='main', 
    dontuseforce=False, 
    usedocker=False, 
    dockerHerokuProcessType=None, 
    dockerBuildArgs=None, 
    appdir=None
):
    """Deploy application to Heroku."""
    force = '' if dontuseforce else '--force'

    if usedocker:
        run_command(f'heroku stack:set container --app {app_name}')
        run_command(
            f'heroku container:push {dockerHerokuProcessType} --app {app_name} {dockerBuildArgs or ""}', 
            cwd=appdir
        )
        run_command(
            f'heroku container:release {dockerHerokuProcessType} --app {app_name}', 
            cwd=appdir
        )
    else:
        remote_branch = subprocess.check_output(
            "git remote show heroku | grep 'HEAD' | cut -d':' -f2 | sed -e 's/^ *//g' -e 's/ *$//g'", 
            shell=True
        ).decode().strip()

        if remote_branch == 'master':
            run_command('heroku plugins:install heroku-repo')
            run_command(f'heroku repo:reset -a {app_name}')

        if not appdir:
            run_command(f'git push heroku {branch}:refs/heads/main {force}')
        else:
            run_command(
                f'git push {force} heroku `git subtree split --prefix={appdir} {branch}`:refs/heads/main'
            )

def health_check(
    app_name, 
    healthcheck=None, 
    checkstring=None, 
    delay=0, 
    rollbackonhealthcheckfailed=False,
    appdir=None
):
    """Perform health check on deployed application."""
    if healthcheck:
        time.sleep(delay)
        try:
            response = requests.get(healthcheck)
            if (response.status_code != 200 or 
                (checkstring and checkstring not in response.text)):
                return handle_health_check_failure(
                    app_name, 
                    rollbackonhealthcheckfailed, 
                    appdir
                )
        except requests.RequestException:
            return handle_health_check_failure(
                app_name, 
                rollbackonhealthcheckfailed, 
                appdir
            )

def handle_health_check_failure(app_name, rollbackonhealthcheckfailed=False, appdir=None):
    """Handle health check failure."""
    if rollbackonhealthcheckfailed:
        subprocess.run(['heroku', 'rollback', f'--app={app_name}'], cwd=appdir, check=True)
        print("Health Check Failed. Deployment rolled back.")
        sys.exit(1)
    else:
        print("Health Check Failed. Check Heroku logs.")
        sys.exit(1)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Heroku Deploy GitHub Action')
    parser.add_argument('--heroku_api_key', required=True)
    parser.add_argument('--heroku_email', required=True)
    parser.add_argument('--heroku_app_name', required=True)
    parser.add_argument('--buildpack', default=None)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--dontuseforce', type=bool, default=False)
    parser.add_argument('--dontautocreate', type=bool, default=False)
    parser.add_argument('--usedocker', type=bool, default=False)
    parser.add_argument('--docker_heroku_process_type', default=None)
    parser.add_argument('--docker_build_args', default=None)
    parser.add_argument('--appdir', default=None)
    parser.add_argument('--healthcheck', default=None)
    parser.add_argument('--checkstring', default=None)
    parser.add_argument('--delay', type=int, default=0)
    parser.add_argument('--procfile', default=None)
    parser.add_argument('--rollbackonhealthcheckfailed', type=bool, default=False)
    parser.add_argument('--env_file', default=None)
    parser.add_argument('--justlogin', type=bool, default=False)
    parser.add_argument('--region', default=None)
    parser.add_argument('--stack', default=None)
    parser.add_argument('--team', default=None)

    args = parser.parse_args()

    try:
        # Just login
        if args.justlogin:
            create_netrc_file(args.heroku_email, args.heroku_api_key)
            return

        # Git configuration
        subprocess.run(['git', 'config', 'user.name', 'Heroku-Deploy'], check=True)
        subprocess.run(['git', 'config', 'user.email', args.heroku_email], check=True)

        # Commit any uncommitted changes
        git_status = subprocess.check_output(['git', 'status', '--porcelain']).decode().strip()
        if git_status:
            subprocess.run(['git', 'add', '-A'], check=True)
            subprocess.run(['git', 'commit', '-m', 'Committed changes from previous actions'], check=True)

        # Check for shallow repository
        if not args.usedocker:
            is_shallow = subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository']).decode().strip()
            if is_shallow == 'true':
                subprocess.run(['git', 'fetch', '--prune', '--unshallow'], check=True)

        # Create .netrc file
        create_netrc_file(args.heroku_email, args.heroku_api_key)

        # Create Procfile
        create_procfile(args.procfile, args.appdir)

        # Docker login if using Docker
        if args.usedocker:
            run_command('heroku container:login')

        # Add remote and config
        add_remote(
            args.heroku_app_name, 
            args.dontautocreate, 
            args.buildpack, 
            args.region, 
            args.team, 
            args.stack
        )
        add_config(args.heroku_app_name, args.env_file, args.appdir)

        # Deploy
        try:
            deploy(
                args.heroku_app_name, 
                args.branch, 
                True, 
                args.usedocker, 
                args.docker_heroku_process_type, 
                args.docker_build_args, 
                args.appdir
            )
        except subprocess.CalledProcessError:
            print("Unable to push branch. Using force deploy.")
            deploy(
                args.heroku_app_name, 
                args.branch, 
                args.dontuseforce, 
                args.usedocker, 
                args.docker_heroku_process_type, 
                args.docker_build_args, 
                args.appdir
            )

        # Health check
        health_check(
            args.heroku_app_name, 
            args.healthcheck, 
            args.checkstring, 
            args.delay, 
            args.rollbackonhealthcheckfailed, 
            args.appdir
        )

    except Exception as error:
        print(f"Deployment failed: {error}")
        sys.exit(1)

if __name__ == '__main__':
    main()