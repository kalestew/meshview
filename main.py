import asyncio
import argparse
import configparser
from meshview import mqtt_reader
from meshview import database
from meshview import mqtt_store
from meshview import web
from meshview import http
from meshview import models
import json



async def load_database_from_mqtt(mqtt_server: str , mqtt_port: int, topic: list, mqtt_user: str | None = None, mqtt_passwd: str | None = None):
    async for topic, env in mqtt_reader.get_topic_envelopes(mqtt_server, mqtt_port, topic, mqtt_user, mqtt_passwd):
        await mqtt_store.process_envelope(topic, env)


async def main(config):
    database.init_database(config["database"]["connection_string"])

    await database.create_tables()
    mqtt_user = None
    mqtt_passwd = None
    if config["mqtt"]["username"] != "":
        mqtt_user: str = config["mqtt"]["username"]
    if config["mqtt"]["password"] != "":
        mqtt_passwd: str = config["mqtt"]["password"]
    mqtt_topics = json.loads(config["mqtt"]["topics"])
    
    # Create database with site configuration
    async with database.async_session() as session:
        site_config = models.SiteConfig(
            site_domain = config["site"]["domain"],
            site_title = config["site"]["title"],
            site_message = config["site"]["message"]
        )

        session.add(site_config)
        # print("Site configuration loaded to database")

    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            web.run_server(
                config["server"]["bind"],
                int(config["server"]["port"]),
                config["server"].get("tls_cert"),
            )
        )

def load_config(file_path):
    """Load configuration from an INI-style text file."""
    config_parser = configparser.ConfigParser()
    config_parser.read(file_path)

    # Convert to a dictionary for easier access
    config = {section: dict(config_parser.items(section)) for section in config_parser.sections()}
    return config



if __name__ == '__main__':
    parser = argparse.ArgumentParser("meshview")
    parser.add_argument("--config", help="Path to the configuration file.", default="config.ini")
    args = parser.parse_args()

    config = load_config(args.config)

    asyncio.run(main(config))