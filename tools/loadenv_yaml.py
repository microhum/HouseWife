import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load YAML file
with open('lavalink/application_template.yml', 'r') as file:
    config = yaml.safe_load(file)

# Replace placeholders in YAML with environment variables
def replace_placeholders(config):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, value)
            else:
                replace_placeholders(value)
    elif isinstance(config, list):
        for index, item in enumerate(config):
            if isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                env_var = item[2:-1]
                config[index] = os.getenv(env_var, item)
            else:
                replace_placeholders(item)

replace_placeholders(config)

# Check for production mode and change address if needed
if os.getenv('MODE', 'production') == 'production':
    if 'server' in config and 'address' in config['server']:
        config['server']['address'] = '127.0.0.1'

# Save the updated YAML file
with open('lavalink/application.yml', 'w') as file:
    yaml.safe_dump(config, file)

print("YAML file has been updated with environment variables.")