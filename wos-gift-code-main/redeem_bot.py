import hashlib
import json
import time
from os.path import exists

import requests
from requests.adapters import HTTPAdapter, Retry

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot 已啟動，登入為：{bot.user}')

async def redeem_code(code, player_file="player.json", results_file="results.json", restart=False):
    try:
        # 開啟玩家檔案
        with open(player_file, encoding="utf-8") as player_file:
            players = json.loads(player_file.read())

        # 初始化結果
        results = []
        if exists(results_file):
            with open(results_file, encoding="utf-8") as results_file:
                results = json.loads(results_file.read())

        # 檢查是否有相同的兌換碼
        found_item = next((result for result in results if result["code"] == code), None)
        if found_item is None:
            print(f"新兌換碼: {code}，新增到結果檔案並處理。")
            new_item = {"code": code, "status": {}}
            results.append(new_item)
            result = new_item
        else:
            result = found_item

        URL = "https://wos-giftcode-api.centurygame.com/api"
        SALT = "tB87#kPtkxqOS2"
        HTTP_HEADER = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        r = requests.Session()
        retry_config = Retry(total=5, backoff_factor=1, status_forcelist=[429], allowed_methods=False)
        r.mount("https://", HTTPAdapter(max_retries=retry_config))

        counter_successfully_claimed = 0
        counter_already_claimed = 0
        counter_error = 0

        for i, player in enumerate(players, start=1):
            print(f"\x1b[K{i}/{len(players)} complete. Redeeming for {player['original_name']}", end="\r", flush=True)

            if result["status"].get(player["id"]) == "Successful" and not restart:
                counter_already_claimed += 1
                continue

            request_data = {"fid": player["id"], "time": time.time_ns()}
            request_data["sign"] = hashlib.md5(
                ("fid=" + request_data["fid"] + "&time=" + str(request_data["time"]) + SALT).encode("utf-8")
            ).hexdigest()

            login_request = r.post(URL + "/player", data=request_data, headers=HTTP_HEADER, timeout=30)
            login_response = login_request.json()

            if login_response["msg"] != "success":
                print(f"登入失敗：{player['original_name']} / {player['id']}。跳過。")
                counter_error += 1
                continue

            request_data["cdk"] = code
            request_data["sign"] = hashlib.md5(
                ("cdk=" + request_data["cdk"] + "&fid=" + request_data["fid"] + "&time=" + str(request_data["time"]) + SALT).encode("utf-8")
            ).hexdigest()

            redeem_request = r.post(URL + "/gift_code", data=request_data, headers=HTTP_HEADER, timeout=30)
            redeem_response = redeem_request.json()

            if redeem_response["err_code"] == 40014:
                return f"兌換碼 {code} 無效！"
            elif redeem_response["err_code"] == 40007:
                return f"兌換碼 {code} 已過期！"
            elif redeem_response["err_code"] == 40008:
                counter_already_claimed += 1
                result["status"][player["id"]] = "Successful"
            elif redeem_response["err_code"] == 20000:
                counter_successfully_claimed += 1
                result["status"][player["id"]] = "Successful"
            else:
                result["status"][player["id"]] = "Unsuccessful"
                print(f"\n錯誤發生: {redeem_response}")
                counter_error += 1

        with open(results_file, "w", encoding="utf-8") as fp:
            json.dump(results, fp)

        return (
            f"成功為 {counter_successfully_claimed} 位玩家兌換禮品碼！\n"
            f"{counter_already_claimed} 位玩家已經兌換過。\n"
            f"發生錯誤：{counter_error} 位玩家未能兌換。"
        )

    except Exception as e:
        return f"執行過程中發生錯誤：{e}"

@bot.command()
async def redeem(ctx, code: str):
    await ctx.send(f"正在處理兌換碼 {code}，請稍候...")
    result_message = await redeem_code(code)
    await ctx.send(result_message)

bot.run("MTMzMzY3MDE4MTYyMDQxNjUyMg.GrDdbj.AzIpTNTVzz5rO6t_aVlfGWkkGpUCNVPGzUZ0h8")
