import re
import tomllib

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
import requests
import json

class MaxKB(PluginBase):
    description = "MaxKB"
    author = "yxj"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/MaxKB/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        config = plugin_config["MaxKB"]
        main_config = main_config["XYBot"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.version = main_config["version"]
        self.base_url = config["base_url"]
        self.authorization = config["authorization"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in self.command:
            return
        
        payload = json.dumps({
            "message": content,
            "stream": False
        })
        headers = {
            'Authorization': self.authorization,
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", self.base_url, headers=headers, data=payload)
        response_data = json.loads(response.text)
        content = response_data["data"]["content"]
        content = re.sub(r'<details>.*?</details>', '', content)
        if response_data["code"] == 200:
            out_message = (f"{content}")
        else:
            out_message = (f"{response_data['message']}")   
        await bot.send_text_message(message.get("FromWxid"), out_message)

    @on_at_message
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = re.split(r'[\s\u2005]+', content)
        
        if len(command) < 2 or command[1] not in self.command:
            return
        
        payload = json.dumps({
            "message": content,
            "stream": False
        })
        headers = {
            'Authorization': self.authorization,
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", self.base_url, headers=headers, data=payload)
        response_data = json.loads(response.text)
        content = response_data["data"]["content"]
        content = re.sub(r'<details>.*?</details>', '', content)
        if response_data["code"] == 200:
            out_message = (f"{content}")
        else:
            out_message = (f"{response_data['message']}")
        await bot.send_text_message(message.get("FromWxid"), out_message)
