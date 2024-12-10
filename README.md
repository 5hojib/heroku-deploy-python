# Heroku Deploy GitHub Action (Python)

A GitHub Action for deploying to Heroku using Python, offering flexible deployment options.

## Features

- Deploy to Heroku using Git or Docker
- Support for custom buildpacks
- Environment file configuration
- Health check support
- Rollback on health check failure
- Comprehensive configuration options

## Inputs

### Authentication
- `heroku_api_key`: (Required) Heroku API key
- `heroku_email`: (Required) Heroku account email

### Deployment Configuration
- `heroku_app_name`: (Required) Name of the Heroku app
- `branch`: Branch to deploy (default: 'main')
- `appdir`: Subdirectory to deploy from
- `buildpack`: Heroku buildpack to use
- `usedocker`: Deploy using Docker (default: false)
- `docker_heroku_process_type`: Heroku process type for Docker (default: 'web')
- `docker_build_args`: Build arguments for Docker deployment

### Advanced Options
- `healthcheck`: URL for post-deployment health check
- `checkstring`: String to verify in health check response
- `delay`: Delay before health check (seconds)
- `env_file`: Path to environment configuration file
- `dontuseforce`: Disable force push (default: false)
- `dontautocreate`: Disable automatic app creation (default: false)
- `rollbackonhealthcheckfailed`: Rollback on health check failure (default: false)
- `region`: Heroku app region
- `stack`: Heroku app stack
- `team`: Heroku team for app creation

## Example Usage

### Basic Deployment
```yaml
- uses: yourusername/heroku-deploy-python@v1
  with:
    heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
    heroku_email: your-email@example.com
    heroku_app_name: your-app-name
```

### Docker Deployment
```yaml
- uses: yourusername/heroku-deploy-python@v1
  with:
    heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
    heroku_email: your-email@example.com
    heroku_app_name: your-docker-app
    usedocker: true
```

### Deployment with Health Check
```yaml
- uses: yourusername/heroku-deploy-python@v1
  with:
    heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
    heroku_email: your-email@example.com
    heroku_app_name: your-app-name
    healthcheck: https://your-app.herokuapp.com/health
    checkstring: "OK"
    rollbackonhealthcheckfailed: true
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.