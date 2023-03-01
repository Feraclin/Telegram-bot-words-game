from dotenv import find_dotenv, dotenv_values


if __name__ == '__main__':
    found_dotenv = find_dotenv(filename=".env")
    config_env = dotenv_values(found_dotenv)
    host = config_env.get("RABBITMQ_DEFAULT_HOST")
    port = config_env.get("RABBITMQ_DEFAULT_PORT")
    user = config_env.get("RABBITMQ_DEFAULT_USER")
    password = config_env.get("RABBITMQ_DEFAULT_PASS")
    token = config_env.get("BOT_TOKEN_TG")
    worker = Worker()